"""
Map LLM-extracted entities and relations from llm_extractions.json
to RDF triples using the London Transport ontology (Ontology.py).

Input:  llm_extractions.json (repo root)
Output: data/processed/llm_extracted_graph.ttl

Mapping rules
─────────────
Entity types → RDF classes
  TransportOperator  → lt:TransportOperator
  TransportLine      → lt:TubeLine / lt:DLRLine / lt:OvergroundLine /
                       lt:ElizabethLine / lt:TramLine / lt:RiverBusLine /
                       lt:BusLine  (name-based; fallback lt:TransportLine)
  Route              → gtfs:Route  (lt:BusRoute / lt:TrainRoute when name implies it)
  Station            → lt:TrainStation
  Place              → schema:Place
  Person / Statistic / TradeUnion → skipped (no ontology mapping)

Predicates → RDF properties
  operatedBy    → lt:operatedBy
  hasRoute      → lt:hasRoute
  hasStop       → lt:hasStop
  connectsTo    → lt:connectsTo   (custom, declared in graph)
  extendsTo     → lt:extendsTo
  locatedIn     → lt:locatedIn
  servedBy      → lt:servedBy
  servesStation → lt:servesStation
  hasFrequency  → lt:hasFrequency
  hasRidership  → lt:hasRidership
  All others    → skipped (financial / ambiguous predicates)

URI generation
  Slugify entity name: lowercase, collapse whitespace → underscore,
  strip non-alphanumeric except underscore.
  URI = lt:<slug>
"""

import json
import re
import sys
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, XSD, URIRef

# ── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = REPO_ROOT / "llm_extractions.json"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "llm_extracted_graph.ttl"

# ── Namespaces ────────────────────────────────────────────────────────────────
LT = Namespace("http://example.org/london-transport#")
GTFS = Namespace("http://vocab.gtfs.org/terms#")
SCHEMA = Namespace("http://schema.org/")

# ── Entity type → RDF class (coarse mapping; TransportLine refined by name) ──
ENTITY_CLASS_MAP = {
    "TransportOperator": LT.TransportOperator,
    "Route":             GTFS.Route,
    "Station":           LT.TrainStation,
    "Place":             SCHEMA.Place,
}
SKIP_TYPES = {"Person", "Statistic", "TradeUnion"}

# Keywords for TransportLine subtype detection (checked in order)
TRANSPORT_LINE_KEYWORDS = [
    (["elizabeth"],                          LT.ElizabethLine),
    (["dlr", "docklands"],                   LT.DLRLine),
    (["overground"],                         LT.OvergroundLine),
    (["river bus", "river"],                 LT.RiverBusLine),
    (["tram"],                               LT.TramLine),
    (["bus route", "bus"],                   LT.BusLine),
    (["tube", "underground", "metro"],       LT.TubeLine),
]

# Known tube line names that map to TubeLine
TUBE_LINE_NAMES = {
    "bakerloo", "central", "circle", "district", "hammersmith", "jubilee",
    "metropolitan", "northern", "piccadilly", "victoria", "waterloo",
}

# ── Predicate → ontology property ────────────────────────────────────────────
PREDICATE_MAP = {
    "operatedBy":    LT.operatedBy,
    "hasRoute":      LT.hasRoute,
    "hasStop":       LT.hasStop,
    "connectsTo":    LT.connectsTo,
    "extendsTo":     LT.extendsTo,
    "locatedIn":     LT.locatedIn,
    "servedBy":      LT.servedBy,
    "servesStation": LT.servesStation,
    "hasFrequency":  LT.hasFrequency,
    "hasRidership":  LT.hasRidership,
}
# Predicates that carry no useful ontology meaning for this KG
SKIP_PREDICATES = {
    "grants", "loanedTo", "ring-fenced grant from",
    "non-ring-fenced grant from", "capital expenditure relating to",
    "published", "Route",
}


def slugify(name: str) -> str:
    """Convert an entity name to a safe URI local name."""
    slug = name.strip().lower()
    slug = re.sub(r"[\s/\\]+", "_", slug)
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"


def entity_uri(name: str) -> URIRef:
    return LT[slugify(name)]


def resolve_transport_line_class(name: str) -> URIRef:
    """Return the most specific lt: subclass for a TransportLine entity."""
    lower = name.lower()
    # Check tube line names list first
    for tl in TUBE_LINE_NAMES:
        if tl in lower:
            return LT.TubeLine
    for keywords, cls in TRANSPORT_LINE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return cls
    return LT.TransportLine


def resolve_class(entity_name: str, entity_type: str) -> URIRef | None:
    if entity_type in SKIP_TYPES:
        return None
    if entity_type == "TransportLine":
        return resolve_transport_line_class(entity_name)
    return ENTITY_CLASS_MAP.get(entity_type)


def declare_custom_properties(g: Graph) -> None:
    """Add OWL declarations for custom properties not in Ontology.py."""
    custom_obj_props = [
        LT.connectsTo, LT.extendsTo, LT.servedBy, LT.servesStation,
    ]
    custom_data_props = [
        LT.hasFrequency, LT.hasRidership, LT.locatedIn,
    ]
    for p in custom_obj_props:
        g.add((p, RDF.type, OWL.ObjectProperty))
    for p in custom_data_props:
        g.add((p, RDF.type, OWL.DatatypeProperty))


def build_graph(data: dict) -> Graph:
    g = Graph()
    g.bind("lt", LT)
    g.bind("gtfs", GTFS)
    g.bind("schema", SCHEMA)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    declare_custom_properties(g)

    # Track URIs already typed so we don't add duplicate type triples
    typed: dict[URIRef, URIRef] = {}

    pages = data.get("pages", [])
    entity_skipped = 0
    relation_skipped = 0
    relations_added = 0

    for page in pages:
        # ── Entities ──────────────────────────────────────────────────────────
        for entity in page.get("entities", []):
            name = entity.get("name") or ""
            if isinstance(name, str):
                name = name.strip()
            etype = entity.get("type") or ""
            if not name or not etype:
                continue

            rdf_class = resolve_class(name, etype)
            if rdf_class is None:
                entity_skipped += 1
                continue

            uri = entity_uri(name)
            if uri not in typed:
                g.add((uri, RDF.type, rdf_class))
                g.add((uri, RDFS.label, Literal(name)))
                typed[uri] = rdf_class

                # Add name property based on class hierarchy
                if rdf_class in (LT.TransportOperator,):
                    g.add((uri, LT.operatorName, Literal(name)))
                elif rdf_class in (
                    LT.TransportLine, LT.TubeLine, LT.DLRLine,
                    LT.OvergroundLine, LT.ElizabethLine, LT.BusLine,
                    LT.RiverBusLine, LT.TramLine,
                ):
                    g.add((uri, LT.lineName, Literal(name)))

            # Attach description if present and not already set
            desc = entity.get("description", "").strip()
            if desc:
                g.add((uri, SCHEMA.description, Literal(desc)))

        # ── Relations ─────────────────────────────────────────────────────────
        for rel in page.get("relations", []):
            subj_name = rel.get("subject", "")
            if isinstance(subj_name, str):
                subj_name = subj_name.strip()
            pred_raw = rel.get("predicate", "")
            if isinstance(pred_raw, str):
                pred_raw = pred_raw.strip()
            obj_raw = rel.get("object")

            if not subj_name or not pred_raw or obj_raw is None:
                relation_skipped += 1
                continue
            if pred_raw in SKIP_PREDICATES:
                relation_skipped += 1
                continue

            rdf_pred = PREDICATE_MAP.get(pred_raw)
            if rdf_pred is None:
                relation_skipped += 1
                continue

            # object may be a string or a list of strings
            obj_names = obj_raw if isinstance(obj_raw, list) else [obj_raw]
            subj_uri = entity_uri(subj_name)
            for obj_name in obj_names:
                if not isinstance(obj_name, str) or not obj_name.strip():
                    continue
                obj_uri = entity_uri(obj_name.strip())
                g.add((subj_uri, rdf_pred, obj_uri))
                relations_added += 1

    print(f"Entities typed:    {len(typed)}")
    print(f"Entities skipped:  {entity_skipped} (no ontology class)")
    print(f"Relations added:   {relations_added}")
    print(f"Relations skipped: {relation_skipped} (unmapped/financial predicates)")
    print(f"Total triples:     {len(g)}")
    return g


def main() -> None:
    if not JSON_PATH.exists():
        print(f"ERROR: JSON file not found at {JSON_PATH}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading {JSON_PATH} ...")
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    print(f"Pages: {len(data.get('pages', []))}")
    g = build_graph(data)

    print(f"\nSerialising to {OUTPUT_PATH} ...")
    g.serialize(destination=str(OUTPUT_PATH), format="turtle")
    print("Done.")


if __name__ == "__main__":
    main()
