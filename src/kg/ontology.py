from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

LT = Namespace("http://example.org/london-transport#")
GTFS = Namespace("http://vocab.gtfs.org/terms#")
SCHEMA = Namespace("https://schema.org/")

NAMESPACES = {
    "lt": LT,
    "gtfs": GTFS,
    "schema": SCHEMA,
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

    # Classes from GTFS ontology
    add_class(g, GTFS.Stop, "Stop", "A physical location passengers use for transport", LT.TransportEntity)
    add_class(g, GTFS.Route, "Route", "A transit route representing a group of trips", LT.TransportEntity)
    add_class(g, GTFS.Trip, "Trip", "A single journey along a route", LT.TransportEntity)    
    add_class(g, GTFS.Service, "Service", "A set of trips operating on specific days", LT.TransportEntity)
    add_class(g, GTFS.StopTime, "Stop Time", "Arrival and departure times at a stop for a trip", LT.TransportEntity)

    # Extend GTFS with subclasses
    add_class(g, LT.BusRoute, "Bus Route", "A route used by buses", GTFS.Route)
    add_class(g, LT.TrainRoute, "Train Route", "A route used by trains", GTFS.Route)
    add_class(g, LT.BusStop, "Bus Stop", "A stop specifically for bus services", GTFS.Stop)
    add_class(g, LT.TrainStation, "Train Station", "A station for train services", GTFS.Stop)

    # GTFS properties
    add_datatype_property(g, GTFS.stopName, "Stop Name", "The name of a stop", range_=XSD.string)
    add_datatype_property(g, GTFS.lat, "Latitude", "The latitude coordinate of a stop", range_=XSD.float)
    add_datatype_property(g, GTFS.long, "Longitude", "The longitude coordinate of a stop", range_=XSD.float)
    add_datatype_property(g, GTFS.routeShortName, "Route Short Name", "The short name or number of a transit route", range_=XSD.string)
    add_datatype_property(g, GTFS.headsign, "Headsign", "The destination text displayed to passengers on a vehicle", range_=XSD.string)
    add_datatype_property(g, GTFS.arrivalTime, "Arrival Time", "The scheduled arrival time at a specific stop", range_=XSD.string)
    add_datatype_property(g, GTFS.departureTime, "Departure Time", "The scheduled departure time from a specific stop", range_=XSD.string)

    # GTFS subproperties
    add_datatype_property(g, LT.naptanCode, "NaPTAN stop code", "A unique identifier assigned to a stop within the UK NaPTAN system", GTFS.Stop, XSD.string, GTFS.stopName)
    add_datatype_property(g, LT.busRouteNumber, "Bus route number/name", "The specific identifier or number used to distinguish a London bus route", LT.BusRoute, XSD.string, GTFS.routeShortName)

    # Classes from Schema.org
    add_class(g, SCHEMA.Place, "Place", "Schema.org Place")
    add_class(g, SCHEMA.Organization, "Organization", "Schema.org Organization")
    add_class(g, SCHEMA.BusStation, "Bus Station", "Schema.org Bus Station")
    add_class(g, SCHEMA.TrainStation, "Train Station", "Schema.org Train Station")

    # Extend Schema.org with subclasses
    add_class(g, LT.TransportLine, "Transport Line", "A transport service line consisting of multiple routes", SCHEMA.Place)
    add_class(g, LT.BusLine, "Bus Line", "A transport line operated by buses", LT.TransportLine)
    add_class(g, LT.TubeLine, "London Underground Line", "A transport line operating within the London Underground network", LT.TransportLine)
    add_class(g, LT.DLRLine, "DLR Line", "A transport line operating within the Docklands Light Railway system", LT.TransportLine)
    add_class(g, LT.OvergroundLine, "London Overground Line", "A transport line operating within the London Overground network", LT.TransportLine)
    add_class(g, LT.ElizabethLine, "Elizabeth Line", "A high-capacity railway line running across London and surrounding areas", LT.TransportLine)
    add_class(g, LT.TramLine, "Tram Line", "A transport line operated by trams", LT.TransportLine)
    add_class(g, LT.RiverBusLine, "River Bus Line", "A transport line operating on river services", LT.TransportLine)
    add_class(g, LT.NationalRailLine, "National Rail Line", "A rail line operating as part of the UK National Rail network", LT.TransportLine)
    add_class(g, LT.TransportOperator, "Transport Operator", "An organisation responsible for operating transport services", SCHEMA.Organization)

    # Schema.org properties
    add_datatype_property(g, SCHEMA.name, "Name", "The name", range_=XSD.string)
    add_object_property(g, SCHEMA.geo, "Geo coordinates", "The coordinates of the place")
    add_datatype_property(g, SCHEMA.url, "URL", "URL", range_=XSD.string)

    # Extend Schema.org with subproperties
    add_datatype_property(g, LT.operatorName, "Operator trading name", "The trading name of a transport operator", LT.TransportOperator, XSD.string, SCHEMA.name)
    add_datatype_property(g, LT.lineName, "Transport line name", "The specific name of a transport service line", LT.TransportLine, XSD.string, SCHEMA.name)

    # Core classes
    add_class(g, LT.TransportEntity, "Transport Entity", "The root class for all London transport-related concepts.")
    add_class(g, LT.Report, "Report", "A service update, incident report, or status announcement", LT.TransportEntity)
    add_class(g, LT.Statistic, "Statistic", "Quantitative data regarding ridership, performance, or usage", LT.TransportEntity)

    # Generic properties
    add_object_property(g, LT.relatedTo, "related to", "A general relationship between any two transport entities.")
    add_object_property(g, LT.operatedBy, "operated by", "A route is operated by a transport operator", LT.Route, LT.TransportOperator, LT.relatedTo)
    add_object_property(g, LT.hasRoute, "has route", "A transport line contains routes", LT.TransportLine, LT.Route, LT.relatedTo)
    add_object_property(g, LT.hasStop, "has stop", "A route goes through specific stops", LT.Route, LT.Stop, LT.relatedTo)
    add_object_property(g, LT.stopsAt, "stops at", "A stop time occurs at a specific stop", LT.StopTime, LT.Stop, LT.relatedTo)
    add_object_property(g, LT.onTrip, "on trip", "A stop time is part of a trip", LT.StopTime, LT.Trip, LT.relatedTo)
    add_object_property(g, LT.onRoute, "on route", "A trip is part of a route", LT.Trip, LT.Route, LT.relatedTo)
    add_object_property(g, LT.belongsToService, "belongs to service", "A trip is associated with a service schedule", LT.Trip, LT.Service, LT.relatedTo)
    add_object_property(g, LT.servesStation, "serves station", "Identifies a station served by a particular route or line", LT.Route, LT.TrainStation, LT.relatedTo)
    add_object_property(g, LT.connectsTo, "connects to", "A stop is connected to another stop", LT.Stop, LT.Stop, parent=LT.relatedTo)
    add_object_property(g, LT.locatedIn, "located in", "Specifies the geographic or administrative container of a place", LT.Stop, LT.Stop, parent=LT.relatedTo)
    add_object_property(g, LT.mentionedInReport, "mentioned in report", "Links a transport entity to a report discussing its status", parent=LT.relatedTo)
    add_object_property(g, LT.aboutLine, "about line", "Links a report to the transport line it concerns", LT.Report, LT.TransportLine, LT.relatedTo)
    add_object_property(g, LT.servedBy, "served by", "Indicates the transport service that provides access to a location", parent=LT.relatedTo)

    # Generic datatype property
    add_datatype_property(g, LT.value, "value", "A generic container for literal values and attributes.")

    add_datatype_property(g, LT.name, "name", "The name of a place or organisation", parent=LT.value)
    add_datatype_property(g, LT.description, "description", "A textual explanation providing additional details", parent=LT.value)
    add_datatype_property(g, LT.routeNumber, "route number", "The identifier or number used to distinguish a bus route", LT.Route, XSD.string, LT.value)
    add_datatype_property(g, LT.stopCode, "stop code", "A unique identifier assigned to a stop within the UK NaPTAN system", LT.Stop, XSD.string, LT.value)
    add_datatype_property(g, LT.wheelchairAccessible, "wheelchair accessible", "Indicates whether a stop is accessible to wheelchair users", LT.Stop, XSD.boolean, LT.value)
    add_datatype_property(g, LT.startDate, "start date", "The date on which a service begins operation", LT.Service, XSD.string, LT.value)
    add_datatype_property(g, LT.endDate, "end date", "The date on which a service ceases operation", LT.Service, XSD.string, LT.value)
    add_datatype_property(g, LT.hasRidership, "has ridership", "Data regarding the number of passengers using a service", None, XSD.string, LT.value)
    add_datatype_property(g, LT.hasFrequency, "has frequency", "Information about how often a service runs", None, XSD.string, LT.value)
    add_datatype_property(g, LT.extendsTo, "extends to", "The geographic reach or terminal destination of a service", None, XSD.string, LT.value)
    add_datatype_property(g, LT.hasStopName, "has stop name", "The textual name of a stop from a transport API", LT.TransportLine, XSD.string, LT.value)
    add_datatype_property(g, LT.hasStatus, "has status", "The current operational status of a transport line", LT.TransportLine, XSD.string, LT.value)
    add_datatype_property(g, LT.isDisrupted, "is disrupted", "A flag indicating if a line is currently experiencing delays", LT.TransportLine, XSD.boolean, LT.value)
    add_datatype_property(g, LT.disruptionReason, "disruption reason", "The explanation provided for a service disruption", LT.TransportLine, XSD.string, LT.value)
    add_datatype_property(g, LT.hasNightService, "has night service", "A flag indicating if a line operates during night hours", LT.TransportLine, XSD.boolean, LT.value)

    # Inverse Properties
    add_object_property(g, LT.isStopOn, "is stop on", "Inverse property linking a stop to the routes it serves", LT.Stop, LT.Route, LT.relatedTo)
    g.add((LT.hasStop, OWL.inverseOf, LT.isStopOn))
    add_object_property(g, LT.hasTrip, "has trip", "Links a route to the journeys scheduled upon it", LT.Route, LT.Trip, LT.relatedTo)
    g.add((LT.onRoute, OWL.inverseOf, LT.hasTrip))
    add_object_property(g, LT.isServedBy, "is served by", "Inverse property linking a station to its calling routes", LT.TrainStation, LT.Route, LT.relatedTo)
    g.add((LT.servesStation, OWL.inverseOf, LT.isServedBy))

    # Symmetric Properties
    add_object_property(g, LT.intersectsWith, "intersects with", "Identifies transport lines that share a common station location", LT.TransportLine, LT.TransportLine, LT.relatedTo)
    g.add((LT.intersectsWith, RDF.type, OWL.SymmetricProperty))
    return g


if __name__ == "__main__":
    g = build_ontology()
    print(f"Ontology triples: {len(g)}")
    print(g.serialize(format="turtle"))