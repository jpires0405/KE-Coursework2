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

from rdflib import Graph

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KG = REPO_ROOT / "data" / "kg" / "final_submission_kg.ttl"


def evaluate(kg_path: Path) -> dict:
    if not kg_path.exists():
        raise FileNotFoundError(f"KG file not found: {kg_path}")

    file_size_mb = kg_path.stat().st_size / (1024 ** 2)

    # ── Parse time + peak memory ───────────────────────────────────────────────
    tracemalloc.start()
    t_start = time.perf_counter()

    g = Graph()
    g.parse(str(kg_path), format="turtle")

    t_end = time.perf_counter()
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "kg_file":        str(kg_path),
        "file_size_mb":   round(file_size_mb, 2),
        "parse_time_s":   round(t_end - t_start, 3),
        "peak_memory_mb": round(peak_bytes / (1024 ** 2), 2),
        "total_triples":  len(g),
    }


def print_report(results: dict) -> None:
    sep = "─" * 52
    print(sep)
    print("  London Transport KG — Performance Evaluation")
    print(sep)
    print(f"  File            : {Path(results['kg_file']).name}")
    print(f"  File size       : {results['file_size_mb']} MB")
    print(f"  Parse time      : {results['parse_time_s']} s")
    print(f"  Peak memory     : {results['peak_memory_mb']} MB")
    print(f"  Total triples   : {results['total_triples']:,}")
    print(sep)


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
