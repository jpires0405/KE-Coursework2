"""
RAG-based ABox instance population for newly added ontology classes.

The RAG-completion script (rag_ontology_completion.py) added 8 new TBox elements
(FareZone, Borough, Interchange, modeOfTransport, lineColour, Fare, etc.) but
created no instances. This script:

  1. Reads final_submission_kg.ttl to extract named transport lines and major stations.
  2. Passes them to Llama-3.3-70b via Groq with an expert KG Engineer prompt.
  3. Instructs the LLM to generate ABox triples in valid Turtle that populate:
       - lt:lineColour  for all named lines
       - lt:modeOfTransport  for all named lines
       - lt:Borough instances (London boroughs) linked to sampled stations
       - lt:FareZone instances (TfL zones 1-9) linked to sampled stations
       - lt:Interchange typing for major multi-modal stations
  4. Saves output to data/kg/rag_instances.ttl.
  5. Merges rag_instances.ttl into final_submission_kg.ttl.

Usage:
  export GROQ_API_KEY="your-key"
  python src/kg/rag_populate_instances.py
"""

import os
import re
import sys
from pathlib import Path

from rdflib import Graph, Namespace, RDF, RDFS

REPO_ROOT = Path(__file__).resolve().parents[2]
FINAL_KG = REPO_ROOT / "data" / "kg" / "final_submission_kg.ttl"
INSTANCES_OUT = REPO_ROOT / "data" / "kg" / "rag_instances.ttl"

LT = Namespace("http://example.org/london-transport#")

GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Named lines we want to populate (extracted from KG exploration) ────────────
NAMED_LINES = {
    # Tube lines
    "lt:line_bakerloo":        ("TubeLine",        "Bakerloo line"),
    "lt:line_central":         ("TubeLine",        "Central line"),
    "lt:line_circle":          ("TubeLine",        "Circle line"),
    "lt:line_district":        ("TubeLine",        "District line"),
    "lt:line_hammersmith-city":("TubeLine",        "Hammersmith & City line"),
    "lt:line_jubilee":         ("TubeLine",        "Jubilee line"),
    "lt:line_metropolitan":    ("TubeLine",        "Metropolitan line"),
    "lt:line_northern":        ("TubeLine",        "Northern line"),
    "lt:line_piccadilly":      ("TubeLine",        "Piccadilly line"),
    "lt:line_victoria":        ("TubeLine",        "Victoria line"),
    "lt:line_waterloo-city":   ("TubeLine",        "Waterloo & City line"),
    # Elizabeth / DLR / Tram / River Bus
    "lt:line_elizabeth":       ("ElizabethLine",   "Elizabeth line"),
    "lt:line_dlr":             ("DLRLine",         "DLR"),
    "lt:line_tram":            ("TramLine",        "Tram"),
    "lt:line_rb1":             ("RiverBusLine",    "RB1"),
    "lt:line_rb2":             ("RiverBusLine",    "RB2"),
    "lt:line_rb4":             ("RiverBusLine",    "RB4"),
    "lt:line_rb6":             ("RiverBusLine",    "RB6"),
    # Overground named lines
    "lt:line_liberty":         ("OvergroundLine",  "Liberty line"),
    "lt:line_lioness":         ("OvergroundLine",  "Lioness line"),
    "lt:line_mildmay":         ("OvergroundLine",  "Mildmay line"),
    "lt:line_suffragette":     ("OvergroundLine",  "Suffragette line"),
    "lt:line_weaver":          ("OvergroundLine",  "Weaver line"),
    "lt:line_windrush":        ("OvergroundLine",  "Windrush line"),
}

# ── Major interchange stations (parent group stops, known interchanges) ────────
MAJOR_STATIONS = [
    ("lt:stop_940GZZLUKSX", "King's Cross St. Pancras"),
    ("lt:stop_940GZZLUVIC", "Victoria"),
    ("lt:stop_940GZZLULBG", "London Bridge"),
    ("lt:stop_940GZZLUWLO", "Waterloo"),
    ("lt:stop_940GZZLUSRA", "Stratford"),
    ("lt:stop_940GZZLUPAC", "Paddington"),
    ("lt:stop_940GZZLULMN", "Liverpool Street"),
    ("lt:stop_940GZZLUCST", "Cannon Street"),
    ("lt:stop_940GZZLUBKF", "Blackfriars"),
    ("lt:stop_940GZZLUMGT", "Moorgate"),
    ("lt:stop_940GZZLUBNK", "Bank / Monument"),
    ("lt:stop_940GZZLUCXR", "Charing Cross"),
    ("lt:stop_940GZZLUEUS", "Euston"),
    ("lt:stop_940GZZLUWYP", "Warren Street"),
    ("lt:stop_940GZZLUGPK", "Green Park"),
    ("lt:stop_940GZZLUOXC", "Oxford Circus"),
    ("lt:stop_940GZZLUTCR", "Tottenham Court Road"),
    ("lt:stop_940GZZLUHBN", "Highbury & Islington"),
    ("lt:stop_940GZZLUSVS", "Seven Sisters"),
    ("lt:stop_940GZZLUFPK", "Finsbury Park"),
    ("lt:stop_940GZZLUWHP", "Whitechapel"),
    ("lt:stop_940GZZLUELY", "Elephant & Castle"),
    ("lt:stop_940GZZLUCPK", "Clapham Junction"),
    ("lt:stop_940GZZLUSHP", "Shepherd's Bush"),
    ("lt:stop_940GZZLUHSD", "Hammersmith"),
    ("lt:stop_940GZZLUGNR", "Gunnersbury"),
    ("lt:stop_940GZZLUWIM", "Wimbledon"),
    ("lt:stop_940GZZLURMD", "Richmond"),
    ("lt:stop_940GZZLUBXN", "Brixton"),
    ("lt:stop_940GZZLUCAM", "Camden Town"),
    ("lt:stop_940GZZLUACT", "Acton Town"),
    ("lt:stop_940GZZLUALD", "Aldgate"),
    ("lt:stop_940GZZLUADE", "Aldgate East"),
    ("lt:stop_940GZZLUAGL", "Angel"),
    ("lt:stop_940GZZLUBST", "Baker Street"),
    ("lt:stop_940GZZLUBND", "Bond Street"),
    ("lt:stop_940GZZLUWSP", "Wembley Park"),
    ("lt:stop_940GZZLUSKS", "South Kensington"),
    ("lt:stop_940GZZLUKNB", "Knightsbridge"),
    ("lt:stop_940GZZLUHSC", "Holborn"),
]


def extract_kg_context(g: Graph) -> str:
    """Build a concise summary of lines and stations for the LLM prompt."""
    lines_block = "\n".join(
        f"  {uri} a lt:{cls} ; rdfs:label \"{label}\" ."
        for uri, (cls, label) in NAMED_LINES.items()
    )
    stations_block = "\n".join(
        f"  {uri} a lt:TrainStation ; rdfs:label \"{label}\" ."
        for uri, label in MAJOR_STATIONS
    )
    return f"### Named Transport Lines\n{lines_block}\n\n### Major Stations\n{stations_block}"


def build_system_prompt() -> str:
    return (
        "You are an expert Knowledge Graph Engineer for the London Transport domain. "
        "You write ABox instance triples in strictly valid Turtle syntax. "
        "You use only URIs and properties already declared in the ontology. "
        "You never invent new classes or properties — only new instances and literal values. "
        "You output ONLY a single fenced ```turtle ... ``` code block with no prose outside it."
    )


def build_user_prompt(kg_context: str) -> str:
    return f"""
## Ontology Namespace

All URIs use: `@prefix lt: <http://example.org/london-transport#> .`
Key new classes and properties added by a previous RAG step:
- `lt:FareZone`         (class, subClassOf lt:TransportEntity)
- `lt:Borough`          (class, subClassOf lt:Place)
- `lt:Interchange`      (class, subClassOf lt:Stop)
- `lt:Fare`             (class, subClassOf lt:TransportEntity)
- `lt:FareTier`         (class, subClassOf lt:Fare)
- `lt:modeOfTransport`  (ObjectProperty, domain lt:Route, range lt:TransportEntity)
- `lt:lineColour`       (DatatypeProperty, domain lt:TransportLine, range xsd:string)
- `lt:inFareZone`       (ObjectProperty — use this to link stops to fare zones)
- `lt:locatedIn`        (ObjectProperty — use this to link stops to boroughs)

## Existing KG Entities (extracted programmatically)

{kg_context}

## Task — Generate ABox Instance Triples

Produce Turtle triples that populate the new ontology classes. Specifically:

### 1. Line Colours and Modes of Transport
For EVERY named transport line listed above, add:
- `lt:lineColour` with the official TfL hex colour code (e.g. "#AE2069" for Hammersmith & City)
- `lt:modeOfTransport` pointing to a plain literal or a new lt: instance describing the mode
  (e.g. `lt:mode_tube`, `lt:mode_bus`, `lt:mode_dlr`, `lt:mode_tram`, `lt:mode_river_bus`, `lt:mode_overground`, `lt:mode_elizabeth_line`)
  Declare each mode instance as `a lt:TransportEntity ; rdfs:label "..."`.

### 2. Fare Zone Instances
Create instances for TfL fare zones 1 through 6 (zones 7-9 exist but are minor):
- URIs: `lt:fare_zone_1` through `lt:fare_zone_6`
- Type: `lt:FareZone`
- Add `rdfs:label` and `lt:name` literals

Then link each of the sampled stations to a realistic fare zone using `lt:inFareZone`.
Use your knowledge of London geography to assign correct zones.

### 3. Borough Instances
Create `lt:Borough` instances for these London boroughs (at minimum):
City of London, Westminster, Camden, Islington, Hackney, Tower Hamlets,
Southwark, Lambeth, Wandsworth, Hammersmith and Fulham, Kensington and Chelsea,
Ealing, Newham, Stratford, Greenwich.
- URIs: e.g. `lt:borough_westminster`, `lt:borough_camden`, etc.
- Type: `lt:Borough` ; add `rdfs:label` and `lt:name`

Then link each sampled station to its correct borough using `lt:locatedIn`.

### 4. Interchange Classification
For the following stations which are confirmed major multi-modal interchanges,
add an additional `rdf:type lt:Interchange` triple:
King's Cross St. Pancras, Victoria, London Bridge, Waterloo, Stratford,
Paddington, Liverpool Street, Waterloo, Whitechapel, Clapham Junction,
Highbury & Islington, Hammersmith.

### Output Rules
- Output ONLY one ```turtle ... ``` fenced block.
- Include `@prefix` declarations at the top: lt, rdf, rdfs, owl, xsd.
- Do NOT redeclare existing classes or properties — only add new instance triples.
- All string literals must be properly quoted.
- Every new resource must have at least `rdf:type` and `rdfs:label`.
""".strip()


def extract_turtle(text: str) -> str:
    for pattern in [r"```turtle\s*\n(.*?)```", r"```\s*\n(.*?)```"]:
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return text.strip()


def run() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    try:
        from groq import Groq
    except ImportError:
        print("ERROR: groq not installed. Run: pip install groq", file=sys.stderr)
        sys.exit(1)

    # ── Load KG and build context ──────────────────────────────────────────────
    print(f"Loading {FINAL_KG} ...")
    g = Graph()
    g.parse(str(FINAL_KG), format="turtle")
    print(f"  {len(g):,} triples loaded.")

    kg_context = extract_kg_context(g)

    # ── Call Groq ──────────────────────────────────────────────────────────────
    print(f"\nCalling Groq ({GROQ_MODEL}) ...")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user",   "content": build_user_prompt(kg_context)},
        ],
        temperature=0.1,
        max_tokens=4096,
    )

    raw = response.choices[0].message.content
    print("Response received.")

    # ── Extract and validate Turtle ────────────────────────────────────────────
    ttl_str = extract_turtle(raw)
    print("\nValidating Turtle ...")
    try:
        new_g = Graph()
        new_g.parse(data=ttl_str, format="turtle")
        print(f"  Valid — {len(new_g)} new triples.")
    except Exception as e:
        print(f"WARNING: Turtle parse error: {e}", file=sys.stderr)
        print("Saving raw output for inspection.")

    # ── Save new instances ─────────────────────────────────────────────────────
    INSTANCES_OUT.parent.mkdir(parents=True, exist_ok=True)
    INSTANCES_OUT.write_text(ttl_str, encoding="utf-8")
    print(f"Saved instances to {INSTANCES_OUT}")

    # ── Merge back into final_submission_kg.ttl ────────────────────────────────
    print(f"\nMerging into {FINAL_KG} ...")
    g.parse(data=ttl_str, format="turtle")
    g.serialize(destination=str(FINAL_KG), format="turtle")
    print(f"  Final KG now has {len(g):,} triples.")
    print("Done.")


if __name__ == "__main__":
    run()
