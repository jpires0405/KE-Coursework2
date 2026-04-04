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


def add_class(g: Graph, cls, label: str, comment: str=None, parent=None):
    g.add((cls, RDF.type, OWL.Class))
    g.add((cls, RDFS.label, Literal(label)))
    if comment:
        g.add((cls, RDFS.comment, Literal(comment)))
    if parent is not None:
        g.add((cls, RDFS.subClassOf, parent))


def add_object_property(g: Graph, prop, label: str, comment: str=None, domain=None, range_=None, parent=None):
    g.add((prop, RDF.type, OWL.ObjectProperty))
    g.add((prop, RDFS.label, Literal(label)))
    if comment:
        g.add((prop, RDFS.comment, Literal(comment)))
    if domain is not None:
        g.add((prop, RDFS.domain, domain))
    if range_ is not None:
        g.add((prop, RDFS.range, range_))
    if parent is not None:
        g.add((prop, RDFS.subPropertyOf, parent))


def add_datatype_property(g: Graph, prop, label: str, comment: str=None, domain=None, range_=None, parent=None):
    g.add((prop, RDF.type, OWL.DatatypeProperty))
    g.add((prop, RDFS.label, Literal(label)))
    if comment:
        g.add((prop, RDFS.comment, Literal(comment)))
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
    add_class(g, LT.TransportOperator, "Transport Operator", "An organisation responsible for operating transport services", LT.TransportEntity)
    add_class(g, LT.TransportLine, "Transport Line", "A transport service line consisting of multiple routes", LT.TransportEntity)
    add_class(g, LT.Route, "Route", "A transit route representing a group of trips", LT.TransportEntity)
    add_class(g, LT.Stop, "Stop", "A physical location passengers use for transport", LT.TransportEntity)
    add_class(g, LT.Service, "Service", "A set of trips operating on specific days", LT.TransportEntity)
    add_class(g, LT.Trip, "Trip", "A single journey along a route", LT.TransportEntity)
    add_class(g, LT.StopTime, "Stop Time", "A single journey along a route", LT.TransportEntity)
    add_class(g, LT.Place, "Place", "A physical location", LT.TransportEntity)
    add_class(g, LT.Report, "Report", None, LT.TransportEntity)
    add_class(g, LT.Statistic, "Statistic", None, LT.TransportEntity)

    # Richer subclasses
    add_class(g, LT.BusLine, "Bus Line", "A transport line operated by buses", LT.TransportLine)
    add_class(g, LT.TubeLine, "Tube Line", "A transport line operating within the London Underground network", LT.TransportLine)
    add_class(g, LT.DLRLine, "DLR Line", "A transport line operating within the Docklands Light Railway system", LT.TransportLine)
    add_class(g, LT.OvergroundLine, "Overground Line", "A transport line operating within the London Overground network", LT.TransportLine)
    add_class(g, LT.ElizabethLine, "Elizabeth Line", "A high-capacity railway line running across London and surrounding areas", LT.TransportLine)
    add_class(g, LT.TramLine, "Tram Line", "A transport line operated by trams", LT.TransportLine)
    add_class(g, LT.RiverBusLine, "River Bus Line", "A transport line operating on river services", LT.TransportLine)
    add_class(g, LT.NationalRailLine, "National Rail Line", None, LT.TransportLine)

    add_class(g, LT.BusRoute, "Bus Route", None, LT.Route)
    add_class(g, LT.TrainRoute, "Train Route", None, LT.Route)

    add_class(g, LT.BusStop, "Bus Stop", None, LT.Stop)
    add_class(g, LT.TrainStation, "Train Station", None, LT.Stop)

    # Generic properties
    add_object_property(g, LT.relatedTo, "related to")
    add_object_property(g, LT.operatedBy, "operated by", None, LT.Route, LT.TransportOperator, LT.relatedTo)
    add_object_property(g, LT.hasRoute, "has route", None, LT.TransportLine, LT.Route, LT.relatedTo)
    add_object_property(g, LT.hasStop, "has stop", None, LT.Route, LT.Stop, LT.relatedTo)
    add_object_property(g, LT.stopsAt, "stops at", None, LT.StopTime, LT.Stop, LT.relatedTo)
    add_object_property(g, LT.onTrip, "on trip", None, LT.StopTime, LT.Trip, LT.relatedTo)
    add_object_property(g, LT.onRoute, "on route", None, LT.Trip, LT.Route, LT.relatedTo)
    add_object_property(g, LT.belongsToService, "belongs to service", None, LT.Trip, LT.Service, LT.relatedTo)
    add_object_property(g, LT.servesStation, "serves station", None, LT.Route, LT.TrainStation, LT.relatedTo)
    add_object_property(g, LT.connectsTo, "connects to", None, LT.Stop, LT.Stop, LT.relatedTo)
    add_object_property(g, LT.locatedIn, "located in", None, LT.Stop, LT.Stop, LT.relatedTo)
    add_object_property(g, LT.mentionedInReport, "mentioned in report", None, None, None, LT.relatedTo)
    add_object_property(g, LT.aboutLine, "about line", None, LT.Report, LT.TransportLine, LT.relatedTo)
    add_object_property(g, LT.servedBy, "served by", None, None, None, LT.relatedTo)

    # Generic datatype property
    add_datatype_property(g, LT.value, "value")

    add_datatype_property(g, LT.name, "name", None, None, None, LT.value)
    add_datatype_property(g, LT.description, "description", None, None, None, LT.value)
    add_datatype_property(g, LT.routeNumber, "route number", None, LT.Route, XSD.string, LT.value)
    add_datatype_property(g, LT.stopCode, "stop code", None, LT.Stop, XSD.string, LT.value)
    add_datatype_property(g, LT.latitude, "latitude", None, LT.Stop, XSD.float, LT.value)
    add_datatype_property(g, LT.longitude, "longitude", None, LT.Stop, XSD.float, LT.value)
    add_datatype_property(g, LT.wheelchairAccessible, "wheelchair accessible", None, LT.Stop, XSD.boolean, LT.value)
    add_datatype_property(g, LT.startDate, "start date", None, LT.Service, XSD.string, LT.value)
    add_datatype_property(g, LT.endDate, "end date", None, LT.Service, XSD.string, LT.value)
    add_datatype_property(g, LT.arrivalTime, "arrival time", None, LT.StopTime, XSD.string, LT.value)
    add_datatype_property(g, LT.departureTime, "departure time", None, LT.StopTime, XSD.string, LT.value)
    add_datatype_property(g, LT.hasRidership, "has ridership", None, None, XSD.string, LT.value)
    add_datatype_property(g, LT.hasFrequency, "has frequency", None, None, XSD.string, LT.value)
    add_datatype_property(g, LT.extendsTo, "extends to", None, None, XSD.string, LT.value)
    add_datatype_property(g, LT.hasStopName, "has stop name", None, LT.TransportLine, XSD.string, LT.value)
    add_datatype_property(g, LT.hasStatus, "has status", None, LT.TransportLine, XSD.string, LT.value)
    add_datatype_property(g, LT.isDisrupted, "is disrupted", None, LT.TransportLine, XSD.boolean, LT.value)
    add_datatype_property(g, LT.disruptionReason, "disruption reason", None, LT.TransportLine, XSD.string, LT.value)
    add_datatype_property(g, LT.hasNightService, "has night service", None, LT.TransportLine, XSD.boolean, LT.value)

    # Inverse Properties
    add_object_property(g, LT.isStopOn, "is stop on", None, LT.Stop, LT.Route, LT.relatedTo)
    g.add((LT.hasStop, OWL.inverseOf, LT.isStopOn))
    add_object_property(g, LT.hasTrip, "has trip", None, LT.Route, LT.Trip, LT.relatedTo)
    g.add((LT.onRoute, OWL.inverseOf, LT.hasTrip))
    add_object_property(g, LT.isServedBy, "is served by", None, LT.TrainStation, LT.Route, LT.relatedTo)
    g.add((LT.servesStation, OWL.inverseOf, LT.isServedBy))

    # Symmetric Properties
    add_object_property(g, LT.intersectsWith, "intersects with", None, LT.TransportLine, LT.TransportLine, LT.relatedTo)
    g.add((LT.intersectsWith, RDF.type, OWL.SymmetricProperty))
    return g


if __name__ == "__main__":
    g = build_ontology()
    print(f"Ontology triples: {len(g)}")
    print(g.serialize(format="turtle"))