import os
import sys
import json

from rdflib import Literal, RDF, RDFS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.kg.ontology import build_ontology, LT

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TFL_JSON_PATH = os.path.join(BASE_DIR, "data/raw/tfl.json")


MODE_CLASS_MAP = {
    "tube": LT.TubeLine,
    "dlr": LT.DLRLine,
    "overground": LT.OvergroundLine,
    "elizabeth-line": LT.ElizabethLine,
    "tram": LT.TramLine,
    "river-bus": LT.RiverBusLine,
    "national-rail": LT.NationalRailLine,
    "NormalBus": LT.BusLine,
    "SchoolService": LT.BusLine,
    "Airport": LT.BusLine,
    "Bexley": LT.BusLine,
    "Central": LT.BusLine,
    "Docklands": LT.BusLine,
    "Ealing": LT.BusLine,
    "EastLondon": LT.BusLine,
    "OtherBus": LT.BusLine,
    "HarrowHounslow": LT.BusLine,
    "Kingston": LT.BusLine,
    "NightBus": LT.BusLine,
    "Peckham": LT.BusLine,
    "RichmondOrpington": LT.BusLine,
    "Sutton": LT.BusLine,
    "CycleShuttle": LT.BusLine,
    "SuperLoop": LT.BusLine,
    "Uxbridge": LT.BusLine,
    "WoodGreenWaltham": LT.BusLine,
    "bus": LT.BusLine,
}


def load_tfl_json(path=TFL_JSON_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def line_uri(line_id: str):
    clean = str(line_id).replace(" ", "_").replace("/", "_")
    return LT[f"line_{clean}"]


def map_tfl_lines(g, data):
    instances = data.get("Instances", [])

    for inst in instances:
        line_id = inst.get("id", "").strip()
        line_name = inst.get("name", "").strip()
        belongs_to = inst.get("belongsToClass", "").strip()

        if not line_id:
            continue

        uri = line_uri(line_id)
        cls = MODE_CLASS_MAP.get(belongs_to, LT.TransportLine)

        g.add((uri, RDF.type, cls))

        if line_name:
            g.add((uri, LT.name, Literal(line_name)))
            g.add((uri, RDFS.label, Literal(line_name)))

    print(f"  Mapped {len(instances)} transport lines")
    return g


def build_tfl_kg():
    print("Building TfL lines knowledge graph...")

    if not os.path.exists(TFL_JSON_PATH):
        print(f"tfl.json not found at {TFL_JSON_PATH}")
        print("Run 'python -m src.ingestion.tfl_api' first.")
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