import persistent
import urllib2
import xml.etree.ElementTree as ET
import transaction
import cPickle as pickle
import time
from unidecode import unidecode

class Paper(object):
    iname = 'Papers'

    def __init__(self, pmid=None, year=None, title=None, abstract=None):
        if title is not None:
            title = unidecode(title)
        if abstract is not None:
            abstract = unidecode(abstract)

        self.pmid = pmid
        self.year = year
        self.title = title
        self.abstract = abstract

    def __str__(self):
        return str(self.pmid)

class Journal(object):
    iname = 'Journals'

    def __init__(self, issn=None, title=None):
        if title is not None:
            title = unidecode(title)

        self.issn = issn
        self.title = title

    def __str__(self):
        return str(self.title)

class OrganismClass(object):
    iname = 'OrganismClasses'

    def __init__(self, name=None):
        if name is not None:
            name = unidecode(name)

        self.name = name

    def __str__(self):
        return str(self.name)

class Author(object):
    iname = 'Authors'

    def __init__(self, last_name=None, fore_name=None, initials=None):
        if last_name is not None:
            last_name = unidecode(last_name)
        if fore_name is not None:
            fore_name = unidecode(fore_name)
        if initials is not None:
            initials = unidecode(initials)

        self.last_name = initials
        self.fore_name = fore_name
        self.initials = initials

    def __str__(self):
        return '{0}, {1} {2}'.format(self.last_name, self.fore_name, self.initials)

class Institution(object):
    iname = 'Institutions'

    def __init__(self, name=None, country=None):
        if name is not None:
            name = unidecode(name)
        if country is not None:
            country = unidecode(country)

        self.name = name
        self.country = country

    def __str__(self):
        return str(self.name)

class Grant(object):
    iname = 'Grants'

    def __init__(self, grant_id=None, acronym=None):
        self.grant_id = grant_id
        self.acronym = acronym

    def __str__(self):
        return str(self.grant_id)

class Agency(object):
    iname = 'Agencies'

    def __init__(self, name=None, country=None):
        if name is not None:
            name = unidecode(name)
        if country is not None:
            country = unidecode(country)

        self.name = name
        self.country = country

    def __str__(self):
        return str(self.name)

class MeSHHeading(object):
    iname = 'Headings'

    def __init__(self, descriptor=None, qualifier=None):
        if descriptor is not None:
            descriptor = unidecode(descriptor)
        if qualifier is not None:
            qualifier = unidecode(qualifier)

        self.descriptor = descriptor
        self.qualifier = qualifier

    def __str__(self):
        return '{0}.{1}'.format(self.descriptor, self.qualifier)