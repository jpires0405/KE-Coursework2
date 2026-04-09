"""
python -m src.evaluation.evaluate
python -m src.evaluation.evaluate --kg data/kg/final_submission_kg.ttl
python -m src.evaluation.evaluate --kg data/kg/completed_kg.ttl
"""

import argparse
import json
import re
import time
import tracemalloc
from collections import OrderedDict
from pathlib import Path

from rdflib import Graph, Namespace, RDF, RDFS

LT = Namespace("http://example.org/london-transport#")
GTFS = Namespace("http://vocab.gtfs.org/terms#")
SCHEMA = Namespace("https://schema.org/")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KG = REPO_ROOT / "data" / "kg" / "final_submission_kg.ttl"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "evaluation" / "evaluation_report.json"

# Try a few import locations for competency questions
try:
    from src.sparql.competency import competency_questions, PREFIXES  # type: ignore
except ImportError:
    try:
        from .competency import competency_questions, PREFIXES  # type: ignore
    except ImportError:
        competency_questions = []
        PREFIXES = ""


def short_name(uri) -> str:
    return re.split(r"[#/]", str(uri))[-1]


TRACKED_CLASSES = OrderedDict({
    LT.TransportEntity: "TransportEntity",
    LT.Report: "Report",
    LT.Statistic: "Statistic",
    SCHEMA.Place: "Place",
    SCHEMA.Organization: "Organization",
    GTFS.Stop: "Stop",
    LT.BusStop: "BusStop",
    LT.TrainStation: "TrainStation",
    GTFS.Route: "Route",
    LT.BusRoute: "BusRoute",
    LT.TrainRoute: "TrainRoute",
    GTFS.Service: "Service",
    GTFS.Trip: "Trip",
    GTFS.StopTime: "StopTime",
    LT.TransportLine: "TransportLine",
    LT.BusLine: "BusLine",
    LT.TubeLine: "TubeLine",
    LT.DLRLine: "DLRLine",
    LT.OvergroundLine: "OvergroundLine",
    LT.ElizabethLine: "ElizabethLine",
    LT.TramLine: "TramLine",
    LT.RiverBusLine: "RiverBusLine",
    LT.NationalRailLine: "NationalRailLine",
    LT.TransportOperator: "TransportOperator",
})

REQUIRED_PROPERTIES = OrderedDict({
    LT.Report: [LT.name, RDFS.label],
    LT.Statistic: [LT.name, RDFS.label],
    SCHEMA.Place: [LT.name, RDFS.label],
    LT.TransportOperator: [LT.operatorName, RDFS.label],
    LT.BusStop: [LT.name, RDFS.label, GTFS.lat, GTFS.long, LT.wheelchairAccessible],
    LT.TrainStation: [LT.name, RDFS.label, GTFS.lat, GTFS.long, LT.wheelchairAccessible],
    GTFS.Route: [RDFS.label],
    LT.BusRoute: [LT.busRouteNumber, LT.name, RDFS.label, LT.operatedBy],
    LT.TrainRoute: [LT.routeNumber, LT.name, RDFS.label, LT.operatedBy],
    LT.TransportLine: [LT.lineName, RDFS.label],
    LT.TubeLine: [LT.lineName, RDFS.label],
    LT.BusLine: [LT.lineName, RDFS.label],
    LT.DLRLine: [LT.lineName, RDFS.label],
    LT.OvergroundLine: [LT.lineName, RDFS.label],
    LT.ElizabethLine: [LT.lineName, RDFS.label],
    LT.TramLine: [LT.lineName, RDFS.label],
    LT.RiverBusLine: [LT.lineName, RDFS.label],
    LT.NationalRailLine: [LT.lineName, RDFS.label],
    GTFS.Service: [LT.startDate, LT.endDate],
    GTFS.Trip: [LT.onRoute, LT.belongsToService],
    GTFS.StopTime: [GTFS.arrivalTime, GTFS.departureTime, LT.stopsAt, LT.onTrip],
})

SOURCE_METRICS = OrderedDict({
    "report_linked_entities": """
        SELECT (COUNT(DISTINCT ?s) AS ?count)
        WHERE { ?s lt:mentionedInReport ?r . }
    """,
    "transport_lines_with_routes": """
        SELECT (COUNT(DISTINCT ?line) AS ?count)
        WHERE { ?line a lt:TransportLine ; lt:hasRoute ?route . }
    """,
    "routes_with_operators": """
        SELECT (COUNT(DISTINCT ?route) AS ?count)
        WHERE { ?route a gtfs:Route ; lt:operatedBy ?op . }
    """,
    "stations_with_serving_routes": """
        SELECT (COUNT(DISTINCT ?station) AS ?count)
        WHERE { ?route lt:servesStation ?station . }
    """,
    "lines_mentioned_in_report": """
        SELECT (COUNT(DISTINCT ?line) AS ?count)
        WHERE { ?line a lt:TransportLine ; lt:mentionedInReport ?report . }
    """,
})

NS = {
    "lt": LT,
    "gtfs": GTFS,
    "schema": SCHEMA,
    "rdf": RDF,
    "rdfs": RDFS,
}


def load_graph_with_metrics(kg_path: Path):
    if not kg_path.exists():
        raise FileNotFoundError(f"KG file not found: {kg_path}")

    file_size_mb = kg_path.stat().st_size / (1024 ** 2)

    tracemalloc.start()
    t_start = time.perf_counter()

    g = Graph()
    g.parse(str(kg_path), format="turtle")

    t_end = time.perf_counter()
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return g, {
        "kg_file": str(kg_path),
        "file_size_mb": round(file_size_mb, 2),
        "parse_time_s": round(t_end - t_start, 3),
        "peak_memory_mb": round(peak_bytes / (1024 ** 2), 2),
        "total_triples": len(g),
    }


def evaluate_class_distribution(g: Graph):
    distribution = OrderedDict()
    for cls, label in TRACKED_CLASSES.items():
        count = len(set(g.subjects(RDF.type, cls)))
        distribution[label] = count
    return distribution


def evaluate_completeness(g: Graph):
    completeness = OrderedDict()

    for cls, properties in REQUIRED_PROPERTIES.items():
        class_label = short_name(cls)
        instances = list(set(g.subjects(RDF.type, cls)))
        total_instances = len(instances)

        prop_stats = OrderedDict()
        for prop in properties:
            prop_label = short_name(prop)
            if total_instances == 0:
                prop_stats[prop_label] = {
                    "count": 0,
                    "percent": None,
                }
                continue

            count_with_prop = sum(1 for inst in instances if (inst, prop, None) in g)
            prop_stats[prop_label] = {
                "count": count_with_prop,
                "percent": round((count_with_prop / total_instances) * 100, 1),
            }

        completeness[class_label] = {
            "instance_count": total_instances,
            "properties": prop_stats,
        }

    return completeness


def run_scalar_query(g: Graph, query: str):
    try:
        qres = g.query(query, initNs=NS)
        rows = list(qres)
        if not rows:
            return 0
        first = rows[0][0]
        try:
            return int(first)
        except (TypeError, ValueError):
            try:
                return float(first)
            except (TypeError, ValueError):
                return str(first)
    except Exception as e:
        return f"ERROR: {e}"


def evaluate_source_metrics(g: Graph):
    results = OrderedDict()
    for name, query in SOURCE_METRICS.items():
        results[name] = run_scalar_query(g, query)
    return results


def evaluate_queries(g: Graph):
    results = []
    answered = 0
    successes = 0
    total_time = 0.0

    for cq in competency_questions:
        qid = cq.get("id", "UNKNOWN")
        question_text = cq.get("question", "")
        query_text = cq.get("query", "")

        start = time.perf_counter()
        try:
            qres = g.query(PREFIXES + query_text)
            rows = list(qres)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 4)

            result_count = len(rows)
            success = True
            is_answered = result_count > 0

            if success:
                successes += 1
            if is_answered:
                answered += 1
            total_time += elapsed_ms

            results.append({
                "id": qid,
                "question": question_text,
                "time_ms": elapsed_ms,
                "result_count": result_count,
                "success": success,
                "answered": is_answered,
                "error": None,
            })
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 4)
            total_time += elapsed_ms
            results.append({
                "id": qid,
                "question": question_text,
                "time_ms": elapsed_ms,
                "result_count": 0,
                "success": False,
                "answered": False,
                "error": str(e),
            })

    total = len(competency_questions)
    summary = {
        "total_queries": total,
        "successful_queries": successes,
        "answered_queries": answered,
        "success_rate_percent": round((successes / total) * 100, 1) if total else None,
        "answer_rate_percent": round((answered / total) * 100, 1) if total else None,
        "average_time_ms": round(total_time / total, 4) if total else None,
    }

    return {
        "summary": summary,
        "details": results,
    }


def evaluate(kg_path: Path):
    g, performance = load_graph_with_metrics(kg_path)

    return {
        "performance": performance,
        "class_distribution": evaluate_class_distribution(g),
        "completeness": evaluate_completeness(g),
        "source_metrics": evaluate_source_metrics(g),
        "queries": evaluate_queries(g),
    }


def print_report(results: dict):
    sep = "─" * 68
    perf = results["performance"]
    query_summary = results["queries"]["summary"]

    print(sep)
    print("London Transport KG — Evaluation Report")
    print(sep)
    print(f"File            : {Path(perf['kg_file']).name}")
    print(f"File size       : {perf['file_size_mb']} MB")
    print(f"Parse time      : {perf['parse_time_s']} s")
    print(f"Peak memory     : {perf['peak_memory_mb']} MB")
    print(f"Total triples   : {perf['total_triples']:,}")

    print(sep)
    print("Tracked class distribution")
    print(sep)
    for cls_name, count in results["class_distribution"].items():
        print(f"{cls_name:24} {count}")

    print(sep)
    print("Baseline completeness")
    print(sep)
    for cls_name, stats in results["completeness"].items():
        print(f"\n{cls_name} (instances: {stats['instance_count']})")
        for prop_name, prop_stats in stats["properties"].items():
            percent = prop_stats["percent"]
            if percent is None:
                percent_display = "N/A"
            else:
                percent_display = f"{percent}%"
            print(f"  {prop_name:22} {prop_stats['count']:>8}  {percent_display}")

    print(sep)
    print("Source / integration metrics")
    print(sep)
    for name, value in results["source_metrics"].items():
        print(f"{name:28} {value}")

    print(sep)
    print("Competency query summary")
    print(sep)
    print(f"Total queries    : {query_summary['total_queries']}")
    print(f"Successful       : {query_summary['successful_queries']}")
    print(f"Answered         : {query_summary['answered_queries']}")
    print(f"Success rate     : {query_summary['success_rate_percent']}%")
    print(f"Answer rate      : {query_summary['answer_rate_percent']}%")
    print(f"Average time     : {query_summary['average_time_ms']} ms")

    print(sep)
    print("Competency query details")
    print(sep)
    print("ID    Answered  Success  Results  Time(ms)")
    for item in results["queries"]["details"]:
        print(
            f"{item['id']:<5} "
            f"{str(item['answered']):<8} "
            f"{str(item['success']):<7} "
            f"{item['result_count']:<7} "
            f"{item['time_ms']}"
        )


def main():
    parser = argparse.ArgumentParser(description="Evaluate the London Transport KG.")
    parser.add_argument(
        "--kg",
        type=Path,
        default=DEFAULT_KG,
        help="Path to the Turtle KG file (default: data/kg/final_submission_kg.ttl)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to write the JSON report (default: data/evaluation/evaluation_report.json)",
    )
    args = parser.parse_args()

    print(f"Loading {args.kg} ...")
    results = evaluate(args.kg)
    print_report(results)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved JSON report to {args.output}")


if __name__ == "__main__":
    main()