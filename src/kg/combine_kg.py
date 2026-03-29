from rdflib import Graph

def merge_transport_graphs(file1, file2, output_file):
    merged_kg = Graph()

    print(f"Parsing {file1}")
    merged_kg.parse(file1, format="turtle")

    print(f"Parsing {file2}...")
    merged_kg.parse(file2, format="turtle")

    print(f"Saving merged graph to {output_file}")
    merged_kg.serialize(destination=output_file, format="turtle")
    
    print("Merge complete!")

merge_transport_graphs("data/kg/gtfs_kg.ttl", "data/kg/tfl_lines_kg.ttl", "data/kg/public_transport.ttl")