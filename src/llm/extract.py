"""
LLM-based entity and relation extraction from TfL Annual Report text.

Sends extracted PDF text to a local Ollama model (default: llama3) and
produces structured JSON output that can be converted to RDF triples
by to_rdf.py.

Usage:
    python -m src.llm.extract                  # run full extraction
    python -m src.llm.extract --pages 3-10     # extract from specific pages
    python -m src.llm.extract --model mistral  # use a different Ollama model
"""

import json
import os
import re
import argparse
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
INPUT_PATH = os.path.join(BASE_DIR, "data", "processed", "tfl_report_text.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "llm_extractions.json")

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3"

# Ontology context passed to the LLM so it extracts domain-relevant entities
ONTOLOGY_CONTEXT = """You are extracting knowledge about London public transport from an official TfL report.

Extract entities and relationships relevant to a transport knowledge graph.

Entity types to look for:
- TransportLine: tube lines, DLR, overground lines, elizabeth line, tram, bus routes, river bus
- Station: train stations, tube stations, bus stops, DLR stations
- TransportOperator: organisations operating transport services (e.g. TfL, Arriva)
- Route: specific routes or services
- Place: boroughs, areas, landmarks connected by transport
- Statistic: ridership numbers, journey counts, performance metrics

Relationship types to look for:
- operatedBy: who operates a line/route
- hasStop / servesStation: which stations a line serves
- connectsTo: connections between lines or places
- locatedIn: where a station or line is located
- hasRidership: passenger numbers for a line/station
- hasFrequency: service frequency information

Return ONLY valid JSON in this exact format (no other text):
{
  "entities": [
    {"name": "...", "type": "...", "description": "..."}
  ],
  "relations": [
    {"subject": "...", "predicate": "...", "object": "...", "context": "..."}
  ]
}"""


def load_pages(input_path=INPUT_PATH):
    """Load extracted PDF text and split into pages."""
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    pages = []
    chunks = re.split(r"--- Page (\d+) ---\n", content)
    # chunks = ['', '1', 'page 1 text...', '2', 'page 2 text...', ...]
    for i in range(1, len(chunks), 2):
        page_num = int(chunks[i])
        text = chunks[i + 1].strip()
        if text:
            pages.append({"page_number": page_num, "text": text})
    return pages


def query_ollama(text, model=DEFAULT_MODEL):
    """Send text to Ollama and get structured extraction back."""
    prompt = f"""{ONTOLOGY_CONTEXT}

--- TEXT ---
{text}
--- END TEXT ---

Extract all transport-related entities and relationships from the text above.
Return ONLY the JSON object, no explanations."""

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2048,
        },
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["response"]


def parse_llm_response(raw_response):
    """Parse JSON from LLM response, handling common formatting issues."""
    text = raw_response.strip()

    # Try to find JSON block in the response
    json_match = re.search(r"\{[\s\S]*\}", text)
    if not json_match:
        return None

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        return None


def extract_from_pages(pages, model=DEFAULT_MODEL):
    """Run extraction on a list of pages, return all results."""
    all_results = []

    for page in pages:
        page_num = page["page_number"]
        text = page["text"]

        # Skip very short pages (table of contents, headers, etc.)
        if len(text) < 100:
            print(f"  Page {page_num}: skipped (too short)")
            continue

        print(f"  Page {page_num}: extracting...", end=" ", flush=True)

        try:
            raw = query_ollama(text, model=model)
            parsed = parse_llm_response(raw)

            if parsed and ("entities" in parsed or "relations" in parsed):
                entities = parsed.get("entities", [])
                relations = parsed.get("relations", [])
                all_results.append({
                    "page": page_num,
                    "entities": entities,
                    "relations": relations,
                })
                print(f"{len(entities)} entities, {len(relations)} relations")
            else:
                print("no valid JSON returned")
                all_results.append({
                    "page": page_num,
                    "entities": [],
                    "relations": [],
                    "raw_response": raw[:500],
                })
        except requests.exceptions.ConnectionError:
            print("FAILED (is Ollama running? Start with: ollama serve)")
            raise SystemExit(1)
        except Exception as e:
            print(f"FAILED ({e})")
            all_results.append({
                "page": page_num,
                "entities": [],
                "relations": [],
                "error": str(e),
            })

    return all_results


def save_results(results, output_path=OUTPUT_PATH):
    """Save extraction results to JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Compute summary stats
    total_entities = sum(len(r.get("entities", [])) for r in results)
    total_relations = sum(len(r.get("relations", [])) for r in results)

    output = {
        "metadata": {
            "source": "tfl_annual_report_2024_25.pdf",
            "pages_processed": len(results),
            "total_entities": total_entities,
            "total_relations": total_relations,
        },
        "pages": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_path}")
    print(f"  Pages processed: {len(results)}")
    print(f"  Total entities:  {total_entities}")
    print(f"  Total relations: {total_relations}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Extract entities from TfL report using LLM")
    parser.add_argument("--pages", type=str, default=None,
                        help="Page range to process, e.g. '3-10' or '5' (default: all)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"Ollama model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--input", type=str, default=INPUT_PATH,
                        help="Path to extracted text file")
    parser.add_argument("--output", type=str, default=OUTPUT_PATH,
                        help="Path for JSON output")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file not found: {args.input}")
        print("Run 'python -m src.processing.parse_pdf' first to extract text.")
        raise SystemExit(1)

    print(f"Loading text from {args.input}")
    pages = load_pages(args.input)
    print(f"Found {len(pages)} pages")

    # Filter to requested page range
    if args.pages:
        if "-" in args.pages:
            start, end = map(int, args.pages.split("-"))
        else:
            start = end = int(args.pages)
        pages = [p for p in pages if start <= p["page_number"] <= end]
        print(f"Filtering to pages {start}-{end} ({len(pages)} pages)")

    print(f"\nExtracting with model: {args.model}")
    results = extract_from_pages(pages, model=args.model)
    save_results(results, args.output)


if __name__ == "__main__":
    main()
