"""
RAG-based ABox relation population for the London Transport Knowledge Graph.

The canonical lt:line_* URIs (which have lt:lineColour and lt:modeOfTransport)
have zero or near-zero lt:servesStation links, and lt:intersectsWith uses string
literals rather than URIs. This script fixes that by generating:

  - lt:servesStation  (TransportLine → TrainStation)  — lines serving stations
  - lt:isServedBy     (TrainStation → TransportLine)  — inverse
  - lt:intersectsWith (TransportLine → TransportLine) — line-to-line URI links
  - lt:connectsTo     (Stop → Stop)                  — adjacent station pairs

The LLM is given the exact URIs from the KG as retrieval context (RAG).

Output: data/kg/rag_relations.ttl  (merged into final_submission_kg.ttl)

Usage:
  export GROQ_API_KEY="your-key"
  python src/kg/rag_populate_relations.py
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

from rdflib import Graph, Namespace, RDF, RDFS

REPO_ROOT = Path(__file__).resolve().parents[2]
FINAL_KG   = REPO_ROOT / "data" / "kg" / "final_submission_kg.ttl"
OUTPUT_TTL = REPO_ROOT / "data" / "kg" / "rag_relations.ttl"

LT   = Namespace("http://example.org/london-transport#")
GTFS = Namespace("http://vocab.gtfs.org/terms#")

GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Canonical named line URIs (have lt:lineColour from previous step) ──────────
CANONICAL_LINES = {
    "lt:line_bakerloo":         "Bakerloo line",
    "lt:line_central":          "Central line",
    "lt:line_circle":           "Circle line",
    "lt:line_district":         "District line",
    "lt:line_hammersmith-city": "Hammersmith & City line",
    "lt:line_jubilee":          "Jubilee line",
    "lt:line_metropolitan":     "Metropolitan line",
    "lt:line_northern":         "Northern line",
    "lt:line_piccadilly":       "Piccadilly line",
    "lt:line_victoria":         "Victoria line",
    "lt:line_waterloo-city":    "Waterloo & City line",
    "lt:line_elizabeth":        "Elizabeth line",
    "lt:line_dlr":              "DLR",
    "lt:line_tram":             "Tram",
    "lt:line_liberty":          "Liberty line (Overground)",
    "lt:line_lioness":          "Lioness line (Overground)",
    "lt:line_mildmay":          "Mildmay line (Overground)",
    "lt:line_suffragette":      "Suffragette line (Overground)",
    "lt:line_weaver":           "Weaver line (Overground)",
    "lt:line_windrush":         "Windrush line (Overground)",
}


def extract_context(g: Graph) -> tuple[str, str]:
    """Extract station URIs that already have lt:inFareZone (our 40 major stations)."""
    stations = []
    for s, _, _ in g.triples((None, LT.inFareZone, None)):
        label = g.value(s, RDFS.label) or ""
        uri = str(s).split("#")[-1]
        # only parent group stops
        if uri.startswith("stop_940G"):
            stations.append((f"lt:{uri}", str(label)))

    station_block = "\n".join(
        f'  {uri}  rdfs:label "{label}" .'
        for uri, label in sorted(stations)
    )
    lines_block = "\n".join(
        f'  {uri}  rdfs:label "{label}" .'
        for uri, label in CANONICAL_LINES.items()
    )
    return lines_block, station_block


def build_system_prompt() -> str:
    return (
        "You are an expert Knowledge Graph Engineer specialising in the London transport network. "
        "You have authoritative knowledge of which stations each TfL line serves and which lines "
        "intersect at which stations. "
        "You write strictly valid Turtle using only the URIs provided — never invent new URIs. "
        "You output ONLY a single fenced ```turtle ... ``` code block."
    )


def build_user_prompt(lines_block: str, station_block: str) -> str:
    return f"""
## Namespace
@prefix lt:   <http://example.org/london-transport#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

## Relevant Object Properties (already declared — do NOT redeclare)
- lt:servesStation   domain: lt:TransportLine,  range: lt:TrainStation
- lt:isServedBy      domain: lt:TrainStation,   range: lt:TransportLine
- lt:intersectsWith  domain: lt:TransportLine,  range: lt:TransportLine
- lt:connectsTo      domain: lt:Stop,           range: lt:Stop

## Canonical Transport Line URIs (from the KG)

{lines_block}

## Major Station URIs (from the KG — these already exist as instances)

{station_block}

## Task — Generate Relation Triples

Using your knowledge of the real London transport network, generate Turtle triples
that connect the lines above to the stations above. Follow these rules strictly:

### 1. lt:servesStation and lt:isServedBy
For each of the 11 numbered Tube lines and the Elizabeth line, generate:
  lt:<line_uri> lt:servesStation lt:<station_uri> .
  lt:<station_uri> lt:isServedBy lt:<line_uri> .
Only link a line to stations it ACTUALLY serves in real life.
Use ONLY station URIs from the list above. Do not invent station URIs.
Each tube line should link to at least 5 stations from the list.

### 2. lt:intersectsWith (line-to-line, using URIs)
For pairs of lines that share at least one station in the list above, generate:
  lt:<line_a> lt:intersectsWith lt:<line_b> .
  lt:<line_b> lt:intersectsWith lt:<line_a> .
Only use canonical line URIs from the list above.

### 3. lt:connectsTo (station-to-station)
For stations that are adjacent on the same line OR are well-known interchange points,
generate directional lt:connectsTo triples:
  lt:<station_a> lt:connectsTo lt:<station_b> .
Aim for at least 15 station pairs. Use only station URIs from the list above.

### Output Rules
- Output ONLY one ```turtle ... ``` fenced block with @prefix declarations at top.
- Use ONLY URIs provided above — never invent new ones.
- No comments, no prose outside the code block.
""".strip()


def extract_turtle(text: str) -> str:
    for pattern in [r"```turtle\s*\n(.*?)```", r"```\s*\n(.*?)```"]:
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return text.strip()


def run() -> None:
    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    try:
        from groq import Groq
    except ImportError:
        print("ERROR: pip install groq", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {FINAL_KG} ...")
    g = Graph()
    g.parse(str(FINAL_KG), format="turtle")
    print(f"  {len(g):,} triples loaded.")

    lines_block, station_block = extract_context(g)
    print(f"  Context: {len(CANONICAL_LINES)} lines, "
          f"{station_block.count('lt:stop')} stations")

    print(f"\nCalling Groq ({GROQ_MODEL}) ...")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user",   "content": build_user_prompt(lines_block, station_block)},
        ],
        temperature=0.1,
        max_tokens=4096,
    )

    raw = response.choices[0].message.content
    print("Response received.")

    ttl_str = extract_turtle(raw)

    print("\nValidating Turtle ...")
    try:
        new_g = Graph()
        new_g.parse(data=ttl_str, format="turtle")
        print(f"  Valid — {len(new_g)} new triples.")
    except Exception as e:
        print(f"WARNING: Turtle error: {e}", file=sys.stderr)

    OUTPUT_TTL.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_TTL.write_text(ttl_str, encoding="utf-8")
    print(f"Saved to {OUTPUT_TTL}")

    print(f"\nMerging into {FINAL_KG} ...")
    g.parse(data=ttl_str, format="turtle")
    g.serialize(destination=str(FINAL_KG), format="turtle")
    print(f"  Final KG: {len(g):,} triples.")
    print("Done.")


if __name__ == "__main__":
    run()
