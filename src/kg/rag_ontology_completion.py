"""
RAG-based ontology completion for the London Transport Knowledge Graph.

Uses Groq (Llama-3) as the LLM. The existing ontology schema (ontology.py)
is read at runtime and injected as retrieval context into the prompt, making
this a Retrieval-Augmented Generation (RAG) workflow.

Identified TBox gaps (8 missing elements):
  1. No lt:FareZone class
  2. lt:hasRoute exists but has no domain/range and is unused in instances
  3. No lt:Borough class
  4. Accessibility modelled only as a boolean — no structured class
  5. No lt:Interchange class for multimodal interchange stations
  6. No lt:modeOfTransport property
  7. No lt:Fare / lt:FareTier pricing class
  8. No lt:lineColour datatype property

Output: data/kg/ontology_extensions_rag.ttl

Usage:
  export GROQ_API_KEY="your-key"
  python src/kg/rag_ontology_completion.py
"""

import os
import re
import sys
from pathlib import Path

from rdflib import Graph

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_SRC = REPO_ROOT / "src" / "kg" / "ontology.py"
OUTPUT_PATH = REPO_ROOT / "data" / "kg" / "ontology_extensions_rag.ttl"

# ── Model config ───────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"

# ── Identified TBox gaps ───────────────────────────────────────────────────────
TBOX_GAPS = """
1. No lt:FareZone class — the KG cannot represent which fare zone a stop belongs to.
2. lt:hasRoute exists but has no domain/range constraints and is unused in instances.
3. No lt:Borough class — the KG cannot link stops or lines to London boroughs.
4. Accessibility is only a boolean (lt:wheelchairAccessible) — no structured lt:AccessibilityFeature class for richer descriptions.
5. No lt:Interchange class — multimodal interchange stations (e.g., Stratford, King's Cross) cannot be typed distinctly.
6. No lt:modeOfTransport property — no way to state which transport mode (bus, tube, rail, tram) a route or line uses.
7. No lt:Fare or lt:FareTier class — the KG cannot represent fare/pricing information.
8. No lt:lineColour datatype property — TfL lines have official colours that are not captured.
""".strip()


def load_ontology_source() -> str:
    """Read ontology.py as plain text — this is the retrieval context for RAG."""
    if not ONTOLOGY_SRC.exists():
        print(f"WARNING: ontology source not found at {ONTOLOGY_SRC}", file=sys.stderr)
        return ""
    return ONTOLOGY_SRC.read_text(encoding="utf-8")


def build_system_prompt() -> str:
    return (
        "You are an expert Knowledge Graph Engineer specialising in public transport ontologies. "
        "You write precise, valid OWL/RDF in Turtle syntax using established ontology engineering principles. "
        "You always declare new classes as owl:Class with rdfs:label and rdfs:comment. "
        "You always declare new properties as owl:ObjectProperty or owl:DatatypeProperty with "
        "rdfs:label, rdfs:comment, rdfs:domain, and rdfs:range. "
        "You use subClassOf and subPropertyOf to integrate new elements into the existing hierarchy. "
        "You output ONLY a single fenced Turtle code block — no prose before or after."
    )


def build_user_prompt(ontology_source: str) -> str:
    return f"""
## Existing Ontology (Retrieval Context)

The following is the complete source of our current London Transport ontology, defined in Python using rdflib.
Read it carefully — all new elements must integrate with the existing namespace, class hierarchy, and property set.

```python
{ontology_source}
```

---

## Task

The ontology above has the following **8 identified TBox gaps** that must be resolved:

{TBOX_GAPS}

---

## Instructions

Generate valid OWL/RDF Turtle that resolves **all 8 gaps**. Your output must:

1. Use the namespace prefix `lt: <http://example.org/london-transport#>` (already declared — do not redeclare it).
2. Also use `@prefix owl: <http://www.w3.org/2002/07/owl#> .`, `@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .`, `@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .`
3. For each new **class**: declare `rdf:type owl:Class`, `rdfs:subClassOf` (choose the correct parent from the existing hierarchy, e.g. `lt:TransportEntity`), `rdfs:label`, and `rdfs:comment`.
4. For each new **property**: declare `rdf:type owl:ObjectProperty` or `owl:DatatypeProperty`, `rdfs:subPropertyOf` where applicable, `rdfs:domain`, `rdfs:range`, `rdfs:label`, and `rdfs:comment`.
5. For gap 2 (lt:hasRoute unused): add the missing `rdfs:domain` and `rdfs:range` constraints to the existing `lt:hasRoute` property and add an example usage comment.
6. Output ONLY a single ```turtle ... ``` fenced code block. No explanations outside the block.
""".strip()


def extract_turtle(response_text: str) -> str:
    """Extract Turtle code from a fenced ```turtle ... ``` block."""
    # Try explicit turtle fence first, then generic code fence
    for pattern in [r"```turtle\s*\n(.*?)```", r"```\s*\n(.*?)```"]:
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    # Fallback: return everything (LLM may have dropped fences)
    return response_text.strip()


def validate_turtle(ttl_str: str) -> Graph:
    """Parse the Turtle with rdflib; raise on syntax error."""
    g = Graph()
    g.parse(data=ttl_str, format="turtle")
    return g


def run() -> None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    try:
        from groq import Groq
    except ImportError:
        print("ERROR: groq package not installed. Run: pip install groq", file=sys.stderr)
        sys.exit(1)

    # ── RAG: load retrieval context ────────────────────────────────────────────
    print(f"Loading ontology context from {ONTOLOGY_SRC} ...")
    ontology_source = load_ontology_source()
    print(f"  Context loaded ({len(ontology_source)} chars)")

    # ── Build prompts ──────────────────────────────────────────────────────────
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(ontology_source)

    # ── Call Groq LLM ──────────────────────────────────────────────────────────
    print(f"Calling Groq ({GROQ_MODEL}) ...")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.1,   # low temperature for deterministic ontology output
        max_tokens=4096,
    )

    raw_response = response.choices[0].message.content
    print("Response received.")

    # ── Extract Turtle ─────────────────────────────────────────────────────────
    ttl_str = extract_turtle(raw_response)

    # ── Validate with rdflib ───────────────────────────────────────────────────
    print("Validating Turtle syntax ...")
    try:
        g = validate_turtle(ttl_str)
        print(f"  Valid — {len(g)} triples parsed.")
    except Exception as e:
        print(f"WARNING: Turtle validation failed: {e}", file=sys.stderr)
        print("Raw LLM output saved anyway for inspection.", file=sys.stderr)

    # ── Save output ────────────────────────────────────────────────────────────
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(ttl_str, encoding="utf-8")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    run()