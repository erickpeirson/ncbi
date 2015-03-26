import urllib2
import xml.etree.ElementTree as ET
import persistent
import transaction
import cPickle as pickle
import time
from unidecode import unidecode

from datatypes import *

import ZODB
from ZEO import ClientStorage

class PubMedManager(object):
    def __init__(self, server, port, tree):
        self.storage = ClientStorage.ClientStorage((server, port))
        self.db = ZODB.DB(self.storage)
        self.conn = self.db.open()
        self.root = getattr(self.conn.root(), tree)
        self.endpoint = 'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db={db}&id={id}&rettype=xml'

    def handle_date(self, e):
        dt_path = 'PubmedArticle/MedlineCitation/DateCreated'
        
        date_created = e.find(dt_path)
        year = date_created.find('Year').text
        month = date_created.find('Month').text
        day = date_created.find('Day').text    
        
        return year, month, day

    def handle_affiliations(self, e, date):
        aff_path = 'AffiliationInfo'
        
        affiliations = []
        try:
            for aff in e.find(aff_path).getchildren():
                affiliations.append(aff.text)
        except AttributeError:
            pass
        return affiliations

    def handle_authors(self, e, date):
        al_path = 'PubmedArticle/MedlineCitation/Article/AuthorList'
        _a = AuthorManager(self.root['authors'])
        authors = []
        try:
            for author in e.find(al_path).getchildren():
                a = _a.get_or_create(
                    last_name = (author.find('LastName').text or None),
                    fore_name = (author.find('ForeName').text or None),
                    initials = (author.find('Initials').text or None)           
                )

                for aff in self.handle_affiliations(author, date):
                    a.add_affiliation(aff, date)

                authors.append(a)
        except AttributeError:    # No authors.
            pass
        return authors

    def handle_headings(self, e):
        mh_path = 'PubmedArticle/MedlineCitation/MeshHeadingList'

        _e = ElementManager(self.root['elements'])
        _h = HeadingManager(self.root['headings'])
        
        headings = []
        for heading in e.find(mh_path).getchildren():
            ds = heading.find('DescriptorName')
            ql = heading.find('QualifierName')

            descriptor = _e.get_or_create(
                mt=ds.attrib['MajorTopicYN'] == 'Y',
                ui=ds.attrib['UI'],
                term=ds.text)
            
            if ql is not None:
                qualifier = _e.get_or_create(
                    mt=ql.attrib['MajorTopicYN'] == 'Y',
                    ui=ql.attrib['UI'],
                    term=ql.text
                )
            else:
                qualifier = None

            h = _h.get_or_create(desc=descriptor, qual=qualifier)
            headings.append(h)
        return headings
    
    def handle_grants(self, e):
        gl_path = 'PubmedArticle/MedlineCitation/Article/GrantList'
        
        _g = GrantManager(self.root['grants'])
        grants = []
        try:
            for grant in e.find(gl_path).getchildren():
                grant_id = (grant.find('GrantID').text or None)
                acronym = (grant.find('Acronym').text or None)
                agency = (grant.find('Agency').text or None)
                country = (grant.find('Country').text or None)
                g = _g.get_or_create(
                    grant_id = grant_id,
                    acronym = acronym,
                    agency = agency,
                    country = country
                )
                grants.append(g)        
        except AttributeError:    # No grant data available.
            pass
        return grants
    
    def get_paper(self, pmid):
        response_content = urllib2.urlopen(self.endpoint.format(db='pubmed', id=pmid)).read()
        e = ET.fromstring(response_content)
        return e

    def process_paper(self, e, pmid):
        if pmid in self.root['papers'].keys():
            return self.root['papers'][pmid]
        else:
            try:
                date = self.handle_date(e)

                p = Paper(pmid, e)
                grants = self.handle_grants(e)
                p.add_grant(grants)

                authors = self.handle_authors(e, date)
                p.add_author(authors)

                headings = self.handle_headings(e)
                p.add_heading(headings)

                self.root['papers'][pmid] = p
                
                # Save changes to database.
                transaction.commit()
            except:
                # Abandon all attempted changes for this paper.
                transaction.abort()
                raise   # Last Exception.
        return p