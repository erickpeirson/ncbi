from py2neo import Graph
from py2neo.ext.ogm import Store
import networkx as nx

class Neo4jManager(object):
    def __init__(self):
        self.graph = Graph("http://localhost:7474/db/data/")
        self.store = Store(self.graph)

    def get_or_create(self, object):
        model = object.__class__
        try:
            node = self.store.load_unique(model.iname, "name", str(object), model)
            if node is not None:
                del object
                return node

        # An AttributeError is raised when no previous nodes have been saved
        #  for this model.
        except AttributeError:
            pass        # Proceed to create a new node.

        return self.create(object)

    def create(self, object):
        model = object.__class__
        self.store.save_unique(model.iname, "name", str(object), object)
        self.store.save(object)
        return object

    def create_relation(self, source, predicate, target, properties={}):
        self.store.relate(source, predicate, target, properties)
        try:
            self.store.save(source)
        except:
            print source.__dict__
            print target.__dict__
            raise

class NetworkXManager(object):
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.node_index = {}

    def get_or_create(self, object):
        try:
            return self.node_index[str(object)]
        except KeyError:
            self.graph.add_node(object)
            self.node_index[str(object)] = object
            return object

    def create_relation(self, source, predicate, target, properties={}):
        properties.update({'predicate':predicate})
        self.graph.add_edge(source, target, **properties)