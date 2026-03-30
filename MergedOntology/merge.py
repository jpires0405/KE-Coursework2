from rdflib import Graph, Namespace
from rdflib.namespace import RDF, RDFS, OWL

g = Graph()

g.parse("MergedOntology/gtfs.ttl", format="turtle")       #
g.parse("MergedOntology/trasnportOntology.owl", format="xml")     

GTFS = Namespace("http://vocab.gtfs.org/terms#")
TOL = Namespace("http://disi.unitn.it/~ldkr/ldkr2016/Ontology/TransportOntologyLondon#")

g.bind("gtfs", GTFS)
g.bind("tol", TOL)
g.bind("owl", OWL)

g.add((GTFS.Station, OWL.equivalentClass, TOL.transportBuilding))
g.add((GTFS.Bus, OWL.equivalentClass, TOL.bus))
g.add((GTFS.Subway, OWL.equivalentClass, TOL.metro))
g.add((GTFS.Subway, OWL.equivalentClass, TOL.tube))
g.add((GTFS.Rail, OWL.equivalentClass, TOL.train))
g.add((GTFS.Ferry, OWL.equivalentClass, TOL.ferry))
g.add((GTFS.CableCar, OWL.equivalentClass, TOL.cableCar))
g.add((GTFS.LightRail, OWL.equivalentClass, TOL.tram))

g.add((GTFS.shortName, OWL.equivalentProperty, TOL.name))

g.add((GTFS.Station, RDFS.subClassOf, TOL.building))

g.add((GTFS.Trip, RDFS.subClassOf, TOL.event))

output_file = "merged_transport_ontology.ttl"
g.serialize(destination=output_file, format="turtle")

print(f"Merged ontology saved to {output_file}")