"""
Define the London Transport ontology, extending two existing ontologies:
1. GTFS ontology (https://vocab.gtfs.org/terms#) — for transit feed concepts
2. Schema.org (https://schema.org/) — for general transport/place concepts

Extends each with 2+ subclasses and 2+ subproperties.
"""

from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD

# Namespace definitions
LT = Namespace("http://example.org/london-transport#")
GTFS = Namespace("http://vocab.gtfs.org/terms#")
SCHEMA = Namespace("http://schema.org/")

NAMESPACES = {
    "lt": LT,
    "gtfs": GTFS,
    "schema": SCHEMA,
    "rdf": RDF,
    "rdfs": RDFS,
    "owl": OWL,
    "xsd": XSD,
}


def build_ontology():
    g = Graph()
    for prefix, ns in NAMESPACES.items():
        g.bind(prefix, ns)

    # ─── Classes from GTFS ontology ───
    g.add((GTFS.Stop, RDF.type, OWL.Class))
    g.add((GTFS.Stop, RDFS.label, Literal("Stop")))
    g.add((GTFS.Stop, RDFS.comment, Literal("A physical location passengers use for transport")))

    g.add((GTFS.Route, RDF.type, OWL.Class))
    g.add((GTFS.Route, RDFS.label, Literal("Route")))
    g.add((GTFS.Route, RDFS.comment, Literal("A transit route representing a group of trips")))

    g.add((GTFS.Trip, RDF.type, OWL.Class))
    g.add((GTFS.Trip, RDFS.label, Literal("Trip")))
    g.add((GTFS.Trip, RDFS.comment, Literal("A single journey along a route")))

    g.add((GTFS.Agency, RDF.type, OWL.Class))
    g.add((GTFS.Agency, RDFS.label, Literal("Agency")))
    g.add((GTFS.Agency, RDFS.comment, Literal("An organisation providing transport services")))

    g.add((GTFS.Service, RDF.type, OWL.Class))
    g.add((GTFS.Service, RDFS.label, Literal("Service")))
    g.add((GTFS.Service, RDFS.comment, Literal("A set of trips operating on specific days")))

    g.add((GTFS.StopTime, RDF.type, OWL.Class))
    g.add((GTFS.StopTime, RDFS.label, Literal("Stop Time")))
    g.add((GTFS.StopTime, RDFS.comment, Literal("Arrival and departure times at a stop for a trip")))

    # ─── Extend GTFS with subclasses ───
    g.add((LT.BusStop, RDF.type, OWL.Class))
    g.add((LT.BusStop, RDFS.subClassOf, GTFS.Stop))
    g.add((LT.BusStop, RDFS.label, Literal("Bus Stop")))
    g.add((LT.BusStop, RDFS.comment, Literal("A stop specifically for bus services")))

    g.add((LT.TrainStation, RDF.type, OWL.Class))
    g.add((LT.TrainStation, RDFS.subClassOf, GTFS.Stop))
    g.add((LT.TrainStation, RDFS.label, Literal("Train Station")))
    g.add((LT.TrainStation, RDFS.comment, Literal("A station for train services")))

    g.add((LT.BusRoute, RDF.type, OWL.Class))
    g.add((LT.BusRoute, RDFS.subClassOf, GTFS.Route))
    g.add((LT.BusRoute, RDFS.label, Literal("Bus Route")))
    g.add((LT.BusRoute, RDFS.comment, Literal("A route used by buses")))
    
    g.add((LT.TrainRoute, RDF.type, OWL.Class))
    g.add((LT.TrainRoute, RDFS.subClassOf, GTFS.Route))
    g.add((LT.TrainRoute, RDFS.label, Literal("Train Route")))
    g.add((LT.TrainRoute, RDFS.comment, Literal("A route used by trains")))

    # ─── GTFS properties ───
    g.add((GTFS.stopName, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.stopName, RDFS.domain, GTFS.Stop))
    g.add((GTFS.stopName, RDFS.range, XSD.string))
    g.add((GTFS.stopName, RDFS.label, Literal("stop name")))
    g.add((GTFS.stopName, RDFS.comment, Literal("The name of a stop")))

    g.add((GTFS.lat, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.lat, RDF.type, OWL.FunctionalProperty))
    g.add((GTFS.lat, RDFS.domain, GTFS.Stop))
    g.add((GTFS.lat, RDFS.range, XSD.float))
    g.add((GTFS.lat, RDFS.label, Literal("latitude")))
    g.add((GTFS.lat, RDFS.comment, Literal("Latitude of a stop")))

    g.add((GTFS.long, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.long, RDF.type, OWL.FunctionalProperty))
    g.add((GTFS.long, RDFS.domain, GTFS.Stop))
    g.add((GTFS.long, RDFS.range, XSD.float))
    g.add((GTFS.long, RDFS.label, Literal("longitude")))
    g.add((GTFS.long, RDFS.comment, Literal("Longitude of a stop")))

    g.add((GTFS.routeShortName, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.routeShortName, RDFS.domain, GTFS.Route))
    g.add((GTFS.routeShortName, RDFS.range, XSD.string))
    g.add((GTFS.routeShortName, RDFS.label, Literal("route short name")))
    g.add((GTFS.routeShortName, RDFS.comment, Literal("Short name or number of a route")))

    g.add((GTFS.headsign, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.headsign, RDFS.domain, GTFS.Trip))
    g.add((GTFS.headsign, RDFS.range, XSD.string))
    g.add((GTFS.headsign, RDFS.label, Literal("headsign")))
    g.add((GTFS.headsign, RDFS.comment, Literal("Destination displayed on a vehicle")))

    g.add((GTFS.arrivalTime, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.arrivalTime, RDFS.domain, GTFS.StopTime))
    g.add((GTFS.arrivalTime, RDFS.range, XSD.time))
    g.add((GTFS.arrivalTime, RDFS.label, Literal("arrival time")))
    g.add((GTFS.arrivalTime, RDFS.comment, Literal("Arrival time at a stop")))

    g.add((GTFS.departureTime, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.departureTime, RDFS.domain, GTFS.StopTime))
    g.add((GTFS.departureTime, RDFS.range, XSD.time))
    g.add((GTFS.departureTime, RDFS.label, Literal("departure time")))
    g.add((GTFS.departureTime, RDFS.comment, Literal("Departure time from a stop")))

    # ─── Extend GTFS with subproperties ───
    g.add((LT.naptanCode, RDF.type, OWL.DatatypeProperty))
    g.add((LT.naptanCode, RDFS.subPropertyOf, GTFS.stopName))
    g.add((LT.naptanCode, RDFS.label, Literal("NaPTAN stop code")))
    g.add((LT.naptanCode, RDFS.comment, Literal("A unique identifier assigned to a stop within the UK NaPTAN system")))
    g.add((LT.naptanCode, RDFS.domain, GTFS.Stop))
    g.add((LT.naptanCode, RDFS.range, XSD.string))

    g.add((LT.busRouteNumber, RDF.type, OWL.DatatypeProperty))
    g.add((LT.busRouteNumber, RDFS.subPropertyOf, GTFS.routeShortName))
    g.add((LT.busRouteNumber, RDFS.label, Literal("Bus route number/name")))
    g.add((LT.busRouteNumber, RDFS.comment, Literal("The identifier or number used to distinguish a bus route")))
    g.add((LT.busRouteNumber, RDFS.domain, LT.BusRoute))
    g.add((LT.busRouteNumber, RDFS.range, XSD.string))

    # ─── Classes from Schema.org ───
    g.add((SCHEMA.Place, RDF.type, OWL.Class))
    g.add((SCHEMA.Place, RDFS.label, Literal("Place")))
    g.add((SCHEMA.Place, RDFS.comment, Literal("A physical location")))

    g.add((SCHEMA.Organization, RDF.type, OWL.Class))
    g.add((SCHEMA.Organization, RDFS.label, Literal("Organization")))
    g.add((SCHEMA.Organization, RDFS.comment, Literal("An organisation such as a transport operator")))

    g.add((SCHEMA.BusStation, RDF.type, OWL.Class))
    g.add((SCHEMA.BusStation, RDFS.label, Literal("Bus Station")))
    g.add((SCHEMA.BusStation, RDFS.comment, Literal("A station for buses")))

    g.add((SCHEMA.TrainStation, RDF.type, OWL.Class))
    g.add((SCHEMA.TrainStation, RDFS.label, Literal("Train Station")))
    g.add((SCHEMA.TrainStation, RDFS.comment, Literal("A station for trains")))

    # ─── Extend Schema.org with subclasses ───
    g.add((LT.TransportLine, RDF.type, OWL.Class))
    g.add((LT.TransportLine, RDFS.subClassOf, SCHEMA.Place))
    g.add((LT.TransportLine, RDFS.label, Literal("Transport Line")))
    g.add((LT.TransportLine, RDFS.comment, Literal("A transport service line consisting of multiple routes")))

    g.add((LT.TubeLine, RDF.type, OWL.Class))
    g.add((LT.TubeLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.TubeLine, RDFS.label, Literal("London Underground Line")))
    g.add((LT.TubeLine, RDFS.comment, Literal("A transport line operating within the London Underground network")))

    g.add((LT.DLRLine, RDF.type, OWL.Class))
    g.add((LT.DLRLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.DLRLine, RDFS.label, Literal("DLR Line")))
    g.add((LT.DLRLine, RDFS.comment, Literal("A transport line operating within the Docklands Light Railway system")))

    g.add((LT.OvergroundLine, RDF.type, OWL.Class))
    g.add((LT.OvergroundLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.OvergroundLine, RDFS.label, Literal("London Overground Line")))
    g.add((LT.OvergroundLine, RDFS.comment, Literal("A transport line operating within the London Overground network")))

    g.add((LT.ElizabethLine, RDF.type, OWL.Class))
    g.add((LT.ElizabethLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.ElizabethLine, RDFS.label, Literal("Elizabeth Line")))
    g.add((LT.ElizabethLine, RDFS.comment, Literal("A high-capacity railway line running across London and surrounding areas")))

    g.add((LT.BusLine, RDF.type, OWL.Class))
    g.add((LT.BusLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.BusLine, RDFS.label, Literal("Bus Line")))
    g.add((LT.BusLine, RDFS.comment, Literal("A transport line operated by buses")))


    g.add((LT.RiverBusLine, RDF.type, OWL.Class))
    g.add((LT.RiverBusLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.RiverBusLine, RDFS.label, Literal("River Bus Line")))
    g.add((LT.RiverBusLine, RDFS.comment, Literal("A transport line operating on river services")))

    g.add((LT.TramLine, RDF.type, OWL.Class))
    g.add((LT.TramLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.TramLine, RDFS.label, Literal("Tram Line")))
    g.add((LT.TramLine, RDFS.comment, Literal("A transport line operated by trams")))

    g.add((LT.TransportOperator, RDF.type, OWL.Class))
    g.add((LT.TransportOperator, RDFS.subClassOf, SCHEMA.Organization))
    g.add((LT.TransportOperator, RDFS.label, Literal("Transport Operator")))
    g.add((LT.TransportOperator, RDFS.comment, Literal("An organisation responsible for operating transport services")))

    # ─── Schema.org properties ───
    g.add((SCHEMA.name, RDF.type, OWL.DatatypeProperty))
    g.add((SCHEMA.name, RDFS.domain, SCHEMA.Place))
    g.add((SCHEMA.name, RDFS.range, XSD.string))
    g.add((SCHEMA.name, RDFS.label, Literal("name")))
    g.add((SCHEMA.name, RDFS.comment, Literal("The name of a place or organisation")))

    g.add((SCHEMA.geo, RDF.type, OWL.ObjectProperty))
    g.add((SCHEMA.geo, RDFS.domain, SCHEMA.Place))
    g.add((SCHEMA.geo, RDFS.range, SCHEMA.Place))
    g.add((SCHEMA.geo, RDFS.label, Literal("geo location")))
    g.add((SCHEMA.geo, RDFS.comment, Literal("Links a place to its geographic location")))

    g.add((SCHEMA.url, RDF.type, OWL.DatatypeProperty))
    g.add((SCHEMA.url, RDFS.domain, SCHEMA.Organization))
    g.add((SCHEMA.url, RDFS.range, XSD.anyURI))
    g.add((SCHEMA.url, RDFS.label, Literal("URL")))
    g.add((SCHEMA.url, RDFS.comment, Literal("A web link associated with an organisation or resource")))

    # ─── Extend Schema.org with subproperties ───
    g.add((LT.operatorName, RDF.type, OWL.DatatypeProperty))
    g.add((LT.operatorName, RDFS.subPropertyOf, SCHEMA.name))
    g.add((LT.operatorName, RDFS.label, Literal("Operator trading name")))
    g.add((LT.operatorName, RDFS.comment, Literal("The name of a transport operator")))
    g.add((LT.operatorName, RDFS.domain, LT.TransportOperator))
    g.add((LT.operatorName, RDFS.range, XSD.string))

    g.add((LT.lineName, RDF.type, OWL.DatatypeProperty))
    g.add((LT.lineName, RDFS.subPropertyOf, SCHEMA.name))
    g.add((LT.lineName, RDFS.label, Literal("Transport line name")))
    g.add((LT.lineName, RDFS.comment, Literal("The name of a transport line")))
    g.add((LT.lineName, RDFS.domain, LT.TransportLine))
    g.add((LT.lineName, RDFS.range, XSD.string))

    # ─── Custom object properties ───

    g.add((LT.hasTrip, RDF.type, OWL.ObjectProperty))
    g.add((LT.hasTrip, RDFS.label, Literal("has trip")))
    g.add((LT.hasTrip, RDFS.comment, Literal("connects route to trip")))
    g.add((LT.hasTrip, RDFS.domain, GTFS.Route))
    g.add((LT.hasTrip, RDFS.range, GTFS.Trip))

    g.add((LT.connectsTo, RDF.type, OWL.ObjectProperty))
    g.add((LT.connectsTo, RDFS.label, Literal("connects to")))
    g.add((LT.connectsTo, RDFS.comment, Literal("A stop is connected to another stop")))
    g.add((LT.connectsTo, RDFS.domain, GTFS.Stop))
    g.add((LT.connectsTo, RDFS.range, GTFS.Stop))

    g.add((LT.operatesLine, RDF.type, OWL.ObjectProperty))
    g.add((LT.operatesLine, RDFS.label, Literal("operates line")))
    g.add((LT.operatesLine, RDFS.comment, Literal("A transport operator operates a transport line")))
    g.add((LT.operatesLine, RDFS.domain, LT.TransportOperator))
    g.add((LT.operatesLine, RDFS.range, LT.TransportLine))

    g.add((LT.managedByAgency, RDF.type, OWL.ObjectProperty))
    g.add((LT.managedByAgency, RDFS.label, Literal("managed by agency")))
    g.add((LT.managedByAgency, RDFS.comment, Literal("A route is managed by a transit agency")))
    g.add((LT.managedByAgency, RDFS.domain, GTFS.Route))
    g.add((LT.managedByAgency, RDFS.range, GTFS.Agency))

    g.add((LT.operatedBy, RDF.type, OWL.ObjectProperty))
    g.add((LT.operatedBy, RDFS.label, Literal("operated by")))
    g.add((LT.operatedBy, RDFS.comment, Literal("A route is operated by a transport operator")))
    g.add((LT.operatedBy, RDFS.domain, GTFS.Route))
    g.add((LT.operatedBy, RDFS.range, LT.TransportOperator))

    g.add((LT.hasRoute, RDF.type, OWL.ObjectProperty))
    g.add((LT.hasRoute, RDFS.label, Literal("has route")))
    g.add((LT.hasRoute, RDFS.comment, Literal("A transport line contains routes")))
    g.add((LT.hasRoute, RDFS.domain, LT.TransportLine))
    g.add((LT.hasRoute, RDFS.range, GTFS.Route))

    g.add((LT.hasStop, RDF.type, OWL.ObjectProperty))
    g.add((LT.hasStop, RDFS.label, Literal("has stop")))
    g.add((LT.hasStop, RDFS.comment, Literal("A route goes through specific stops")))
    g.add((LT.hasStop, RDFS.domain, GTFS.Route))
    g.add((LT.hasStop, RDFS.range, GTFS.Stop))

    g.add((LT.belongsToService, RDF.type, OWL.ObjectProperty))
    g.add((LT.belongsToService, RDFS.label, Literal("belongs to service")))
    g.add((LT.belongsToService, RDFS.comment, Literal("A trip is associated with a service schedule")))
    g.add((LT.belongsToService, RDFS.domain, GTFS.Trip))
    g.add((LT.belongsToService, RDFS.range, GTFS.Service))

    g.add((LT.stopsAt, RDF.type, OWL.ObjectProperty))
    g.add((LT.stopsAt, RDFS.label, Literal("stops at")))
    g.add((LT.stopsAt, RDFS.comment, Literal("A stop time occurs at a specific stop")))
    g.add((LT.stopsAt, RDFS.domain, GTFS.StopTime))
    g.add((LT.stopsAt, RDFS.range, GTFS.Stop))

    g.add((LT.onTrip, RDF.type, OWL.ObjectProperty))
    g.add((LT.onTrip, RDFS.label, Literal("on trip")))
    g.add((LT.onTrip, RDFS.comment, Literal("A stop time is part of a trip")))
    g.add((LT.onTrip, RDFS.domain, GTFS.StopTime))
    g.add((LT.onTrip, RDFS.range, GTFS.Trip))

    g.add((LT.onRoute, RDF.type, OWL.ObjectProperty))
    g.add((LT.onRoute, RDFS.label, Literal("on route")))
    g.add((LT.onRoute, RDFS.comment, Literal("A trip is part of a route")))
    g.add((LT.onRoute, RDFS.domain, GTFS.Trip))
    g.add((LT.onRoute, RDFS.range, GTFS.Route))

    g.add((LT.wheelchairAccessible, RDF.type, OWL.DatatypeProperty))
    g.add((LT.wheelchairAccessible, RDFS.label, Literal("wheelchair accessible")))
    g.add((LT.wheelchairAccessible, RDFS.comment, Literal("Indicates whether a stop is accessible to wheelchair users")))
    g.add((LT.wheelchairAccessible, RDFS.domain, GTFS.Stop))
    g.add((LT.wheelchairAccessible, RDFS.range, XSD.boolean))

    return g


if __name__ == "__main__":
    g = build_ontology()
    print(f"Ontology triples: {len(g)}")
    print(g.serialize(format="turtle"))
