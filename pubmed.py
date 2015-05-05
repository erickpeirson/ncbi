import urllib2
import xml.etree.ElementTree as ET
import persistent
import transaction
import cPickle as pickle
import time
from unidecode import unidecode

from datatypes import *
from managers import *

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
                i = self.manager.get_or_create(Institution(name=aff.text))
                affiliations.append(i)

        return affiliations

    def handle_authors(self, e, date):
        al_path = 'PubmedArticle/MedlineCitation/Article/AuthorList'

        authors = []
        al = e.find(al_path)
        if al is not None:
            for author in al.getchildren():
                lname_elem = author.find('LastName')
                fname_elem = author.find('ForeName')
                init_elem = author.find('Initials')
                if lname_elem is not None:  last_name = lname_elem.text 
                else:                       last_name = None
                if fname_elem is not None:  fore_name = fname_elem.text
                else:                       fore_name = None   
                if init_elem is not None:   initials = init_elem.text
                else:                       initials = None

                a = self.manager.get_or_create(Author(
                    fore_name = fore_name,
                    last_name = last_name,
                    initials = initials           
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
                ds = heading.find('DescriptorName')
                ql = heading.find('QualifierName')
                
                if ds is not None:
                    descriptor = ds.text
                    if ql is not None:
                        qualifier = ql.text
                    else:
                        qualifier = None

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
                id_elem = grant.find('GrantID')
                ac_elem = grant.find('Acronym')
                ag_elem = grant.find('Agency')
                co_elem = grant.find('Country')

                if id_elem is not None:         grant_id = id_elem.text
                else:                           grant_id = None
                if ac_elem is not None:         acronym = ac_elem.text
                else:                           acronym = None
                if ag_elem is not None:         agency = ag_elem.text
                else:                           agency = None
                if co_elem is not None:         country = co_elem.text
                else:                           country = None

                if agency is not None:
                    a = self.manager.get_or_create(Agency(
                            name = agency,
                            country = country
                        ))

                if grant_id is not None:
                    g = self.manager.get_or_create(Grant(
                            grant_id = grant_id,
                            acronym = acronym
                        ))
                    grants.append(g)

                if agency is not None and grant_id is not None:
                    self.manager.create_relation(a, "AWARDED", g)

        return grants

    def handle_journal(self, e):
        jnl = e.find('.//Journal')
        if jnl is not None:
            issn_elem = jnl.find('.//ISSN')
            title_elem = jnl.find('.//Title')

            if issn_elem is not None:   issn = issn_elem.text
            else:                       issn = None
            if title_elem is not None:  title = title_elem.text
            else:                       return # Don't proceed without title.

            return self.manager.get_or_create(Journal(issn=issn, title=title))

    def get_paper(self, pmid):
        response_content = urllib2.urlopen(self.endpoint.format(db='pubmed', id=pmid)).read()
        e = ET.fromstring(response_content)
        return e

    def process_paper(self, e, pmid):

        date = self.handle_date(e)
        t_elem = e.find('.//ArticleTitle')
        a_elem = e.find('.//AbstractText')
        if t_elem is not None:      title = t_elem.text
        else:                       title = ''
        if a_elem is not None:      abstract = a_elem.text
        else:                       abstract = ''

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