"""
Map GTFS CSV data to RDF triples using the London Transport ontology.
Converts agencies, stops, routes, trips, and stop_times into a knowledge graph.
"""

import os
import sys

from rdflib import Graph, Literal, URIRef, RDF, RDFS, XSD

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.processing.parse_gtfs import (
    parse_agencies, parse_stops, parse_routes, parse_trips,
    parse_calendar, parse_stop_times
)
from src.kg.ontology import build_ontology, LT, GTFS, SCHEMA


def uri(prefix, local_id):
    """Create a URI for a resource. Replaces spaces/special chars."""
    clean = str(local_id).replace(" ", "_").replace("/", "_")
    return LT[f"{prefix}_{clean}"]

#Each agency row becomes a TransportOperator instance.
def map_agencies(g):
    agencies = parse_agencies()
    for a in agencies:
        agent = uri("agency", a["agency_id"])
        g.add((agent, RDF.type, LT.TransportOperator))
        g.add((agent, LT.operatorName, Literal(a["agency_name"])))
        if a.get("agency_url"):
            g.add((agent, SCHEMA.url, Literal(a["agency_url"], datatype=XSD.anyURI)))
    print(f"  Mapped {len(agencies)} agencies")
    return g


def map_stops(g):
    """
    Each stop row becomes a BusStop (or TrainStation if the stop_id
    starts with '9400' which indicates a rail/tube station in NaPTAN).
    Includes name, latitude, longitude, and wheelchair accessibility.
    """
    stops = parse_stops()
    for s in stops:
        stop = uri("stop", s["stop_id"])

        #code 9400 are rail/tube stations
        if s["stop_id"].startswith("9400"):
            g.add((stop, RDF.type, LT.TrainStation))
        else:
            g.add((stop, RDF.type, LT.BusStop))

        g.add((stop, GTFS.stopName, Literal(s["stop_name"])))
        g.add((stop, GTFS.lat, Literal(float(s["stop_lat"]), datatype=XSD.float)))
        g.add((stop, GTFS.long, Literal(float(s["stop_lon"]), datatype=XSD.float)))

        if s.get("stop_code"):
            g.add((stop, LT.naptanCode, Literal(s["stop_code"])))

        wheelchair = s.get("wheelchair_boarding", "0")
        g.add((stop, LT.wheelchairAccessible, Literal(wheelchair == "1", datatype=XSD.boolean)))

    print(f"  Mapped {len(stops)} stops")
    return g


def map_routes(g):
    """
    Each route becomes a BusRoute or TrainRoute, linked to its agency.
    Route type 200 = bus, other types are rail/tram.
    """
    routes = parse_routes()
    for r in routes:
        route = uri("route", r["route_id"])

        if r.get("route_type") == "200":
            g.add((route, RDF.type, LT.BusRoute))
            if r.get("route_short_name"):
                g.add((route, LT.busRouteNumber, Literal(r["route_short_name"])))
        else:
            g.add((route, RDF.type, LT.TrainRoute))

        if r.get("route_short_name"):
            g.add((route, GTFS.routeShortName, Literal(r["route_short_name"])))
        if r.get("route_long_name"):
            g.add((route, RDFS.label, Literal(r["route_long_name"])))

        # Link route to its agency
        if r.get("agency_id"):
            agency = uri("agency", r["agency_id"])
            g.add((route, LT.operatedBy, agency))

    print(f"  Mapped {len(routes)} routes")
    return g


def map_calendar(g):
    """
    Each calendar entry becomes a Service instance with days of operation.
    e.g. service_id 4 runs Mon-Fri → lt:service_4 has weekday flags.
    """
    calendar = parse_calendar()
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    for c in calendar:
        service = uri("service", c["service_id"])
        g.add((service, RDF.type, GTFS.Service))

        for day in days:
            g.add((service, LT[day], Literal(c[day] == "1", datatype=XSD.boolean)))

        if c.get("start_date"):
            g.add((service, LT.startDate, Literal(c["start_date"], datatype=XSD.string)))
        if c.get("end_date"):
            g.add((service, LT.endDate, Literal(c["end_date"], datatype=XSD.string)))

    print(f"  Mapped {len(calendar)} calendar entries")
    return g


def map_trips(g, limit=10000):
    """
    Each trip links a route to a service with a headsign.
    Limiting to first 10,000 to keep the KG manageable —
    the full dataset has 475,000+ trips.
    """
    trips = parse_trips(limit=limit)
    for t in trips:
        trip = uri("trip", t["trip_id"][:16])  # Shorten long IDs
        g.add((trip, RDF.type, GTFS.Trip))

        if t.get("trip_headsign"):
            g.add((trip, GTFS.headsign, Literal(t["trip_headsign"])))

        # Link trip to its route
        route = uri("route", t["route_id"])
        g.add((trip, LT.onRoute, route))

        # Link trip to its service schedule
        service = uri("service", t["service_id"])
        g.add((trip, LT.belongsToService, service))

    print(f"  Mapped {len(trips)} trips")
    return g


def map_stop_times(g, limit=50000):
    """
    Each stop_time links a trip to a stop with arrival/departure times.
    Limiting to 50,000 — the full dataset has 17.9 million rows.
    Also creates hasStop links between routes and stops via trips.
    """
    stop_times = parse_stop_times(limit=limit)
    for st in stop_times:
        stop_time = uri("stoptime", f"{st['trip_id'][:16]}_{st['stop_sequence']}")
        g.add((stop_time, RDF.type, GTFS.StopTime))

        g.add((stop_time, GTFS.arrivalTime, Literal(st["arrival_time"])))
        g.add((stop_time, GTFS.departureTime, Literal(st["departure_time"])))

        # Link to stop and trip
        stop = uri("stop", st["stop_id"])
        trip = uri("trip", st["trip_id"][:16])
        g.add((stop_time, LT.stopsAt, stop))
        g.add((stop_time, LT.onTrip, trip))

    print(f"  Mapped {len(stop_times)} stop times")
    return g


def build_gtfs_kg():
    """Run the full GTFS → RDF mapping pipeline."""
    print("Building GTFS knowledge graph...")
    g = build_ontology()  # Start with the ontology

    g = map_agencies(g)
    g = map_stops(g)
    g = map_routes(g)
    g = map_calendar(g)
    g = map_trips(g)
    g = map_stop_times(g)

    print(f"Total triples: {len(g)}")
    return g


if __name__ == "__main__":
    g = build_gtfs_kg()
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    output = os.path.join(base_dir, "data/kg/gtfs_kg.ttl")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    g.serialize(destination=output, format="turtle")
    print(f"Saved to {output}")
