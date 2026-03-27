import json
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS
import networkx as nx
import matplotlib.pyplot as plt


nx_graph = nx.DiGraph()


# Helper function to strip long URIs into short, readable labels
def get_short_name(uri):
    # Splits the URL by '/' or '#' and grabs the very last piece
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.split("/")[-1]




file = "tfl.json"
with open(file, "r") as f:
    tfl_data = json.load(f)


g = Graph()
TFL = Namespace("http://example.org/tfl/ontology/")
TFL_RES = Namespace("http://example.org/tfl/resource/")


g.bind("tfl", TFL)
g.bind("tflres", TFL_RES)


# tbox 
for broad_category, sub_categories in tfl_data["Lines"].items():
    category_uri = TFL[broad_category]
    g.add((category_uri, RDF.type, RDFS.Class))

    for sub_cat in sub_categories:
        sub_cat_uri = TFL[sub_cat]
        g.add((sub_cat_uri, RDF.type, RDFS.Class))
        g.add((sub_cat_uri, RDFS.subClassOf, category_uri))


# a box
for instance in tfl_data["Instances"]:
    instance_uri = TFL_RES[f"line_{instance['id']}"]
    class_uri = TFL[instance["belongsToClass"]]

    g.add((instance_uri, RDF.type, class_uri))
    g.add((instance_uri, TFL.hasId, Literal(instance["id"])))
    g.add((instance_uri, TFL.hasName, Literal(instance["name"])))


output_file = "tfl_knowledge_graph.ttl"
g.serialize(destination=output_file, format="turtle")

print(f"Success! Knowledge graph saved to {output_file}")




# visualisation


for subject, predicate, object in g:
    s_label = get_short_name(subject)
    p_label = get_short_name(predicate)
    o_label = get_short_name(object)
    
    if "http" in str(object): 
        nx_graph.add_edge(s_label, o_label, label=p_label)

# 1. MAKE THE CANVAS BIGGER
plt.figure(figsize=(16, 12)) 

# 2. INCREASE 'k' AND 'iterations' TO SPACE NODES OUT
pos = nx.spring_layout(nx_graph, seed=42, k=2.5, iterations=100) 

node_colors = []
for node in nx_graph.nodes():
    if "line_" in node:  
        node_colors.append("lightseagreen")
    else:                
        node_colors.append("mediumpurple")

# 3. MAKE THE NODES SLIGHTLY SMALLER
nx.draw_networkx_nodes(nx_graph, pos, node_color=node_colors, node_size=1200, alpha=0.9)

# (Optional) Shrink the font size so it fits in the smaller nodes
nx.draw_networkx_labels(nx_graph, pos, font_size=8, font_weight="bold", font_color="white")

nx.draw_networkx_edges(nx_graph, pos, arrows=True, arrowsize=15, edge_color="gray", width=1.5)

edge_labels = nx.get_edge_attributes(nx_graph, 'label')
nx.draw_networkx_edge_labels(nx_graph, pos, edge_labels=edge_labels, font_size=7, font_color="red")

plt.title("TfL Knowledge Graph Structure", fontsize=18, fontweight="bold")
plt.axis("off") 
plt.tight_layout()

plt.savefig("tfl_graph_visualization.png", dpi=300)
plt.show()