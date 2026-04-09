import os
import sys
from rdflib import Literal, RDF, RDFS, XSD

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.processing.parse_gtfs import (
    parse_agencies, parse_stops, parse_routes, parse_trips,
    parse_calendar, parse_stop_times
)
from src.kg.ontology import build_ontology, LT, GTFS, SCHEMA


def uri(prefix, local_id):
    clean = str(local_id).replace(" ", "_").replace("/", "_")
    return LT[f"{prefix}_{clean}"]


def map_agencies(g):
    agencies = parse_agencies()
    for a in agencies:
        agent = uri("agency", a["agency_id"])
        if a.get("agency_url"):
            g.add((agent, SCHEMA.url, Literal(a["agency_url"], datatype=XSD.string)))
        g.add((agent, RDF.type, LT.TransportOperator))
        g.add((agent, LT.operatorName, Literal(a["agency_name"])))
        g.add((agent, RDFS.label, Literal(a["agency_name"])))
    print(f"  Mapped {len(agencies)} agencies")
    return g


def map_stops(g):
    stops = parse_stops()
    for s in stops:
        stop = uri("stop", s["stop_id"])

        if s["stop_id"].startswith(("9400", "940G")):
            g.add((stop, RDF.type, LT.TrainStation))
        else:
            g.add((stop, RDF.type, LT.BusStop))

        g.add((stop, LT.name, Literal(s["stop_name"])))
        g.add((stop, RDFS.label, Literal(s["stop_name"])))
        g.add((stop, GTFS.lat, Literal(float(s["stop_lat"]), datatype=XSD.float)))
        g.add((stop, GTFS.long, Literal(float(s["stop_lon"]), datatype=XSD.float)))

        if s.get("stop_code"):
            g.add((stop, LT.naptanCode, Literal(s["stop_code"])))

        if s.get("parent_station"):
            parent_uri = uri("stop", s["parent_station"])
            g.add((stop, LT.locatedIn, parent_uri))
        
        wheelchair = s.get("wheelchair_boarding", "0")
        g.add((stop, LT.wheelchairAccessible, Literal(wheelchair == "1", datatype=XSD.boolean)))

    print(f"  Mapped {len(stops)} stops")
    return g


def map_routes(g):
    routes = parse_routes()
    for r in routes:
        route = uri("route", r["route_id"])

        if r.get("route_type") == "200":
            g.add((route, RDF.type, LT.BusRoute))
        else:
            g.add((route, RDF.type, LT.TrainRoute))

        if r.get("route_short_name"):
            if r.get("route_type") == "200":
                g.add((route, LT.busRouteNumber, Literal(r["route_short_name"])))
            else:
                g.add((route, LT.routeNumber, Literal(r["route_short_name"])))
            g.add((route, LT.name, Literal(r["route_short_name"])))

        if r.get("route_long_name"):
            g.add((route, RDFS.label, Literal(r["route_long_name"])))
            if not r.get("route_short_name"):
                g.add((route, LT.name, Literal(r["route_long_name"])))

        if r.get("agency_id"):
            agency = uri("agency", r["agency_id"])
            g.add((route, LT.operatedBy, agency))


    print(f"  Mapped {len(routes)} routes")
    return g


def map_calendar(g):
    calendar = parse_calendar()
    for c in calendar:
        service = uri("service", c["service_id"])
        g.add((service, RDF.type, GTFS.Service))

        if c.get("start_date"):
            g.add((service, LT.startDate, Literal(c["start_date"])))
        if c.get("end_date"):
            g.add((service, LT.endDate, Literal(c["end_date"])))

    print(f"  Mapped {len(calendar)} calendar entries")
    return g


def map_trips(g, limit=10000):
    trips = parse_trips(limit=limit)
    for t in trips:
        trip = uri("trip", t["trip_id"][:16])
        g.add((trip, RDF.type, GTFS.Trip))

        if t.get("trip_headsign"):
            g.add((trip, GTFS.headsign, Literal(t["trip_headsign"])))
            g.add((trip, RDFS.label, Literal(t["trip_headsign"])))

        route = uri("route", t["route_id"])
        g.add((trip, LT.onRoute, route))

        service = uri("service", t["service_id"])
        g.add((trip, LT.belongsToService, service))

        g.add((route, LT.hasTrip, trip))

    print(f"  Mapped {len(trips)} trips")
    return g


def map_stop_times(g, limit=50000):
    stop_times = parse_stop_times(limit=limit)

    trips = parse_trips(limit=None)
    trip_to_route = {t["trip_id"]: t["route_id"] for t in trips}

    stops_data = parse_stops()
    stop_to_parent = {s['stop_id']: s['parent_station'] for s in stops_data if s.get('parent_station')}

    last_trip_id = None
    last_stop_uri = None

    for st in stop_times:
        stop_time = uri("stoptime", f"{st['trip_id'][:16]}_{st['stop_sequence']}")
        g.add((stop_time, RDF.type, GTFS.StopTime))
        g.add((stop_time, GTFS.arrivalTime, Literal(st["arrival_time"])))
        g.add((stop_time, GTFS.departureTime, Literal(st["departure_time"])))

        stop = uri("stop", st["stop_id"])
        trip = uri("trip", st["trip_id"][:16])

        g.add((stop_time, LT.stopsAt, stop))
        g.add((stop_time, LT.onTrip, trip))

        if st["trip_id"] == last_trip_id and last_stop_uri:
            g.add((last_stop_uri, LT.connectsTo, stop))

        route_id = trip_to_route.get(st["trip_id"])
        if route_id:
            route_uri = uri("route", route_id)
            g.add((route_uri, LT.hasStop, stop))
            g.add((stop, LT.isStopOn, route_uri))

            parent_id = stop_to_parent.get(st["stop_id"])
            if parent_id:
                station_uri = uri("stop", parent_id)
                g.add((route_uri, LT.servesStation, station_uri))
                g.add((station_uri, LT.isServedBy, route_uri))

        last_trip_id = st["trip_id"]
        last_stop_uri = stop

    print(f"  Mapped {len(stop_times)} stop times")
    return g


def build_gtfs_kg():
    print("Building GTFS knowledge graph...")
    g = build_ontology()
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