from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

LT = Namespace("http://example.org/london-transport#")

NAMESPACES = {
    "lt": LT,
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "xsd": XSD,
}


def add_class(g: Graph, cls, label: str, parent=None):
    g.add((cls, RDF.type, OWL.Class))
    g.add((cls, RDFS.label, Literal(label)))
    if parent is not None:
        g.add((cls, RDFS.subClassOf, parent))


def add_object_property(g: Graph, prop, label: str, domain=None, range_=None, parent=None):
    g.add((prop, RDF.type, OWL.ObjectProperty))
    g.add((prop, RDFS.label, Literal(label)))
    if domain is not None:
        g.add((prop, RDFS.domain, domain))
    if range_ is not None:
        g.add((prop, RDFS.range, range_))
    if parent is not None:
        g.add((prop, RDFS.subPropertyOf, parent))


def add_datatype_property(g: Graph, prop, label: str, domain=None, range_=None, parent=None):
    g.add((prop, RDF.type, OWL.DatatypeProperty))
    g.add((prop, RDFS.label, Literal(label)))
    if domain is not None:
        g.add((prop, RDFS.domain, domain))
    if range_ is not None:
        g.add((prop, RDFS.range, range_))
    if parent is not None:
        g.add((prop, RDFS.subPropertyOf, parent))


def build_ontology() -> Graph:
    g = Graph()
    for prefix, ns in NAMESPACES.items():
        g.bind(prefix, ns)

    # Core classes
    add_class(g, LT.TransportEntity, "Transport Entity")
    add_class(g, LT.TransportOperator, "Transport Operator", LT.TransportEntity)
    add_class(g, LT.TransportLine, "Transport Line", LT.TransportEntity)
    add_class(g, LT.Route, "Route", LT.TransportEntity)
    add_class(g, LT.Stop, "Stop", LT.TransportEntity)
    add_class(g, LT.Service, "Service", LT.TransportEntity)
    add_class(g, LT.Trip, "Trip", LT.TransportEntity)
    add_class(g, LT.StopTime, "Stop Time", LT.TransportEntity)
    add_class(g, LT.Place, "Place", LT.TransportEntity)
    add_class(g, LT.Report, "Report", LT.TransportEntity)
    add_class(g, LT.Statistic, "Statistic", LT.TransportEntity)

    # Richer subclasses
    add_class(g, LT.BusLine, "Bus Line", LT.TransportLine)
    add_class(g, LT.TubeLine, "Tube Line", LT.TransportLine)
    add_class(g, LT.DLRLine, "DLR Line", LT.TransportLine)
    add_class(g, LT.OvergroundLine, "Overground Line", LT.TransportLine)
    add_class(g, LT.ElizabethLine, "Elizabeth Line", LT.TransportLine)
    add_class(g, LT.TramLine, "Tram Line", LT.TransportLine)
    add_class(g, LT.RiverBusLine, "River Bus Line", LT.TransportLine)
    add_class(g, LT.NationalRailLine, "National Rail Line", LT.TransportLine)

    add_class(g, LT.BusRoute, "Bus Route", LT.Route)
    add_class(g, LT.TrainRoute, "Train Route", LT.Route)

    add_class(g, LT.BusStop, "Bus Stop", LT.Stop)
    add_class(g, LT.TrainStation, "Train Station", LT.Stop)

    # Generic properties
    add_object_property(g, LT.relatedTo, "related to")
    add_object_property(g, LT.operatedBy, "operated by", LT.Route, LT.TransportOperator, LT.relatedTo)
    add_object_property(g, LT.hasRoute, "has route", LT.TransportLine, LT.Route, LT.relatedTo)
    add_object_property(g, LT.hasStop, "has stop", LT.Route, LT.Stop, LT.relatedTo)
    add_object_property(g, LT.stopsAt, "stops at", LT.StopTime, LT.Stop, LT.relatedTo)
    add_object_property(g, LT.onTrip, "on trip", LT.StopTime, LT.Trip, LT.relatedTo)
    add_object_property(g, LT.onRoute, "on route", LT.Trip, LT.Route, LT.relatedTo)
    add_object_property(g, LT.belongsToService, "belongs to service", LT.Trip, LT.Service, LT.relatedTo)
    add_object_property(g, LT.servesStation, "serves station", LT.TransportLine, LT.TrainStation, LT.relatedTo)
    add_object_property(g, LT.connectsTo, "connects to", parent=LT.relatedTo)
    add_object_property(g, LT.locatedIn, "located in", parent=LT.relatedTo)
    add_object_property(g, LT.mentionedInReport, "mentioned in report", parent=LT.relatedTo)
    add_object_property(g, LT.aboutLine, "about line", LT.Report, LT.TransportLine, LT.relatedTo)
    add_object_property(g, LT.extendsTo, "extends to", parent=LT.relatedTo)
    add_object_property(g, LT.servedBy, "served by", parent=LT.relatedTo)

    # Generic datatype property
    add_datatype_property(g, LT.value, "value")

    add_datatype_property(g, LT.name, "name", parent=LT.value)
    add_datatype_property(g, LT.description, "description", parent=LT.value)
    add_datatype_property(g, LT.routeNumber, "route number", LT.Route, XSD.string, LT.value)
    add_datatype_property(g, LT.stopCode, "stop code", LT.Stop, XSD.string, LT.value)
    add_datatype_property(g, LT.latitude, "latitude", LT.Stop, XSD.float, LT.value)
    add_datatype_property(g, LT.longitude, "longitude", LT.Stop, XSD.float, LT.value)
    add_datatype_property(g, LT.wheelchairAccessible, "wheelchair accessible", LT.Stop, XSD.boolean, LT.value)
    add_datatype_property(g, LT.startDate, "start date", LT.Service, XSD.string, LT.value)
    add_datatype_property(g, LT.endDate, "end date", LT.Service, XSD.string, LT.value)
    add_datatype_property(g, LT.arrivalTime, "arrival time", LT.StopTime, XSD.string, LT.value)
    add_datatype_property(g, LT.departureTime, "departure time", LT.StopTime, XSD.string, LT.value)
    add_datatype_property(g, LT.hasRidership, "has ridership", range_=XSD.string, parent=LT.value)
    add_datatype_property(g, LT.hasFrequency, "has frequency", range_=XSD.string, parent=LT.value)

    return g


if __name__ == "__main__":
    g = build_ontology()
    print(f"Ontology triples: {len(g)}")
    print(g.serialize(format="turtle"))