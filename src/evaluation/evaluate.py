"""
Performance evaluation for the London Transport Knowledge Graph.

Measures:
  - Parse time       : wall-clock seconds to load the TTL file into rdflib
  - Peak memory      : peak RAM usage during loading (tracemalloc)
  - Total triples    : number of RDF triples in the loaded graph

Usage:
  python src/evaluation/evaluate.py
  python src/evaluation/evaluate.py --kg path/to/other.ttl
"""

import argparse
import time
import tracemalloc
from pathlib import Path
import re
from collections import Counter
from competency import competency_questions, PREFIXES
from rdflib import Graph, Namespace, RDF, RDFS

LT = Namespace("http://example.org/london-transport#")
GTFS = Namespace("http://vocab.gtfs.org/terms#")
SCHEMA = Namespace("https://schema.org/")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KG = REPO_ROOT / "data" / "kg" / "final_submission_kg.ttl"


required_properties = {
    LT.Report: [LT.name, RDFS.label],
    LT.Statistic: [LT.name, RDFS.label],
    SCHEMA.Place: [LT.name, RDFS.label],
    LT.TransportOperator: [LT.operatorName, LT.name, RDFS.label, SCHEMA.url, LT.mentionedInReport],
    LT.BusStop: [LT.name, RDFS.label, GTFS.lat, GTFS.long, LT.naptanCode, LT.wheelchairAccessible, LT.connectsTo, LT.isStopOn],
    LT.TrainStation: [LT.name, RDFS.label, GTFS.lat, GTFS.long, LT.wheelchairAccessible, LT.mentionedInReport, LT.isStopOn, LT.connectsTo],
    GTFS.Route: [LT.name, RDFS.label, LT.mentionedInReport],
    LT.BusRoute: [LT.busRouteNumber, LT.name, RDFS.label, LT.operatedBy, LT.hasStop, LT.hasTrip, LT.servesStation],
    LT.TrainRoute: [LT.routeNumber, LT.name, RDFS.label, LT.mentionedInReport, LT.operatedBy, LT.hasStop, LT.hasTrip, LT.servesStation],
    LT.TransportLine: [LT.lineName, RDFS.label, LT.hasStatus, LT.isDisrupted, LT.hasNightService, LT.extendsTo, LT.mentionedInReport, LT.hasStopName, LT.description],
    LT.TubeLine: [LT.lineName, RDFS.label, LT.hasStatus, LT.isDisrupted, LT.mentionedInReport, LT.hasNightService, LT.extendsTo, LT.hasStopName],
    LT.BusLine: [LT.lineName, RDFS.label, LT.hasStatus, LT.isDisrupted, LT.mentionedInReport, LT.extendsTo, LT.hasStopName],
    LT.DLRLine: [LT.lineName, RDFS.label, LT.hasStatus, LT.isDisrupted, LT.mentionedInReport, LT.extendsTo, LT.hasStopName],
    LT.OvergroundLine: [LT.lineName, RDFS.label, LT.hasStatus, LT.isDisrupted, LT.mentionedInReport, LT.extendsTo, LT.hasStopName],
    LT.ElizabethLine: [LT.lineName, RDFS.label, LT.hasStatus, LT.isDisrupted, LT.mentionedInReport, LT.extendsTo, LT.hasStopName],
    LT.TramLine: [LT.lineName, RDFS.label, LT.hasStatus, LT.isDisrupted, LT.mentionedInReport, LT.extendsTo, LT.hasStopName],
    LT.RiverBusLine: [LT.lineName, RDFS.label, LT.hasStatus, LT.isDisrupted, LT.mentionedInReport, LT.extendsTo, LT.hasStopName],
    LT.NationalRailLine: [LT.lineName, RDFS.label, LT.hasStatus, LT.isDisrupted, LT.extendsTo, LT.hasStopName],
    GTFS.Service: [LT.startDate, LT.endDate],
    GTFS.Trip: [GTFS.headsign, RDFS.label, LT.onRoute, LT.belongsToService],
    GTFS.StopTime: [GTFS.arrivalTime, GTFS.departureTime, LT.stopsAt, LT.onTrip],
    LT.TransportEntity: [RDFS.label, LT.description, LT.mentionedInReport],
    LT.Fare: [RDFS.label, LT.value],
    LT.FareTier: [RDFS.label, RDFS.subClassOf],
    LT.AccessibilityFeature: [RDFS.label, LT.description],
    LT.StepFreeAccess: [RDFS.label, RDFS.subClassOf],
    LT.Disruption: [LT.disruptionReason, LT.description, LT.aboutLine]
}

def evaluate(kg_path: Path) -> dict:
    if not kg_path.exists():
        raise FileNotFoundError(f"KG file not found: {kg_path}")

    file_size_mb = kg_path.stat().st_size / (1024 ** 2)

    print("Checking Parse Time")
    # ── Parse time + peak memory ───────────────────────────────────────────────
    tracemalloc.start()
    t_start = time.perf_counter()

    g = Graph()
    g.parse(str(kg_path), format="turtle")

    t_end = time.perf_counter()

    print("Checking Peak Memory")
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print("Checking Class Distribution")
    # Class distribution
    type_counters = Counter(g.objects(None, RDF.type))

    class_dist = {}
    for i, count in type_counters.items():
        name = str(re.split(r"[#/]", i)[-1])
        class_dist[name] = count
    sorted_dict = sorted(class_dist.items(), key=lambda x: x[1], reverse=True)

    print("Checking Completeness")
    # Measures the amount of instances that have required properties
    completeness = {}
    for classes, properties in required_properties.items():
        instances = list(g.subjects(RDF.type, classes))
        stats = {}
        for prop in properties:
            count_with_prop = 0
            for i in instances:
                if (i, prop, None) in g:
                    count_with_prop += 1
                stats[str(re.split(r"[#/]", prop)[-1])] = round(count_with_prop/len(instances) * 100, 1)

        completeness[str(re.split(r"[#/]", classes)[-1])] = {
            "prop": stats
        }

    print("Checking Query Time")
    # Measures Query Time
    query_stats = []
    for i in competency_questions:
        start = time.perf_counter()
        results = g.query(PREFIXES + i["query"])
        end = time.perf_counter()
        query_stats.append({
            "id": i["id"],
            "time_ms": round((end-start)*1000, 4)
        })

    return {
        "kg_file":        str(kg_path),
        "file_size_mb":   round(file_size_mb, 2),
        "parse_time_s":   round(t_end - t_start, 3),
        "peak_memory_mb": round(peak_bytes / (1024 ** 2), 2),
        "total_triples":  len(g),
        "class_distribution": dict(sorted_dict),
        "completeness": completeness,
        "queries": query_stats
    }


def print_report(results: dict) -> None:
    sep = "─" * 52
    print(sep)
    print("  London Transport KG — Performance Evaluation")
    print(sep)
    print(f"\n  Class Distribution:")

    for i, count in results["class_distribution"].items():
        print(f"  {i}: {count}")
    print(sep)

    print(f"\n  Property Completeness:")
    print(f"  Class Name | Property")

    for i, j in results["completeness"].items():
        print(f"\n  {i}")
        for prop, percent in j["prop"].items():
            print(f"  {prop} | {percent}%")

    print(sep)
    print(f"  ID  | Time(ms)")
    for i in results["queries"]:
        print(f"  {i['id']} | {i["time_ms"]}")
    
    print(sep)
    print(f"  File            : {Path(results['kg_file']).name}")
    print(f"  File size       : {results['file_size_mb']} MB")
    print(f"  Parse time      : {results['parse_time_s']} s")
    print(f"  Peak memory     : {results['peak_memory_mb']} MB")
    print(f"  Total triples   : {results['total_triples']:,}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate KG loading performance.")
    parser.add_argument(
        "--kg",
        type=Path,
        default=DEFAULT_KG,
        help="Path to the Turtle KG file (default: data/kg/final_submission_kg.ttl)",
    )
    args = parser.parse_args()

    print(f"Loading {args.kg} ...")
    results = evaluate(args.kg)
    print_report(results)


if __name__ == "__main__":
    main()
