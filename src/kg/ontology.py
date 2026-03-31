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
    g.add((GTFS.Route, RDF.type, OWL.Class))
    g.add((GTFS.Trip, RDF.type, OWL.Class))
    g.add((GTFS.Agency, RDF.type, OWL.Class))
    g.add((GTFS.Service, RDF.type, OWL.Class))
    g.add((GTFS.StopTime, RDF.type, OWL.Class))

    # ─── Extend GTFS with subclasses ───
    g.add((LT.BusStop, RDF.type, OWL.Class))
    g.add((LT.BusStop, RDFS.subClassOf, GTFS.Stop))
    g.add((LT.BusStop, RDFS.label, Literal("Bus Stop")))

    g.add((LT.TrainStation, RDF.type, OWL.Class))
    g.add((LT.TrainStation, RDFS.subClassOf, GTFS.Stop))
    g.add((LT.TrainStation, RDFS.label, Literal("Train Station")))

    g.add((LT.BusRoute, RDF.type, OWL.Class))
    g.add((LT.BusRoute, RDFS.subClassOf, GTFS.Route))
    g.add((LT.BusRoute, RDFS.label, Literal("Bus Route")))

    g.add((LT.TrainRoute, RDF.type, OWL.Class))
    g.add((LT.TrainRoute, RDFS.subClassOf, GTFS.Route))
    g.add((LT.TrainRoute, RDFS.label, Literal("Train Route")))

    # ─── GTFS properties ───
    g.add((GTFS.stopName, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.stopName, RDFS.domain, GTFS.Stop))
    g.add((GTFS.stopName, RDFS.range, XSD.string))

    g.add((GTFS.lat, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.lat, RDF.type, OWL.FunctionalProperty))
    g.add((GTFS.lat, RDFS.domain, GTFS.Stop))
    g.add((GTFS.lat, RDFS.range, XSD.float))

    g.add((GTFS.long, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.long, RDF.type, OWL.FunctionalProperty))
    g.add((GTFS.long, RDFS.domain, GTFS.Stop))
    g.add((GTFS.long, RDFS.range, XSD.float))

    g.add((GTFS.routeShortName, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.routeShortName, RDFS.domain, GTFS.Route))
    g.add((GTFS.routeShortName, RDFS.range, XSD.string))

    g.add((GTFS.headsign, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.headsign, RDFS.domain, GTFS.Trip))
    g.add((GTFS.headsign, RDFS.range, XSD.string))

    g.add((GTFS.arrivalTime, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.arrivalTime, RDFS.domain, GTFS.StopTime))
    g.add((GTFS.arrivalTime, RDFS.range, XSD.time))

    g.add((GTFS.departureTime, RDF.type, OWL.DatatypeProperty))
    g.add((GTFS.departureTime, RDFS.domain, GTFS.StopTime))
    g.add((GTFS.departureTime, RDFS.range, XSD.time))


    # ─── Extend GTFS with subproperties ───
    g.add((LT.naptanCode, RDF.type, OWL.DatatypeProperty))
    g.add((LT.naptanCode, RDFS.subPropertyOf, GTFS.stopName))
    g.add((LT.naptanCode, RDFS.label, Literal("NaPTAN stop code")))
    g.add((LT.naptanCode, RDFS.domain, GTFS.Stop))
    g.add((LT.naptanCode, RDFS.range, XSD.string))

    g.add((LT.busRouteNumber, RDF.type, OWL.DatatypeProperty))
    g.add((LT.busRouteNumber, RDFS.subPropertyOf, GTFS.routeShortName))
    g.add((LT.busRouteNumber, RDFS.label, Literal("Bus route number/name")))
    g.add((LT.busRouteNumber, RDFS.domain, LT.BusRoute))
    g.add((LT.busRouteNumber, RDFS.range, XSD.string))

    # ─── Classes from Schema.org ───
    g.add((SCHEMA.Place, RDF.type, OWL.Class))
    g.add((SCHEMA.Organization, RDF.type, OWL.Class))
    g.add((SCHEMA.BusStation, RDF.type, OWL.Class))
    g.add((SCHEMA.TrainStation, RDF.type, OWL.Class))

    # ─── Extend Schema.org with subclasses ───
    g.add((LT.TransportLine, RDF.type, OWL.Class))
    g.add((LT.TransportLine, RDFS.subClassOf, SCHEMA.Place))
    g.add((LT.TransportLine, RDFS.label, Literal("Transport Line")))

    g.add((LT.TubeLine, RDF.type, OWL.Class))
    g.add((LT.TubeLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.TubeLine, RDFS.label, Literal("London Underground Line")))

    g.add((LT.DLRLine, RDF.type, OWL.Class))
    g.add((LT.DLRLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.DLRLine, RDFS.label, Literal("DLR Line")))

    g.add((LT.OvergroundLine, RDF.type, OWL.Class))
    g.add((LT.OvergroundLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.OvergroundLine, RDFS.label, Literal("London Overground Line")))

    g.add((LT.ElizabethLine, RDF.type, OWL.Class))
    g.add((LT.ElizabethLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.ElizabethLine, RDFS.label, Literal("Elizabeth Line")))

    g.add((LT.BusLine, RDF.type, OWL.Class))
    g.add((LT.BusLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.BusLine, RDFS.label, Literal("Bus Line")))

    g.add((LT.RiverBusLine, RDF.type, OWL.Class))
    g.add((LT.RiverBusLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.RiverBusLine, RDFS.label, Literal("River Bus Line")))

    g.add((LT.TramLine, RDF.type, OWL.Class))
    g.add((LT.TramLine, RDFS.subClassOf, LT.TransportLine))
    g.add((LT.TramLine, RDFS.label, Literal("Tram Line")))

    g.add((LT.TransportOperator, RDF.type, OWL.Class))
    g.add((LT.TransportOperator, RDFS.subClassOf, SCHEMA.Organization))
    g.add((LT.TransportOperator, RDFS.label, Literal("Transport Operator")))

    # ─── Schema.org properties ───
    g.add((SCHEMA.name, RDF.type, OWL.DatatypeProperty))
    g.add((SCHEMA.geo, RDF.type, OWL.ObjectProperty))
    g.add((SCHEMA.url, RDF.type, OWL.DatatypeProperty))

    # ─── Extend Schema.org with subproperties ───
    g.add((LT.operatorName, RDF.type, OWL.DatatypeProperty))
    g.add((LT.operatorName, RDFS.subPropertyOf, SCHEMA.name))
    g.add((LT.operatorName, RDFS.label, Literal("Operator trading name")))
    g.add((LT.operatorName, RDFS.domain, LT.TransportOperator))
    g.add((LT.operatorName, RDFS.range, XSD.string))

    g.add((LT.lineName, RDF.type, OWL.DatatypeProperty))
    g.add((LT.lineName, RDFS.subPropertyOf, SCHEMA.name))
    g.add((LT.lineName, RDFS.label, Literal("Transport line name")))
    g.add((LT.lineName, RDFS.domain, LT.TransportLine))
    g.add((LT.lineName, RDFS.range, XSD.string))

    # ─── Custom object properties ───
    g.add((LT.operatedBy, RDF.type, OWL.ObjectProperty))
    g.add((LT.operatedBy, RDFS.label, Literal("operated by")))
    g.add((LT.operatedBy, RDFS.domain, GTFS.Route))
    g.add((LT.operatedBy, RDFS.range, LT.TransportOperator))

    g.add((LT.hasRoute, RDF.type, OWL.ObjectProperty))
    g.add((LT.hasRoute, RDFS.label, Literal("has route")))
    g.add((LT.hasRoute, RDFS.domain, LT.TransportLine))
    g.add((LT.hasRoute, RDFS.range, GTFS.Route))

    g.add((LT.hasStop, RDF.type, OWL.ObjectProperty))
    g.add((LT.hasStop, RDFS.label, Literal("has stop")))
    g.add((LT.hasStop, RDFS.domain, GTFS.Route))
    g.add((LT.hasStop, RDFS.range, GTFS.Stop))

    g.add((LT.belongsToService, RDF.type, OWL.ObjectProperty))
    g.add((LT.belongsToService, RDFS.label, Literal("belongs to service")))
    g.add((LT.belongsToService, RDFS.domain, GTFS.Trip))
    g.add((LT.belongsToService, RDFS.range, GTFS.Service))

    g.add((LT.stopsAt, RDF.type, OWL.ObjectProperty))
    g.add((LT.stopsAt, RDFS.label, Literal("stops at")))
    g.add((LT.stopsAt, RDFS.domain, GTFS.StopTime))
    g.add((LT.stopsAt, RDFS.range, GTFS.Stop))

    g.add((LT.onTrip, RDF.type, OWL.ObjectProperty))
    g.add((LT.onTrip, RDFS.label, Literal("on trip")))
    g.add((LT.onTrip, RDFS.domain, GTFS.StopTime))
    g.add((LT.onTrip, RDFS.range, GTFS.Trip))

    g.add((LT.onRoute, RDF.type, OWL.ObjectProperty))
    g.add((LT.onRoute, RDFS.label, Literal("on route")))
    g.add((LT.onRoute, RDFS.domain, GTFS.Trip))
    g.add((LT.onRoute, RDFS.range, GTFS.Route))

    g.add((LT.wheelchairAccessible, RDF.type, OWL.DatatypeProperty))
    g.add((LT.wheelchairAccessible, RDFS.label, Literal("wheelchair accessible")))
    g.add((LT.wheelchairAccessible, RDFS.range, XSD.boolean))

    return g


if __name__ == "__main__":
    g = build_ontology()
    print(f"Ontology triples: {len(g)}")
    print(g.serialize(format="turtle"))
