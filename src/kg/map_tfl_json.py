"""
Map TfL API JSON data to RDF triples.
Converts transport lines (Tube, DLR, Overground, buses, etc.) into the KG.
"""

import os
import sys
import json

from rdflib import Graph, Literal, URIRef, RDF, RDFS, XSD, OWL

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.kg.ontology import build_ontology, LT, GTFS, SCHEMA

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TFL_JSON_PATH = os.path.join(BASE_DIR, "data/raw/tfl.json")

# Maps TfL mode names to the ontology classes
MODE_CLASS_MAP = {
    "tube": LT.TubeLine,
    "dlr": LT.DLRLine,
    "overground": LT.OvergroundLine,
    "elizabeth-line": LT.ElizabethLine,
    "tram": LT.TramLine,
    "bus": LT.BusLine,
    "river-bus": LT.RiverBusLine,
    "national-rail": LT.TransportLine,
}


def load_tfl_json(path=TFL_JSON_PATH):
    with open(path, "r") as f:
        return json.load(f)


def map_tfl_lines(g, data):
    """
    Each line instance from the TfL JSON becomes a TransportLine subclass.
    e.g. "victoria" → lt:line_victoria a lt:TubeLine ; lt:lineName "Victoria"
    """
    instances = data.get("Instances", [])

    for inst in instances:
        line_id = inst["id"]
        line_name = inst["name"]
        belongs_to = inst["belongsToClass"]

        line_uri = LT[f"line_{line_id.replace(' ', '_')}"]

        # Pick the right class based on what category the line belongs to
        line_class = MODE_CLASS_MAP.get(belongs_to, LT.TransportLine)
        g.add((line_uri, RDF.type, line_class))
        g.add((line_uri, LT.lineName, Literal(line_name)))
        g.add((line_uri, RDFS.label, Literal(line_name)))

    print(f"  Mapped {len(instances)} transport lines")
    return g


def map_line_categories(g, data):
    """
    Maps the category structure (TrainLines, BusLines, etc.)
    so we can see which subcategories exist.
    """
    lines = data.get("Lines", {})
    for category, subcategories in lines.items():
        cat_uri = LT[category]
        g.add((cat_uri, RDF.type, OWL.Class))
        for sub in subcategories:
            sub_uri = LT[sub.replace("-", "_")]
            g.add((sub_uri, RDFS.subClassOf, cat_uri))

    return g


def build_tfl_kg():
    """Run the full TfL JSON → RDF mapping pipeline."""
    print("Building TfL lines knowledge graph...")

    if not os.path.exists(TFL_JSON_PATH):
        print(f"tfl.json not found at {TFL_JSON_PATH}")
        print("Run 'python src/ingestion/tfl_api.py' first.")
        return None

    g = build_ontology()
    data = load_tfl_json()
    g = map_tfl_lines(g, data)

    print(f"Total triples: {len(g)}")
    return g


if __name__ == "__main__":
    g = build_tfl_kg()
    if g:
        output = os.path.join(BASE_DIR, "data/kg/tfl_lines_kg.ttl")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        g.serialize(destination=output, format="turtle")
        print(f"Saved to {output}")
