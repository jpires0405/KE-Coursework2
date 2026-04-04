import json
import re
import sys
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD, URIRef

REPO_ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = REPO_ROOT / "data" / "processed" / "llm_extractions.json"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "llm_extracted_graph.ttl"

LT = Namespace("http://example.org/london-transport#")

ENTITY_CLASS_MAP = {
    "TransportOperator": LT.TransportOperator,
    "Route": LT.Route,
    "Station": LT.TrainStation,
    "Place": LT.Place,
    "Statistic": LT.Statistic,
}

SKIP_TYPES = {"Person", "TradeUnion"}

TRANSPORT_LINE_KEYWORDS = [
    (["elizabeth"], LT.ElizabethLine),
    (["dlr", "docklands"], LT.DLRLine),
    (["overground"], LT.OvergroundLine),
    (["river bus", "river"], LT.RiverBusLine),
    (["tram"], LT.TramLine),
    (["bus route", "bus"], LT.BusLine),
    (["tube", "underground", "metro"], LT.TubeLine),
    (["national rail"], LT.NationalRailLine),
]

TUBE_LINE_NAMES = {
    "bakerloo", "central", "circle", "district", "hammersmith", "jubilee",
    "metropolitan", "northern", "piccadilly", "victoria", "waterloo",
}

PREDICATE_MAP = {
    "operatedBy": LT.operatedBy,
    "hasRoute": LT.hasRoute,
    "hasStop": LT.hasStop,
    "connectsTo": LT.connectsTo,
    "extendsTo": LT.extendsTo,
    "locatedIn": LT.locatedIn,
    "servedBy": LT.servedBy,
    "servesStation": LT.servesStation,
    "hasFrequency": LT.hasFrequency,
    "hasRidership": LT.hasRidership,
}

SKIP_PREDICATES = {
    "grants", "loanedTo", "ring-fenced grant from",
    "non-ring-fenced grant from", "capital expenditure relating to",
    "published", "Route",
}


def slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[\s/\\]+", "_", slug)
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"


def entity_uri(name: str) -> URIRef:
    return LT[slugify(name)]


def resolve_transport_line_class(name: str):
    lower = name.lower()
    for tl in TUBE_LINE_NAMES:
        if tl in lower:
            return LT.TubeLine
    for keywords, cls in TRANSPORT_LINE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return cls
    return LT.TransportLine


def resolve_class(entity_name: str, entity_type: str):
    if entity_type in SKIP_TYPES:
        return None
    if entity_type == "TransportLine":
        return resolve_transport_line_class(entity_name)
    return ENTITY_CLASS_MAP.get(entity_type)


def build_graph(data: dict) -> Graph:
    g = Graph()
    g.bind("lt", LT)

    typed = {}

    pages = data.get("pages", [])
    entity_skipped = 0
    relation_skipped = 0
    relations_added = 0

    report_uri = LT["tfl_annual_report_2024_25"]
    g.add((report_uri, RDF.type, LT.Report))
    g.add((report_uri, LT.name, Literal("TfL Annual Report and Statement of Accounts 2024/25")))
    g.add((report_uri, RDFS.label, Literal("TfL Annual Report and Statement of Accounts 2024/25")))

    for page in pages:
        for entity in page.get("entities", []):
            name = (entity.get("name") or "").strip()
            etype = (entity.get("type") or "").strip()
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
                g.add((uri, LT.name, Literal(name)))
                typed[uri] = rdf_class

            desc = (entity.get("description") or "").strip()
            if desc:
                g.add((uri, LT.description, Literal(desc)))

            g.add((uri, LT.mentionedInReport, report_uri))

        for rel in page.get("relations", []):
            subj_name = (rel.get("subject") or "").strip()
            pred_raw = (rel.get("predicate") or "").strip()
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

            obj_names = obj_raw if isinstance(obj_raw, list) else [obj_raw]
            subj_uri = entity_uri(subj_name)

            for obj_name in obj_names:
                if not isinstance(obj_name, str) or not obj_name.strip():
                    continue

                obj_name = obj_name.strip()
                if rdf_pred in {LT.hasFrequency, LT.hasRidership, LT.locatedIn}:
                    g.add((subj_uri, rdf_pred, Literal(obj_name)))
                else:
                    obj_uri = entity_uri(obj_name)
                    g.add((subj_uri, rdf_pred, obj_uri))
                relations_added += 1

    print(f"Entities typed:    {len(typed)}")
    print(f"Entities skipped:  {entity_skipped}")
    print(f"Relations added:   {relations_added}")
    print(f"Relations skipped: {relation_skipped}")
    print(f"Total triples:     {len(g)}")
    return g


def main():
    if not JSON_PATH.exists():
        print(f"ERROR: JSON file not found at {JSON_PATH}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading {JSON_PATH} ...")
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    g = build_graph(data)

    print(f"\nSerialising to {OUTPUT_PATH} ...")
    g.serialize(destination=str(OUTPUT_PATH), format="turtle")
    print("Done.")


if __name__ == "__main__":
    main()