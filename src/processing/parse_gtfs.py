"""
Parse London GTFS CSV files and extract structured data for KG construction.
Reads stops, routes, trips, agencies, calendars, and stop_times from the GTFS feed.
"""

import csv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
GTFS_DIR = os.path.join(BASE_DIR, "data/raw/london_gtfs")


def parse_csv(filename, limit=None):
    filepath = os.path.join(GTFS_DIR, filename)
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            rows.append(dict(row))
    return rows


def parse_agencies():
    return parse_csv("agency.txt")


def parse_stops():
    return parse_csv("stops.txt")


def parse_routes():
    return parse_csv("routes.txt")


def parse_trips(limit=None):
    return parse_csv("trips.txt", limit=limit)


def parse_calendar():
    return parse_csv("calendar.txt")


def parse_stop_times(limit=None):
    return parse_csv("stop_times.txt", limit=limit)


if __name__ == "__main__":
    agencies = parse_agencies()
    print(f"Agencies: {len(agencies)}")
    print(f"  Sample: {agencies[0]}")

    stops = parse_stops()
    print(f"Stops: {len(stops)}")
    print(f"  Sample: {stops[0]}")

    routes = parse_routes()
    print(f"Routes: {len(routes)}")
    print(f"  Sample: {routes[0]}")

    trips = parse_trips(limit=5)
    print(f"Trips (first 5): {len(trips)}")
    print(f"  Sample: {trips[0]}")

    calendar = parse_calendar()
    print(f"Calendar entries: {len(calendar)}")
    print(f"  Sample: {calendar[0]}")

    stop_times = parse_stop_times(limit=5)
    print(f"Stop times (first 5): {len(stop_times)}")
    print(f"  Sample: {stop_times[0]}")
