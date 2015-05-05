import urllib2
import xml.etree.ElementTree as ET
import persistent
import transaction
import cPickle as pickle
import time
from unidecode import unidecode

from datatypes import *
from managers import *

def get_smart(e, element):
    elem = e.find(element)
    if elem is not None:     
        text = elem.text
        if text is not None: 
            text = unidecode(text)
    else:
        text = ''
    return text
    
class PubMedManager(object):
    def __init__(self, manager=Neo4jManager):
        self.endpoint = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db={db}&id={id}&rettype=xml'
        self.manager = manager()

    def handle_date(self, e):
        dt_path = 'PubmedArticle/MedlineCitation/DateCreated'
        
        date_created = e.find(dt_path)
        year = date_created.find('Year').text
        month = date_created.find('Month').text
        day = date_created.find('Day').text    
        
        return year, month, day

    def handle_affiliations(self, e):
        aff_path = 'AffiliationInfo'
        
        affiliations = []
        aff_parent = e.find(aff_path)
        if aff_parent is not None:
            for aff in aff_parent.getchildren():
                if aff.text is not None:
                    i = self.manager.get_or_create(Institution(name=unidecode(aff.text)))
                    affiliations.append(i)

        return affiliations

    def handle_authors(self, e, date):
        al_path = 'PubmedArticle/MedlineCitation/Article/AuthorList'

        authors = []
        al = e.find(al_path)
        if al is not None:
            for author in al.getchildren():
                a = self.manager.get_or_create(Author(
                    fore_name = get_smart(author, 'ForeName'),
                    last_name = get_smart(author, 'LastName'),
                    initials = get_smart(author, 'Initials')
                ))

                for aff in self.handle_affiliations(author):
                    self.manager.create_relation(a, "AFFILIATED", aff, {"year":date[0], "month":date[1], "day":date[2]})

                authors.append(a)

        return authors

    def handle_headings(self, e):
        mh_path = 'PubmedArticle/MedlineCitation/MeshHeadingList'
        
        headings = []
        mh = e.find(mh_path)
        if mh is not None:
            for heading in mh.getchildren():
                descriptor = get_smart(heading, 'DescriptorName')
                qualifier = get_smart(heading, 'QualifierName')
                if descriptor != '':
                    h = self.manager.get_or_create(MeSHHeading(
                            descriptor=descriptor,
                            qualifier=qualifier
                        ))
                    headings.append(h)

        return headings
    
    def handle_grants(self, e):
        gl_path = 'PubmedArticle/MedlineCitation/Article/GrantList'

        grants = []
        gl = e.find(gl_path)

        if gl is not None:
            for grant in gl.getchildren():

                grant_id = get_smart(grant, 'GrantID')
                acronym = get_smart(grant, 'Acronym')
                agency = get_smart(grant, 'Agency')
                country = get_smart(grant, 'Country')

                if agency != '':
                    a = self.manager.get_or_create(Agency(
                            name = agency,
                            country = country
                        ))

                if grant_id != '':
                    g = self.manager.get_or_create(Grant(
                            grant_id = grant_id,
                            acronym = acronym
                        ))
                    grants.append(g)

                if agency != '' and grant_id != '':
                    self.manager.create_relation(a, "AWARDED", g)

        return grants

    def handle_journal(self, e):
        jnl = e.find('.//Journal')
        if jnl is not None:
            issn = get_smart(jnl, './/ISSN')
            title = get_smart(jnl, './/Title')
            
            if title == '':
                return

            return self.manager.get_or_create(Journal(issn=issn, title=title))

    def get_paper(self, pmid):
        response_content = urllib2.urlopen(self.endpoint.format(db='pubmed', id=pmid)).read()
        e = ET.fromstring(response_content)
        return e

    def process_paper(self, e, pmid):

        date = self.handle_date(e)

        
        title = get_smart(e, './/ArticleTitle')
        abstract = get_smart(e, './/AbstractText')

        p = self.manager.get_or_create(Paper(
                pmid=pmid,
                year=date[0],
                title=title,
                abstract=abstract
            ))
        grants = self.handle_grants(e)
        for grant in grants:
            self.manager.create_relation(p, "FUNDED_BY", grant)

        authors = self.handle_authors(e, date)
        for author in authors:
            self.manager.create_relation(p, "HAS_AUTHOR", author, {"year":date[0], "month":date[1], "day":date[2]})

        headings = self.handle_headings(e)
        for heading in headings:
            self.manager.create_relation(p, "HAS_HEADING", heading)

        journal = self.handle_journal(e)
        if journal is not None:
            self.manager.create_relation(p, "PUBLISHED_IN", journal, {"year": date[0], "month": date[1], "day": date[2]})

        return p