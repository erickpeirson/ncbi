import persistent
import urllib2
import xml.etree.ElementTree as ET
import transaction
import cPickle as pickle
import time
from unidecode import unidecode

class Paper(persistent.Persistent):
    def __init__(self, pmid, et):
        self.pmid = pmid
        self.et = et
        self.grants = []
        self.headings = []
        self.authors = []
    
    def add_grant(self, grant):
        if hasattr(grant, '__iter__'):
            for g in grant:
                self.add_grant(g)
        else:
            self.grants.append(grant)
    
    def add_heading(self, mesh_heading):
        if hasattr(mesh_heading, '__iter__'):
            for h in mesh_heading:
                self.add_heading(h)
        else:
            self.headings.append(mesh_heading)
        
    def add_author(self, author):
        if hasattr(author, '__iter__'):
            for a in author:
                self.add_author(a)
        else:
            self.authors.append(author)

class Grant(persistent.Persistent):
    def __init__(self, grant_id, acronym, agency, country):
        self.grant_id = grant_id
        self.acronym = acronym
        self.agency = agency
        self.country = country

class MeSHHeading(persistent.Persistent):
    def __init__(self, desc, qual=None):
        self.descriptor = desc
        self.qualifier = qual

class MeSHElement(persistent.Persistent):
    def __init__(self, mt, ui, term):
        self.major_topic = mt
        self.ui = ui
        self.term = term

class Author(persistent.Persistent):
    def __init__(self, last_name, fore_name, initials=None):
        self.last_name = last_name
        self.fore_name = fore_name
        self.initials = initials
        
        self.affiliations = []
    
    def add_affiliation(self, affiliation, date):
        self.affiliations.append((date, affiliation))

class Manager(object):
    def __init__(self, index):
        self.index = index
    
    def get_or_create(self, *args, **kwargs):
        kwargs_clean = {}
        for k,v in kwargs.iteritems():
            if type(v) is str or type(v) is unicode:
                kwargs_clean[k] = unidecode(v)
            else:
                kwargs_clean[k] = v
        try:
            return self.index[self.iformat.format(**kwargs_clean)]
        except KeyError:
            instance = self.model(**kwargs)
            self.index[self.iformat.format(**kwargs_clean)] = instance
            return instance

class ElementManager(Manager):
    iformat = '{mt}_{ui}_{term}'
    model = MeSHElement

class HeadingManager(Manager):
    iformat = '{desc}_{qual}'
    model = MeSHHeading

class GrantManager(Manager):
    iformat = '{grant_id}'
    model = Grant

class AuthorManager(Manager):
    iformat = '{last_name}_{fore_name}'
    model = Author


                                                                