from pathlib import Path
from rdflib import Graph

BASE_DIR = Path(__file__).resolve().parents[2]

def merge_graphs(files, output_file):
    merged = Graph()

    for file in files:
        file_path = BASE_DIR / file
        print(f"Parsing {file_path}")

        with open(file_path, "rb") as f:
            merged.parse(file=f, format="turtle")

    output_path = BASE_DIR / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Saving merged graph to {output_path}")
    merged.serialize(destination=str(output_path), format="turtle")
    print("Merge complete!")


if __name__ == "__main__":
    files = [
        "data/kg/gtfs_kg.ttl",
        "data/kg/tfl_lines_kg.ttl",
        "data/processed/llm_extracted_graph.ttl",
    ]
    merge_graphs(files, "data/kg/public_transport.ttl")