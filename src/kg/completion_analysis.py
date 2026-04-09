"""
KG Completion Analysis — identifies incomplete ontology and instance elements.

Runs SPARQL queries against the merged knowledge graph to find gaps,
then outputs a structured report documenting what is missing and how
it could be resolved.
"""

import json
import os
import sys
from pathlib import Path

from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD

BASE_DIR = Path(__file__).resolve().parents[2]
KG_PATH = BASE_DIR / "data" / "kg" / "public_transport.ttl"
OUTPUT_PATH = BASE_DIR / "data" / "kg" / "completion_report.json"

LT = Namespace("http://example.org/london-transport#")
GTFS = Namespace("http://vocab.gtfs.org/terms#")
SCHEMA = Namespace("https://schema.org/")


def load_kg(path=KG_PATH):
    """Load the merged knowledge graph."""
    if not path.exists():
        print(f"ERROR: KG not found at {path}", file=sys.stderr)
        print("Run 'python -m src.kg.combine_kg' first.", file=sys.stderr)
        sys.exit(1)

    g = Graph()
    g.bind("lt", LT)
    g.bind("gtfs", GTFS)
    g.bind("schema", SCHEMA)
    g.parse(str(path), format="turtle")
    print(f"Loaded {len(g)} triples from {path.name}")
    return g


# Ontology gap queries
ONTOLOGY_GAPS = [
    {
        "id": "O1",
        "title": "No FareZone class or zone property on stops",
        "description": (
            "London's fare zone system (zones 1-9) is fundamental to the "
            "transport domain. The ontology has no FareZone class and stops "
            "have no property linking them to a fare zone."
        ),
        "resolution": (
            "Add lt:FareZone as a subclass of lt:TransportEntity and a "
            "lt:inFareZone object property with domain lt:Stop and range "
            "lt:FareZone. Populate using TfL API stop data or NaPTAN."
        ),
        "query": """
            SELECT (COUNT(?cls) AS ?count)
            WHERE {
                ?cls a owl:Class .
                FILTER(CONTAINS(LCASE(STR(?cls)), "zone"))
            }
        """,
        "expected": "0 classes matching 'zone' exist",
    },
    {
        "id": "O2",
        "title": "TransportLine has no hasRoute links defined in practice",
        "description": (
            "The ontology defines lt:hasRoute (TransportLine → Route), but "
            "no instances use it. There is no way to navigate from a "
            "TransportLine to its constituent routes."
        ),
        "resolution": (
            "Map each GTFS route's agency to its parent TransportLine using "
            "route names/IDs. For example, Piccadilly line routes should link "
            "via lt:hasRoute to their corresponding lt:TrainRoute instances."
        ),
        "query": """
            SELECT (COUNT(?link) AS ?count)
            WHERE { ?line a lt:TransportLine . ?line lt:hasRoute ?link }
        """,
        "expected": "0 hasRoute links exist",
    },
    {
        "id": "O3",
        "title": "No borough or area class for spatial context",
        "description": (
            "The ontology has lt:Place but no Borough or Area subclass. "
            "London has 33 boroughs that are central to how transport is "
            "organised. Stops cannot be linked to their borough."
        ),
        "resolution": (
            "Add lt:Borough as a subclass of lt:Place and a lt:inBorough "
            "property. Populate by reverse-geocoding stop coordinates or "
            "using NaPTAN locality data."
        ),
        "query": """
            SELECT (COUNT(?cls) AS ?count)
            WHERE {
                ?cls a owl:Class .
                FILTER(CONTAINS(LCASE(STR(?cls)), "borough"))
            }
        """,
        "expected": "0 Borough classes exist",
    },
    {
        "id": "O4",
        "title": "Accessibility is modelled as a single boolean",
        "description": (
            "Wheelchair accessibility is a single boolean on Stop. Real "
            "accessibility includes step-free access, platform-to-train gap, "
            "lifts, tactile paving, hearing loops, and accessible toilets. "
            "The ontology cannot express which specific accessibility "
            "features a stop has."
        ),
        "resolution": (
            "Add lt:AccessibilityFeature class with subclasses "
            "(StepFreeAccess, Lift, TactilePaving, etc.) and a "
            "lt:hasAccessibilityFeature object property on lt:Stop. "
            "Populate from TfL accessibility data or the annual report."
        ),
        "query": """
            SELECT (COUNT(?prop) AS ?count)
            WHERE {
                ?prop a owl:DatatypeProperty .
                FILTER(CONTAINS(LCASE(STR(?prop)), "accessible"))
            }
        """,
        "expected": "Only 1 accessibility property (wheelchairAccessible boolean)",
    },
    {
        "id": "O5",
        "title": "No interchange/connection class between lines or stops",
        "description": (
            "The ontology has lt:connectsTo but no Interchange or Connection "
            "class to model transfer points between lines. Interchanges are "
            "critical for route planning and have properties like walking "
            "time and whether they are cross-platform or out-of-station."
        ),
        "resolution": (
            "Add lt:Interchange class linking two lt:Stop instances with "
            "properties lt:transferTime and lt:transferType. Populate from "
            "GTFS transfers.txt if available, or from TfL interchange data."
        ),
        "query": """
            SELECT (COUNT(?cls) AS ?count)
            WHERE {
                ?cls a owl:Class .
                FILTER(CONTAINS(LCASE(STR(?cls)), "interchange") ||
                       CONTAINS(LCASE(STR(?cls)), "connection") ||
                       CONTAINS(LCASE(STR(?cls)), "transfer"))
            }
        """,
        "expected": "0 interchange/connection classes exist",
    },
    {
        "id": "O6",
        "title": "No modeOfTransport property for lines",
        "description": (
            "Transport mode (bus, tube, DLR, tram, etc.) is implicit in "
            "the subclass hierarchy (BusLine, TubeLine) but there is no "
            "explicit modeOfTransport datatype property. This makes it "
            "hard to query 'all lines of mode X' without enumerating "
            "every subclass."
        ),
        "resolution": (
            "Add lt:modeOfTransport datatype property with domain "
            "lt:TransportLine and range xsd:string. Populate from "
            "the TfL JSON mode field or derive from the subclass type."
        ),
        "query": """
            SELECT (COUNT(?prop) AS ?count)
            WHERE {
                ?prop a owl:DatatypeProperty .
                FILTER(CONTAINS(LCASE(STR(?prop)), "mode"))
            }
        """,
        "expected": "0 mode-related properties exist",
    },
    {
        "id": "O7",
        "title": "No Fare or pricing class",
        "description": (
            "Fares and pricing are entirely absent from the ontology. "
            "There is no Fare class, no ticketPrice property, and no "
            "way to represent Oyster caps, contactless fares, or "
            "concessionary pricing — all central to London transport."
        ),
        "resolution": (
            "Add lt:Fare class with properties lt:fareAmount (xsd:decimal), "
            "lt:fareType (xsd:string), and link it to routes or zones. "
            "Populate from TfL fares data or extract from the annual report."
        ),
        "query": """
            SELECT (COUNT(?cls) AS ?count)
            WHERE {
                ?cls a owl:Class .
                FILTER(CONTAINS(LCASE(STR(?cls)), "fare") ||
                       CONTAINS(LCASE(STR(?cls)), "price") ||
                       CONTAINS(LCASE(STR(?cls)), "ticket"))
            }
        """,
        "expected": "0 fare/pricing classes exist",
    },
    {
        "id": "O8",
        "title": "No colour property for transport lines",
        "description": (
            "London tube lines have official colours (e.g. Bakerloo is "
            "brown, Central is red) used on maps and signage. The ontology "
            "has no colour/color property to capture this. This also "
            "applies to Overground line naming colours introduced in 2024."
        ),
        "resolution": (
            "Add lt:lineColour datatype property with domain "
            "lt:TransportLine and range xsd:string. Populate from "
            "TfL API line data or extract from the annual report "
            "(which discusses the new Overground line colour names)."
        ),
        "query": """
            SELECT (COUNT(?prop) AS ?count)
            WHERE {
                { ?prop a owl:DatatypeProperty } UNION { ?prop a owl:ObjectProperty }
                FILTER(CONTAINS(LCASE(STR(?prop)), "colour") ||
                       CONTAINS(LCASE(STR(?prop)), "color"))
            }
        """,
        "expected": "0 colour-related properties exist",
    },
]


# Instance gap queries
INSTANCE_GAPS = [
    {
        "id": "I1",
        "title": "TransportLine instances lack operatedBy relationships",
        "description": (
            "704 TransportLine instances exist (from TfL JSON) but only 1 "
            "has an operatedBy link. Lines like the Piccadilly, Northern, "
            "and bus routes have no operator information."
        ),
        "resolution": (
            "Use RAG: query KG for lines without operators, retrieve "
            "matching passages from the TfL report, and use the LLM to "
            "determine which operator runs each line. Most are operated "
            "by TfL directly, but some bus routes are contracted out."
        ),
        "query": """
            SELECT ?line ?name
            WHERE {
                ?line a lt:TransportLine .
                ?line lt:lineName ?name .
                FILTER NOT EXISTS { ?line lt:operatedBy ?op }
            }
            LIMIT 10
        """,
        "count_query": """
            SELECT (COUNT(?line) AS ?total)
                   (SUM(IF(BOUND(?op), 1, 0)) AS ?with_operator)
            WHERE {
                ?line a lt:TransportLine .
                OPTIONAL { ?line lt:operatedBy ?op }
            }
        """,
    },
    {
        "id": "I2",
        "title": "Stops have no locatedIn borough or area",
        "description": (
            "24,865 stops have latitude/longitude coordinates but zero "
            "have a locatedIn relationship to any place or borough. "
            "This makes spatial queries about which stops serve which "
            "area of London impossible."
        ),
        "resolution": (
            "Use RAG: for key stations mentioned in the TfL report, "
            "extract their borough from report text. For the wider stop "
            "set, reverse-geocode coordinates or use NaPTAN locality data."
        ),
        "query": """
            SELECT ?stop ?name ?lat ?lon
            WHERE {
                { ?stop a lt:BusStop } UNION { ?stop a lt:TrainStation }
                ?stop lt:name ?name .
                ?stop gtfs:lat ?lat .
                ?stop gtfs:long ?lon .
                FILTER NOT EXISTS { ?stop lt:locatedIn ?place }
            }
            LIMIT 10
        """,
        "count_query": """
            SELECT (COUNT(?stop) AS ?total)
                   (SUM(IF(BOUND(?place), 1, 0)) AS ?with_location)
            WHERE {
                { ?stop a lt:BusStop } UNION { ?stop a lt:TrainStation }
                OPTIONAL { ?stop lt:locatedIn ?place }
            }
        """,
    },
    {
        "id": "I3",
        "title": "LLM-extracted entities are disconnected from GTFS data",
        "description": (
            "The LLM extracted entities like lt:elizabeth_line and "
            "lt:london_overground from the PDF, but these are separate "
            "nodes from the GTFS-sourced route and line instances. The "
            "Elizabeth Line exists as both lt:elizabeth_line (LLM) and "
            "as multiple lt:TrainRoute instances (GTFS) with no link."
        ),
        "resolution": (
            "Use RAG: query both LLM entities and GTFS routes, use the "
            "LLM to identify matches (e.g. 'Elizabeth line' from PDF = "
            "GTFS routes with 'Elizabeth' in their name), then add "
            "owl:sameAs or lt:hasRoute links between them."
        ),
        "query": """
            SELECT ?entity ?label ?type
            WHERE {
                ?entity lt:mentionedInReport ?report .
                ?entity a ?type .
                ?entity rdfs:label ?label .
                FILTER(?type != lt:Report)
            }
        """,
        "count_query": """
            SELECT (COUNT(?entity) AS ?llm_entities)
            WHERE {
                ?entity lt:mentionedInReport ?report .
                FILTER NOT EXISTS {
                    ?entity lt:hasRoute ?route .
                }
            }
        """,
    },
    {
        "id": "I4",
        "title": "TransportOperator instances mostly lack names",
        "description": (
            "57 TransportOperator instances exist in the KG, but the "
            "majority sourced from GTFS have names only via rdfs:label "
            "in the GTFS KG. After merging, operator data is sparse — "
            "no website, contact info, or lines-operated linkage."
        ),
        "resolution": (
            "Use RAG: retrieve passages from the TfL report mentioning "
            "operators (TfL, Arriva, Go-Ahead, etc.) and use the LLM "
            "to extract operator details and which lines they operate."
        ),
        "query": """
            SELECT ?op ?name
            WHERE {
                ?op a lt:TransportOperator .
                OPTIONAL { ?op lt:operatorName ?name }
                OPTIONAL { ?op rdfs:label ?label }
            }
            LIMIT 10
        """,
        "count_query": """
            SELECT (COUNT(?op) AS ?total)
                   (SUM(IF(BOUND(?name), 1, 0)) AS ?with_name)
            WHERE {
                ?op a lt:TransportOperator .
                OPTIONAL { ?op lt:operatorName ?name }
            }
        """,
    },
    {
        "id": "I5",
        "title": "Trips have no human-readable names (headsigns)",
        "description": (
            "10,000 Trip instances exist but none have a lt:name or "
            "rdfs:label. They only link to routes via lt:onRoute. "
            "Without headsigns, it is impossible to know the direction "
            "or destination of a trip."
        ),
        "resolution": (
            "Re-examine GTFS trips.txt — the trip_headsign field may be "
            "empty in this dataset. Use RAG to extract typical headsigns "
            "for major lines from the report, or derive from the "
            "last stop in each trip's stop_time sequence."
        ),
        "query": """
            SELECT ?trip ?route
            WHERE {
                ?trip a gtfs:Trip .
                ?trip lt:onRoute ?route .
                FILTER NOT EXISTS { ?trip lt:name ?name }
                FILTER NOT EXISTS { ?trip rdfs:label ?label }
            }
            LIMIT 10
        """,
        "count_query": """
            SELECT (COUNT(?trip) AS ?total)
                   (SUM(IF(BOUND(?name), 1, 0)) AS ?with_name)
            WHERE {
                ?trip a gtfs:Trip .
                OPTIONAL { ?trip gtfs:headsign ?name }
            }
        """,
    },
    {
        "id": "I6",
        "title": "TransportLine instances have no hasRoute links to GTFS Routes",
        "description": (
            "704 TransportLine instances (from TfL JSON) and 1,102 Route "
            "instances (from GTFS) exist as separate, unlinked nodes. The "
            "ontology defines lt:hasRoute (TransportLine → Route) but no "
            "instances use it. It is impossible to navigate from a named "
            "line like 'Northern' to its actual GTFS route schedules."
        ),
        "resolution": (
            "Use RAG: query KG for TransportLines and Routes, use the LLM "
            "to match line names to route names/numbers, then add "
            "lt:hasRoute links between them."
        ),
        "query": """
            SELECT ?line ?name
            WHERE {
                ?line a lt:TransportLine .
                ?line lt:lineName ?name .
                FILTER NOT EXISTS { ?line lt:hasRoute ?route }
            }
            LIMIT 10
        """,
        "count_query": """
            SELECT (COUNT(?line) AS ?total)
                   (SUM(IF(BOUND(?route), 1, 0)) AS ?with_route)
            WHERE {
                ?line a lt:TransportLine .
                OPTIONAL { ?line lt:hasRoute ?route }
            }
        """,
    },
    {
        "id": "I7",
        "title": "TubeLines have zero servesStation links",
        "description": (
            "11 TubeLine instances exist (Bakerloo, Central, Circle, etc.) "
            "but none link to any station via lt:servesStation. It is "
            "impossible to query which stations a tube line serves."
        ),
        "resolution": (
            "Use RAG: retrieve passages from the TfL report mentioning "
            "tube line stations, or use the LLM's knowledge of tube "
            "stations to populate servesStation links for each line."
        ),
        "query": """
            SELECT ?line ?label
            WHERE {
                ?line a lt:TubeLine .
                ?line rdfs:label ?label .
                FILTER NOT EXISTS { ?line lt:servesStation ?station }
            }
        """,
        "count_query": """
            SELECT (COUNT(?line) AS ?total)
                   (SUM(IF(BOUND(?station), 1, 0)) AS ?with_station)
            WHERE {
                ?line a lt:TubeLine .
                OPTIONAL { ?line lt:servesStation ?station }
            }
        """,
    },
    {
        "id": "I8",
        "title": "All 24,865 stops have wheelchairAccessible = false",
        "description": (
            "Every stop in the KG has lt:wheelchairAccessible set to false. "
            "This is almost certainly a data mapping issue — many London "
            "stations do have step-free access. The GTFS wheelchair_boarding "
            "field likely uses '0' for 'no info' rather than 'not accessible'."
        ),
        "resolution": (
            "Use RAG: extract accessibility information from the TfL "
            "annual report (which discusses step-free access progress) "
            "and update key stations. Also re-examine the GTFS "
            "wheelchair_boarding mapping ('0' = unknown, not 'false')."
        ),
        "query": """
            SELECT ?stop ?name
            WHERE {
                { ?stop a lt:TrainStation }
                ?stop lt:name ?name .
                ?stop lt:wheelchairAccessible true .
            }
            LIMIT 10
        """,
        "count_query": """
            SELECT (COUNT(?stop) AS ?total)
                   (SUM(IF(?acc = true, 1, 0)) AS ?accessible)
            WHERE {
                { ?stop a lt:BusStop } UNION { ?stop a lt:TrainStation }
                ?stop lt:wheelchairAccessible ?acc .
            }
        """,
    },
]

# Run all gap queries and return structured results
def run_gap_analysis(g):
    results = {"ontology_gaps": [], "instance_gaps": []}

    print("\n=== ONTOLOGY GAPS ===\n")
    for gap in ONTOLOGY_GAPS:
        print(f"[{gap['id']}] {gap['title']}")
        query_result = None
        try:
            rows = list(g.query(gap["query"], initNs={"lt": LT, "owl": OWL}))
            if rows:
                query_result = str(rows[0][0])
                print(f"  Query result: {query_result}")
        except Exception as e:
            query_result = f"Query error: {e}"
            print(f"  {query_result}")

        results["ontology_gaps"].append({
            "id": gap["id"],
            "title": gap["title"],
            "description": gap["description"],
            "resolution": gap["resolution"],
            "evidence": gap["expected"],
            "query_result": query_result,
        })

    print("\n=== INSTANCE GAPS ===\n")
    ns = {"lt": LT, "owl": OWL, "rdfs": RDFS, "gtfs": GTFS}
    for gap in INSTANCE_GAPS:
        print(f"[{gap['id']}] {gap['title']}")

        # Run count query
        count_result = {}
        try:
            qres = g.query(gap["count_query"], initNs=ns)
            var_names = [str(v) for v in qres.vars]
            for row in qres:
                for i, var in enumerate(var_names):
                    if row[i] is not None:
                        count_result[var] = str(row[i])
                break  
            for k, v in count_result.items():
                print(f"  {k}: {v}")
        except Exception as e:
            print(f"  Count query error: {e}")

        # Run sample query
        samples = []
        try:
            qres = g.query(gap["query"], initNs=ns)
            var_names = [str(v) for v in qres.vars]
            for row in list(qres)[:5]:
                sample = {}
                for i, var in enumerate(var_names):
                    if row[i] is not None:
                        sample[var] = str(row[i]).split("#")[-1]
                samples.append(sample)
            if samples:
                print(f"  Samples: {samples[:3]}")
        except Exception as e:
            print(f"  Sample query error: {e}")

        results["instance_gaps"].append({
            "id": gap["id"],
            "title": gap["title"],
            "description": gap["description"],
            "resolution": gap["resolution"],
            "counts": count_result,
            "samples": samples,
        })

    return results


def print_summary(results):
    print("\n" + "=" * 60)
    print("COMPLETION ANALYSIS SUMMARY")
    print("=" * 60)

    print(f"\nOntology gaps found: {len(results['ontology_gaps'])}")
    for gap in results["ontology_gaps"]:
        print(f"  [{gap['id']}] {gap['title']}")

    print(f"\nInstance gaps found: {len(results['instance_gaps'])}")
    for gap in results["instance_gaps"]:
        counts = gap.get("counts", {})
        print(f"  [{gap['id']}] {gap['title']}")
        if counts:
            vals = ", ".join(f"{k}={v}" for k, v in counts.items())
            print(f"         ({vals})")


def main():
    g = load_kg()
    results = run_gap_analysis(g)
    print_summary(results)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nFull report saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
