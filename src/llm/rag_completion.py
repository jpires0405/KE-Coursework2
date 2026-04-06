"""
RAG-based KG completion — retrieves context from the TfL report to fill
gaps identified by the completion analysis.
"""

import json
import os
import re
import sys
from pathlib import Path
import requests
from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, XSD, URIRef

BASE_DIR = Path(__file__).resolve().parents[2]
KG_PATH = BASE_DIR / "data" / "kg" / "public_transport.ttl"
PDF_TEXT_PATH = BASE_DIR / "data" / "processed" / "tfl_report_text.txt"
OUTPUT_KG_PATH = BASE_DIR / "data" / "kg" / "completed_kg.ttl"
OUTPUT_LOG_PATH = BASE_DIR / "data" / "kg" / "rag_completion_log.json"

LT = Namespace("http://example.org/london-transport#")
GTFS = Namespace("http://vocab.gtfs.org/terms#")

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3"


# Helpers
def slugify(name: str) -> str:
    slug = name.strip().lower()
    slug = re.sub(r"[\s/\\]+", "_", slug)
    slug = re.sub(r"[^a-z0-9_]", "", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"


def entity_uri(name: str) -> URIRef:
    return LT[slugify(name)]


def load_kg():
    if not KG_PATH.exists():
        print(f"ERROR: KG not found at {KG_PATH}", file=sys.stderr)
        sys.exit(1)
    g = Graph()
    g.bind("lt", LT)
    g.parse(str(KG_PATH), format="turtle")
    print(f"Loaded {len(g)} triples from {KG_PATH.name}")
    return g


def load_pages():
    """Load extracted PDF text split by page."""
    with open(PDF_TEXT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    pages = []
    chunks = re.split(r"--- Page (\d+) ---\n", content)
    for i in range(1, len(chunks), 2):
        page_num = int(chunks[i])
        text = chunks[i + 1].strip()
        if text:
            pages.append({"page": page_num, "text": text})
    return pages


def retrieve_passages(pages, keywords, max_passages=5):
    """Simple keyword-based retrieval: return pages mentioning any keyword."""
    scored = []
    kw_lower = [kw.lower() for kw in keywords]
    for page in pages:
        text_lower = page["text"].lower()
        hits = sum(1 for kw in kw_lower if kw in text_lower)
        if hits > 0:
            scored.append((hits, page))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:max_passages]]


def query_ollama(prompt, model=DEFAULT_MODEL):
    """Send prompt to Ollama, return raw text response."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2048},
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()["response"]


def parse_json_response(raw):
    """Extract JSON object or array from LLM text."""
    # Try array first, then object
    for pattern in [r"\[[\s\S]*\]", r"\{[\s\S]*\}"]:
        m = re.search(pattern, raw)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                continue
    return None


# RAG completion tasks
def complete_line_operators(g, pages, model, log):
    """I1: Fill missing operatedBy for TransportLine instances."""
    print("\n--- [I1] Completing TransportLine operatedBy ---")

    qres = g.query("""
        SELECT ?line ?name WHERE {
            ?line a lt:TransportLine .
            ?line lt:lineName ?name .
            FILTER NOT EXISTS { ?line lt:operatedBy ?op }
        } LIMIT 50
    """, initNs={"lt": LT})
    lines = [(str(row[0]), str(row[1])) for row in qres]

    if not lines:
        print("  No lines missing operatedBy — skipping")
        return

    line_names = [name for _, name in lines[:50]]
    passages = retrieve_passages(pages, line_names + ["operator", "operated", "contracted"])

    context_text = "\n\n".join(
        f"[Page {p['page']}]\n{p['text'][:1500]}" for p in passages[:3]
    )

    prompt = f"""You are completing a London transport knowledge graph.

The following transport lines are missing their operator (the organisation that runs them):
{json.dumps(line_names[:30], indent=2)}

Here are excerpts from the TfL Annual Report mentioning transport operations:

{context_text}

Based on the report and your knowledge of London transport:
- Most Tube lines, DLR, London Overground, Elizabeth line, and Tram are operated by TfL
- Bus routes are operated by TfL (contracted to private operators but TfL is the authority)

Return a JSON array of objects with "line_name" and "operator" fields.
Only return the JSON array, no other text.

Example:
[{{"line_name": "Piccadilly", "operator": "TfL"}}]
"""

    print(f"  Querying LLM for {len(line_names)} lines...")
    raw = query_ollama(prompt, model)
    results = parse_json_response(raw)

    triples_added = 0
    if results and isinstance(results, list):
        for item in results:
            line_name = item.get("line_name", "")
            operator = item.get("operator", "")
            if not line_name or not operator:
                continue
            # Find matching line URIs
            for line_uri, name in lines:
                if name.lower() == line_name.lower() or line_name.lower() in name.lower():
                    op_uri = entity_uri(operator)
                    g.add((URIRef(line_uri), LT.operatedBy, op_uri))
                    # Ensure operator exists
                    if (op_uri, RDF.type, None) not in g:
                        g.add((op_uri, RDF.type, LT.TransportOperator))
                        g.add((op_uri, RDFS.label, Literal(operator)))
                        g.add((op_uri, LT.name, Literal(operator)))
                    triples_added += 1

    print(f"  Added {triples_added} operatedBy triples")
    log.append({
        "gap": "I1", "task": "TransportLine operatedBy",
        "triples_added": triples_added,
        "lines_queried": len(line_names),
        "passages_retrieved": len(passages),
    })


def complete_stop_locations(g, pages, model, log):
    """I2: Fill locatedIn for key stations using RAG."""
    print("\n--- [I2] Completing Stop locatedIn ---")

    # Get train stations  
    qres = g.query("""
        SELECT ?stop ?name WHERE {
            ?stop a lt:TrainStation .
            ?stop lt:name ?name
            FILTER NOT EXISTS { ?stop lt:locatedIn ?place }
        } LIMIT 50
    """, initNs={"lt": LT, "gtfs": GTFS})
    stations = [(str(row[0]), str(row[1])) for row in qres]

    if not stations:
        print("  No stations missing locatedIn — skipping")
        return

    station_names = [name for _, name in stations[:50]]
    passages = retrieve_passages(
        pages,
        station_names[:20] + ["station", "borough", "located", "area"],
    )

    context_text = "\n\n".join(
        f"[Page {p['page']}]\n{p['text'][:1500]}" for p in passages[:3]
    )

    prompt = f"""You are completing a London transport knowledge graph.

The following train stations are missing their location (borough or area):
{json.dumps(station_names[:30], indent=2)}

Here are excerpts from the TfL Annual Report:

{context_text}

Based on the report and your knowledge of London, determine which borough or area each station is in.

Return a JSON array with "station_name" and "borough" fields.
Only return the JSON array, no other text.

Example:
[{{"station_name": "King's Cross St. Pancras", "borough": "Camden"}}]
"""

    print(f"  Querying LLM for {len(station_names)} stations...")
    raw = query_ollama(prompt, model)
    results = parse_json_response(raw)

    triples_added = 0
    if results and isinstance(results, list):
        for item in results:
            stn_name = item.get("station_name", "")
            borough = item.get("borough", "")
            if not stn_name or not borough:
                continue
            for stn_uri, name in stations:
                if name.lower() == stn_name.lower() or stn_name.lower() in name.lower():
                    borough_uri = entity_uri(borough)
                    g.add((URIRef(stn_uri), LT.locatedIn, borough_uri))
                    if (borough_uri, RDF.type, None) not in g:
                        g.add((borough_uri, RDF.type, LT.Place))
                        g.add((borough_uri, RDFS.label, Literal(borough)))
                        g.add((borough_uri, LT.name, Literal(borough)))
                    triples_added += 1

    print(f"  Added {triples_added} locatedIn triples")
    log.append({
        "gap": "I2", "task": "Stop locatedIn",
        "triples_added": triples_added,
        "stations_queried": len(station_names),
        "passages_retrieved": len(passages),
    })


def complete_entity_links(g, pages, model, log):
    """I3: Link LLM-extracted entities to GTFS route instances."""
    print("\n--- [I3] Linking LLM entities to GTFS routes ---")

    # Get LLM-extracted entities
    qres = g.query("""
        SELECT ?entity ?label ?type WHERE {
            ?entity lt:mentionedInReport ?report .
            ?entity a ?type .
            ?entity rdfs:label ?label .
            FILTER(?type != lt:Report)
            FILTER NOT EXISTS { ?entity lt:hasRoute ?route }
        }
    """, initNs={"lt": LT, "rdfs": RDFS})
    llm_entities = [(str(r[0]), str(r[1]), str(r[2]).split("#")[-1]) for r in qres]

    # Get GTFS route names
    qres2 = g.query("""
        SELECT ?route ?name WHERE {
            { ?route a lt:TrainRoute } UNION { ?route a lt:BusRoute }
            ?route lt:name ?name
        } LIMIT 200
    """, initNs={"lt": LT, "gtfs": GTFS})
    routes = [(str(r[0]), str(r[1])) for r in qres2]

    if not llm_entities or not routes:
        print("  No entities or routes to link — skipping")
        return

    entity_names = [name for _, name, _ in llm_entities]
    route_names = [name for _, name in routes[:50]]

    prompt = f"""You are linking entities in a London transport knowledge graph.

These entities were extracted from the TfL Annual Report (PDF):
{json.dumps([{"name": n, "type": t} for _, n, t in llm_entities], indent=2)}

These are GTFS route names already in the knowledge graph:
{json.dumps(route_names[:50], indent=2)}

Which report entities correspond to which GTFS routes? An entity like "Elizabeth Line"
might match routes containing "Elizabeth" in their name.

Return a JSON array with "entity_name" and "matching_routes" (list of route names).
Only return the JSON array, no other text.

Example:
[{{"entity_name": "Elizabeth Line", "matching_routes": ["Elizabeth line"]}}]
"""

    print(f"  Querying LLM to match {len(llm_entities)} entities to {len(routes)} routes...")
    raw = query_ollama(prompt, model)
    results = parse_json_response(raw)

    triples_added = 0
    if results and isinstance(results, list):
        for item in results:
            ent_name = item.get("entity_name", "")
            matching = item.get("matching_routes", [])
            if not ent_name or not matching:
                continue
            # Find entity URI
            ent_uri = None
            for uri, name, _ in llm_entities:
                if name.lower() == ent_name.lower():
                    ent_uri = URIRef(uri)
                    break
            if not ent_uri:
                continue
            # Find matching route URIs
            for route_name in matching:
                for route_uri, rname in routes:
                    if rname.lower() == route_name.lower() or route_name.lower() in rname.lower():
                        g.add((ent_uri, LT.hasRoute, URIRef(route_uri)))
                        triples_added += 1

    print(f"  Added {triples_added} hasRoute link triples")
    log.append({
        "gap": "I3", "task": "Entity-route linking",
        "triples_added": triples_added,
        "entities": len(llm_entities),
        "routes_available": len(routes),
    })


def complete_operator_names(g, pages, model, log):
    """I4: Fill missing names for TransportOperator instances."""
    print("\n--- [I4] Completing TransportOperator names ---")

    qres = g.query("""
        SELECT ?op ?label WHERE {
            ?op a lt:TransportOperator .
            OPTIONAL { ?op rdfs:label ?label }
            FILTER NOT EXISTS { ?op lt:operatorName ?name }
        } LIMIT 30
    """, initNs={"lt": LT, "rdfs": RDFS})
    operators = [(str(r[0]), str(r[1]) if r[1] else None) for r in qres]

    if not operators:
        print("  No operators missing names — skipping")
        return

    # Some may have rdfs:label from GTFS — use that
    triples_added = 0
    for op_uri, label in operators:
        if label:
            g.add((URIRef(op_uri), LT.operatorName, Literal(label)))
            triples_added += 1

    # For those still without, try RAG
    still_missing = [(uri, lbl) for uri, lbl in operators if not lbl]
    if still_missing:
        op_ids = [uri.split("#")[-1] for uri, _ in still_missing[:20]]
        passages = retrieve_passages(pages, ["operator", "contracted", "bus operator", "Arriva", "Go-Ahead"])

        context_text = "\n\n".join(
            f"[Page {p['page']}]\n{p['text'][:1500]}" for p in passages[:3]
        )

        prompt = f"""You are completing a London transport knowledge graph.

These transport operator IDs have no human-readable name:
{json.dumps(op_ids[:20], indent=2)}

Here are excerpts from the TfL Annual Report about operators:

{context_text}

The IDs follow the pattern "agency_OPXXXXX". Can you identify the operator names
for any of these based on the report text or your knowledge of London bus operators?

Return a JSON array with "operator_id" and "name" fields.
Only return the JSON array, no other text.
"""

        print(f"  Querying LLM for {len(op_ids)} operator names...")
        raw = query_ollama(prompt, model)
        results = parse_json_response(raw)

        if results and isinstance(results, list):
            for item in results:
                op_id = item.get("operator_id", "")
                name = item.get("name", "")
                if not op_id or not name:
                    continue
                for uri, _ in still_missing:
                    if op_id in uri:
                        g.add((URIRef(uri), LT.operatorName, Literal(name)))
                        g.add((URIRef(uri), RDFS.label, Literal(name)))
                        triples_added += 1

    print(f"  Added {triples_added} operator name triples")
    log.append({
        "gap": "I4", "task": "TransportOperator names",
        "triples_added": triples_added,
        "operators_queried": len(operators),
    })


def complete_trip_headsigns(g, pages, model, log):
    """I5: Derive headsigns for trips from their route + last stop."""
    print("\n--- [I5] Completing Trip headsigns ---")

    # Get trips with their route names and a stop name from their stop times
    qres = g.query("""
        SELECT ?trip ?routeName ?stopName WHERE {
            ?trip a gtfs:Trip .
            ?trip lt:onRoute ?route .
            ?route lt:name ?routeName
            OPTIONAL {
                ?st lt:onTrip ?trip .
                ?st lt:stopsAt ?stop .
                ?stop lt:name ?stopName
            }
            FILTER NOT EXISTS { ?trip lt:name ?name }
            FILTER NOT EXISTS { ?trip rdfs:label ?lbl }
        } LIMIT 30
    """, initNs={"lt": LT, "gtfs": GTFS, "rdfs": RDFS})

    trips = []
    for row in qres:
        trips.append({
            "uri": str(row[0]),
            "route": str(row[1]),
            "stop": str(row[2]) if row[2] else None,
        })

    if not trips:
        print("  No trips to complete — skipping")
        return

    # Group by route for efficiency
    route_trips = {}
    for t in trips:
        route_trips.setdefault(t["route"], []).append(t)

    route_names = list(route_trips.keys())[:20]
    passages = retrieve_passages(pages, route_names + ["route", "service", "destination"])

    context_text = "\n\n".join(
        f"[Page {p['page']}]\n{p['text'][:1000]}" for p in passages[:2]
    )

    sample_trips = []
    for t in trips[:20]:
        sample_trips.append({
            "route": t["route"],
            "last_stop": t["stop"],
        })

    prompt = f"""You are completing a London transport knowledge graph.

These trips have no headsign (destination display name). Each trip has a route name
and optionally a last stop:

{json.dumps(sample_trips, indent=2)}

Here is some context from the TfL Annual Report:

{context_text}

For each trip, generate a reasonable headsign based on the route name and last stop.
The headsign is typically the destination station/stop name.

Return a JSON array with "route", "last_stop", and "headsign" fields.
Only return the JSON array, no other text.
"""

    print(f"  Querying LLM for {len(sample_trips)} trip headsigns...")
    raw = query_ollama(prompt, model)
    results = parse_json_response(raw)

    triples_added = 0
    if results and isinstance(results, list):
        for item in results:
            route = item.get("route", "")
            headsign = item.get("headsign", "")
            last_stop = item.get("last_stop")
            if not route or not headsign:
                continue
            for t in trips:
                if t["route"] == route and t.get("stop") == last_stop:
                    g.add((URIRef(t["uri"]), LT.name, Literal(headsign)))
                    g.add((URIRef(t["uri"]), RDFS.label, Literal(headsign)))
                    triples_added += 1
                    break

    print(f"  Added {triples_added} trip headsign triples")
    log.append({
        "gap": "I5", "task": "Trip headsigns",
        "triples_added": triples_added,
        "trips_queried": len(sample_trips),
        "passages_retrieved": len(passages),
    })


def complete_line_routes(g, pages, model, log):
    """I6: Link TransportLine instances to GTFS Route instances via hasRoute."""
    print("\n--- [I6] Linking TransportLines to GTFS Routes ---")

    # Get TransportLine names
    qres = g.query("""
        SELECT ?line ?name WHERE {
            ?line a lt:TransportLine .
            ?line lt:lineName ?name .
            FILTER NOT EXISTS { ?line lt:hasRoute ?route }
        } LIMIT 50
    """, initNs={"lt": LT})
    lines = [(str(r[0]), str(r[1])) for r in qres]

    # Get Route names
    qres2 = g.query("""
        SELECT ?route ?name WHERE {
            { ?route a lt:TrainRoute } UNION { ?route a lt:BusRoute }
            ?route lt:name ?name .
        } LIMIT 200
    """, initNs={"lt": LT})
    routes = [(str(r[0]), str(r[1])) for r in qres2]

    if not lines or not routes:
        print("  No lines or routes to link — skipping")
        return

    line_names = [name for _, name in lines[:30]]
    route_names = [name for _, name in routes[:100]]

    prompt = f"""You are linking entities in a London transport knowledge graph.

These are TransportLine instances (from TfL API) with no route links:
{json.dumps(line_names[:30], indent=2)}

These are GTFS Route names already in the knowledge graph:
{json.dumps(route_names[:100], indent=2)}

Match each TransportLine to the GTFS routes that belong to it.
For example, line "Northern" should match routes containing "Northern" in their name.
Bus lines with number names (e.g. "24") should match routes with the same number.

Return a JSON array with "line_name" and "matching_routes" (list of route names).
Only return the JSON array, no other text.
"""

    print(f"  Querying LLM to match {len(line_names)} lines to {len(route_names)} routes...")
    raw = query_ollama(prompt, model)
    results = parse_json_response(raw)

    triples_added = 0
    if results and isinstance(results, list):
        for item in results:
            lname = item.get("line_name", "")
            matching = item.get("matching_routes", [])
            if not lname or not matching:
                continue
            line_uri = None
            for uri, name in lines:
                if name.lower() == lname.lower() or lname.lower() in name.lower():
                    line_uri = URIRef(uri)
                    break
            if not line_uri:
                continue
            for route_name in matching:
                if not isinstance(route_name, str):
                    continue
                for route_uri, rname in routes:
                    if rname.lower() == route_name.lower() or route_name.lower() in rname.lower():
                        g.add((line_uri, LT.hasRoute, URIRef(route_uri)))
                        triples_added += 1
                        break

    print(f"  Added {triples_added} hasRoute link triples")
    log.append({
        "gap": "I6", "task": "TransportLine-Route linking",
        "triples_added": triples_added,
        "lines_queried": len(line_names),
        "routes_available": len(route_names),
    })


def complete_tube_stations(g, pages, model, log):
    """I7: Fill servesStation for TubeLine instances using RAG."""
    print("\n--- [I7] Completing TubeLine servesStation ---")

    qres = g.query("""
        SELECT ?line ?label WHERE {
            ?line a lt:TubeLine .
            ?line rdfs:label ?label .
            FILTER NOT EXISTS { ?line lt:servesStation ?station }
        }
    """, initNs={"lt": LT, "rdfs": RDFS})
    tube_lines = [(str(r[0]), str(r[1])) for r in qres]

    if not tube_lines:
        print("  No tube lines missing servesStation — skipping")
        return

    line_names = [name for _, name in tube_lines]
    passages = retrieve_passages(
        pages,
        line_names + ["station", "tube", "underground", "step-free"],
    )

    context_text = "\n\n".join(
        f"[Page {p['page']}]\n{p['text'][:1500]}" for p in passages[:3]
    )

    # Also get existing TrainStation names to match against
    qres2 = g.query("""
        SELECT ?station ?name WHERE {
            ?station a lt:TrainStation .
            ?station lt:name ?name
        } LIMIT 200
    """, initNs={"lt": LT, "gtfs": GTFS})
    stations = [(str(r[0]), str(r[1])) for r in qres2]
    station_names = [name for _, name in stations[:100]]

    prompt = f"""You are completing a London transport knowledge graph.

These London Underground (Tube) lines have no stations linked:
{json.dumps(line_names, indent=2)}

Here are some station names already in the knowledge graph:
{json.dumps(station_names[:80], indent=2)}

Here are excerpts from the TfL Annual Report:

{context_text}

For each tube line, list 5-10 key stations it serves. Prefer station names that
match the list above. Include major interchange stations.

Return a JSON array with "line_name" and "stations" (list of station names).
Only return the JSON array, no other text.

Example:
[{{"line_name": "Bakerloo", "stations": ["Oxford Circus", "Paddington", "Waterloo"]}}]
"""

    print(f"  Querying LLM for stations on {len(tube_lines)} tube lines...")
    raw = query_ollama(prompt, model)
    results = parse_json_response(raw)

    triples_added = 0
    if results and isinstance(results, list):
        # Build a lookup for station names → URIs
        station_lookup = {}
        for stn_uri, stn_name in stations:
            station_lookup[stn_name.lower()] = stn_uri

        for item in results:
            lname = item.get("line_name", "")
            stn_names = item.get("stations", [])
            if not lname or not stn_names:
                continue
            # Find line URI
            line_uri = None
            for uri, name in tube_lines:
                if name.lower() == lname.lower() or lname.lower() in name.lower():
                    line_uri = URIRef(uri)
                    break
            if not line_uri:
                continue
            for stn_name in stn_names:
                if not isinstance(stn_name, str):
                    continue
                # Try exact match then fuzzy
                stn_uri = station_lookup.get(stn_name.lower())
                if not stn_uri:
                    for existing_name, existing_uri in station_lookup.items():
                        if stn_name.lower() in existing_name or existing_name in stn_name.lower():
                            stn_uri = existing_uri
                            break
                if stn_uri:
                    g.add((line_uri, LT.servesStation, URIRef(stn_uri)))
                    triples_added += 1

    print(f"  Added {triples_added} servesStation triples")
    log.append({
        "gap": "I7", "task": "TubeLine servesStation",
        "triples_added": triples_added,
        "lines_queried": len(tube_lines),
        "passages_retrieved": len(passages),
    })


def complete_accessibility(g, pages, model, log):
    """I8: Update wheelchairAccessible for key stations using RAG."""
    print("\n--- [I8] Completing station accessibility ---")

    passages = retrieve_passages(
        pages,
        ["step-free", "step free", "accessible", "wheelchair", "accessibility",
         "lift", "ramp", "disabled"],
    )

    if not passages:
        print("  No accessibility passages found — skipping")
        return

    context_text = "\n\n".join(
        f"[Page {p['page']}]\n{p['text'][:2000]}" for p in passages[:5]
    )

    prompt = f"""You are completing a London transport knowledge graph.

Currently ALL 24,865 stops in the graph have wheelchairAccessible = false.
This is incorrect — many London stations have step-free access.

Here are excerpts from the TfL Annual Report discussing accessibility:

{context_text}

Based on the report, list London stations that ARE wheelchair accessible
(have step-free access from street to platform).

Return a JSON array with "station_name" and "accessible" (true/false) fields.
Focus on stations explicitly mentioned in the report as having step-free access.
Only return the JSON array, no other text.

Example:
[{{"station_name": "King's Cross St Pancras", "accessible": true}}]
"""

    print(f"  Querying LLM for accessibility info from {len(passages)} passages...")
    raw = query_ollama(prompt, model)
    results = parse_json_response(raw)

    # Get station URI lookup
    qres = g.query("""
        SELECT ?station ?name WHERE {
            ?station a lt:TrainStation .
            ?station lt:name ?name
        }
    """, initNs={"lt": LT, "gtfs": GTFS})
    station_lookup = {}
    for row in qres:
        station_lookup[str(row[1]).lower()] = str(row[0])

    triples_added = 0
    if results and isinstance(results, list):
        for item in results:
            stn_name = item.get("station_name", "")
            accessible = item.get("accessible", False)
            if not stn_name or not accessible:
                continue
            # Find station URI
            stn_uri = station_lookup.get(stn_name.lower())
            if not stn_uri:
                for existing_name, existing_uri in station_lookup.items():
                    if stn_name.lower() in existing_name or existing_name in stn_name.lower():
                        stn_uri = existing_uri
                        break
            if stn_uri:
                # Remove old false value and set true
                g.remove((URIRef(stn_uri), LT.wheelchairAccessible, None))
                g.add((URIRef(stn_uri), LT.wheelchairAccessible,
                       Literal(True, datatype=XSD.boolean)))
                triples_added += 1

    print(f"  Updated {triples_added} stations to wheelchairAccessible = true")
    log.append({
        "gap": "I8", "task": "Station accessibility",
        "triples_added": triples_added,
        "passages_retrieved": len(passages),
    })


# Ontology completion — add missing classes and properties
def complete_ontology(g, log):
    """Add the 8 missing ontology elements identified in the analysis."""
    print("\n--- Completing ontology gaps ---")
    triples_before = len(g)

    # O1: FareZone class and inFareZone property
    g.add((LT.FareZone, RDF.type, OWL.Class))
    g.add((LT.FareZone, RDFS.label, Literal("Fare Zone")))
    g.add((LT.FareZone, RDFS.subClassOf, LT.TransportEntity))
    g.add((LT.inFareZone, RDF.type, OWL.ObjectProperty))
    g.add((LT.inFareZone, RDFS.label, Literal("in fare zone")))
    g.add((LT.inFareZone, RDFS.domain, LT.Stop))
    g.add((LT.inFareZone, RDFS.range, LT.FareZone))

    # O3: Borough class and inBorough property
    g.add((LT.Borough, RDF.type, OWL.Class))
    g.add((LT.Borough, RDFS.label, Literal("Borough")))
    g.add((LT.Borough, RDFS.subClassOf, LT.Place))
    g.add((LT.inBorough, RDF.type, OWL.ObjectProperty))
    g.add((LT.inBorough, RDFS.label, Literal("in borough")))
    g.add((LT.inBorough, RDFS.domain, LT.Stop))
    g.add((LT.inBorough, RDFS.range, LT.Borough))

    # O4: AccessibilityFeature class and hasAccessibilityFeature property
    g.add((LT.AccessibilityFeature, RDF.type, OWL.Class))
    g.add((LT.AccessibilityFeature, RDFS.label, Literal("Accessibility Feature")))
    g.add((LT.AccessibilityFeature, RDFS.subClassOf, LT.TransportEntity))
    g.add((LT.StepFreeAccess, RDF.type, OWL.Class))
    g.add((LT.StepFreeAccess, RDFS.label, Literal("Step-Free Access")))
    g.add((LT.StepFreeAccess, RDFS.subClassOf, LT.AccessibilityFeature))
    g.add((LT.hasAccessibilityFeature, RDF.type, OWL.ObjectProperty))
    g.add((LT.hasAccessibilityFeature, RDFS.label, Literal("has accessibility feature")))
    g.add((LT.hasAccessibilityFeature, RDFS.domain, LT.Stop))
    g.add((LT.hasAccessibilityFeature, RDFS.range, LT.AccessibilityFeature))

    # O5: Interchange class and properties
    g.add((LT.Interchange, RDF.type, OWL.Class))
    g.add((LT.Interchange, RDFS.label, Literal("Interchange")))
    g.add((LT.Interchange, RDFS.subClassOf, LT.TransportEntity))
    g.add((LT.hasInterchange, RDF.type, OWL.ObjectProperty))
    g.add((LT.hasInterchange, RDFS.label, Literal("has interchange")))
    g.add((LT.hasInterchange, RDFS.domain, LT.Stop))
    g.add((LT.hasInterchange, RDFS.range, LT.Interchange))
    g.add((LT.transferTime, RDF.type, OWL.DatatypeProperty))
    g.add((LT.transferTime, RDFS.label, Literal("transfer time")))
    g.add((LT.transferTime, RDFS.domain, LT.Interchange))
    g.add((LT.transferTime, RDFS.range, XSD.integer))

    # O6: modeOfTransport property
    g.add((LT.modeOfTransport, RDF.type, OWL.DatatypeProperty))
    g.add((LT.modeOfTransport, RDFS.label, Literal("mode of transport")))
    g.add((LT.modeOfTransport, RDFS.domain, LT.TransportLine))
    g.add((LT.modeOfTransport, RDFS.range, XSD.string))

    # O7: Fare class and fareAmount property
    g.add((LT.Fare, RDF.type, OWL.Class))
    g.add((LT.Fare, RDFS.label, Literal("Fare")))
    g.add((LT.Fare, RDFS.subClassOf, LT.TransportEntity))
    g.add((LT.fareAmount, RDF.type, OWL.DatatypeProperty))
    g.add((LT.fareAmount, RDFS.label, Literal("fare amount")))
    g.add((LT.fareAmount, RDFS.domain, LT.Fare))
    g.add((LT.fareAmount, RDFS.range, XSD.decimal))
    g.add((LT.fareType, RDF.type, OWL.DatatypeProperty))
    g.add((LT.fareType, RDFS.label, Literal("fare type")))
    g.add((LT.fareType, RDFS.domain, LT.Fare))
    g.add((LT.fareType, RDFS.range, XSD.string))
    g.add((LT.hasFare, RDF.type, OWL.ObjectProperty))
    g.add((LT.hasFare, RDFS.label, Literal("has fare")))
    g.add((LT.hasFare, RDFS.range, LT.Fare))

    # O8: lineColour property
    g.add((LT.lineColour, RDF.type, OWL.DatatypeProperty))
    g.add((LT.lineColour, RDFS.label, Literal("line colour")))
    g.add((LT.lineColour, RDFS.domain, LT.TransportLine))
    g.add((LT.lineColour, RDFS.range, XSD.string))

    triples_added = len(g) - triples_before
    print(f"  Added {triples_added} ontology triples")
    log.append({
        "gap": "O1,O3,O4,O5,O6,O7,O8", "task": "Ontology completion",
        "triples_added": triples_added,
    })


# Main
def main():
    import argparse
    parser = argparse.ArgumentParser(description="RAG-based KG completion")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Only run ontology completion (no LLM needed)")
    args = parser.parse_args()

    g = load_kg()
    pages = load_pages()
    print(f"Loaded {len(pages)} pages of report text")

    log = []

    # Always run ontology completion 
    complete_ontology(g, log)

    if not args.skip_llm:
        try:
            requests.get(OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=5)
        except requests.exceptions.ConnectionError:
            print("\nERROR: Ollama is not running. Start with: ollama serve")
            print("Use --skip-llm to only run ontology completion.")
            sys.exit(1)

        # Run instance completions via RAG
        complete_line_operators(g, pages, args.model, log)
        complete_stop_locations(g, pages, args.model, log)
        complete_entity_links(g, pages, args.model, log)
        complete_operator_names(g, pages, args.model, log)
        complete_trip_headsigns(g, pages, args.model, log)
        complete_line_routes(g, pages, args.model, log)
        complete_tube_stations(g, pages, args.model, log)
        complete_accessibility(g, pages, args.model, log)

    OUTPUT_KG_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nSerialising completed KG to {OUTPUT_KG_PATH} ...")
    g.serialize(destination=str(OUTPUT_KG_PATH), format="turtle")
    print(f"Total triples: {len(g)}")

    # Save log
    with open(OUTPUT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    print(f"Completion log saved to {OUTPUT_LOG_PATH}")

    total_added = sum(entry.get("triples_added", 0) for entry in log)
    print(f"\n=== SUMMARY ===")
    print(f"Total new triples added: {total_added}")
    for entry in log:
        print(f"  [{entry['gap']}] {entry['task']}: +{entry['triples_added']} triples")


if __name__ == "__main__":
    main()
