"""
LLM-Augmented Competency Question generation for the London Transport KG.

Uses Groq (Llama-3.3-70b-versatile) to generate 10 CQs that complement
the 10 manually authored CQs. The manual CQs are passed as context so the
LLM produces questions that are genuinely additive — targeting deeper domain
insights and cross-referencing GTFS structured data with TfL Annual Report text.

Output: appends CQ11–CQ20 to docs/requirements.md

Usage:
  export GROQ_API_KEY="your-key"
  python src/llm/generate_augmented_cqs.py
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_PATH = REPO_ROOT / "docs" / "requirements.md"

GROQ_MODEL = "llama-3.3-70b-versatile"

# ── The 10 manually authored CQs ──────────────────────────────────────────────
MANUAL_CQS = """
CQ1:  What transport operators are in this ontology?
CQ2:  What are the names of all tube lines available?
CQ3:  Which stations are served by the Piccadilly line?
CQ4:  Which bus routes are operated by 'National Express'?
CQ5:  Which stops are located in Wandsworth?
CQ6:  What are the operational dates for 'Service 33'?
CQ7:  Which routes are mentioned in the TfL Annual Report?
CQ8:  What are the coordinates of 'Plaistow Green'?
CQ9:  Which stops are wheelchair accessible?
CQ10: Which lines have night service?
""".strip()


def build_system_prompt() -> str:
    return (
        "You are an expert Knowledge Engineer specialising in public transport ontologies and SPARQL-queryable Knowledge Graphs. "
        "You have deep familiarity with the London transport network — including TfL's bus, Tube, Overground, DLR, Elizabeth line, "
        "Tram, and River Bus services — and with the GTFS data standard (routes, stops, trips, stop_times, services, agencies). "
        "Your task is to generate Competency Questions (CQs) that are precise, non-trivial, and directly answerable by a SPARQL query "
        "over a Knowledge Graph built from two sources: (1) structured GTFS schedule data and (2) unstructured text from the TfL Annual Report 2024/25."
    )


def build_user_prompt() -> str:
    return f"""
## Context

We are building a London Transport Knowledge Graph (KG) that combines two data sources:
- **Structured source:** London GTFS feed (routes, stops, trips, stop_times, calendar, agencies)
- **Unstructured source:** TfL Annual Report 2024/25 (LLM-extracted entities: lines, stations, operators, ridership statistics, projects)

The ontology uses the `lt:` namespace (`http://example.org/london-transport#`) with classes including:
`lt:TransportOperator`, `lt:TransportLine` (and subclasses: `lt:TubeLine`, `lt:DLRLine`, `lt:OvergroundLine`,
`lt:ElizabethLine`, `lt:BusLine`, `lt:TramLine`, `lt:RiverBusLine`), `lt:Route`, `lt:BusRoute`, `lt:TrainRoute`,
`lt:Stop`, `lt:BusStop`, `lt:TrainStation`, `lt:Service`, `lt:Trip`, `lt:StopTime`, `lt:Place`, `lt:Report`.

Key properties include: `lt:operatedBy`, `lt:hasRoute`, `lt:hasStop`, `lt:onRoute`, `lt:belongsToService`,
`lt:stopsAt`, `lt:connectsTo`, `lt:servesStation`, `lt:mentionedInReport`, `lt:wheelchairAccessible`,
`lt:latitude`, `lt:longitude`, `lt:stopCode`, `lt:routeNumber`, `lt:startDate`, `lt:endDate`,
`lt:arrivalTime`, `lt:departureTime`, `lt:hasRidership`, `lt:hasFrequency`, `lt:lineColour`.

## Already-authored Manual CQs (DO NOT repeat or closely paraphrase these)

{MANUAL_CQS}

## Task

Generate exactly **10 new Competency Questions** (CQ11–CQ20) that:

1. **Complement** the manual CQs above — do not repeat or trivially rephrase them.
2. Target **deeper domain insights** — e.g. multi-hop queries, aggregations, comparisons across lines or operators.
3. At least **3 questions** must require **cross-referencing** both data sources — i.e. combining GTFS schedule facts with entities or statistics mentioned in the TfL Annual Report (use `lt:mentionedInReport` or `lt:hasRidership`/`lt:hasFrequency`).
4. At least **2 questions** must involve **accessibility or interchange** (e.g. `lt:wheelchairAccessible`, `lt:Interchange`, or multi-modal connections).
5. Questions must be answerable by SPARQL over the KG — avoid questions that require free-text reasoning.
6. Write each question as a clear, natural-language sentence ending with a question mark.

## Output Format

Return ONLY a numbered list of 10 questions, one per line, in this exact format:

CQ11: <question text>
CQ12: <question text>
...
CQ20: <question text>

No preamble, no explanation, no commentary — just the 10 lines.
""".strip()


def extract_cqs(response_text: str) -> list[str]:
    """Extract CQ11–CQ20 lines from the LLM response."""
    lines = []
    for line in response_text.splitlines():
        line = line.strip()
        if re.match(r"CQ(1[1-9]|20):", line):
            lines.append(line)
    return lines


def append_to_requirements(cqs: list[str]) -> None:
    """Append the generated CQs as a markdown table to docs/requirements.md."""
    if not REQUIREMENTS_PATH.exists():
        print(f"ERROR: {REQUIREMENTS_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    rows = []
    for cq_line in cqs:
        match = re.match(r"(CQ\d+):\s*(.+)", cq_line)
        if match:
            rows.append(f"| {match.group(1)} | {match.group(2).strip()} |")

    table = "\n".join(rows)

    existing = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    # Replace the trailing placeholder line if present
    updated = existing.rstrip() + "\n\n" + table + "\n"
    REQUIREMENTS_PATH.write_text(updated, encoding="utf-8")
    print(f"Appended {len(rows)} CQs to {REQUIREMENTS_PATH}")


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

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt()

    print(f"Calling Groq ({GROQ_MODEL}) ...")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content
    print("Response received.\n")
    print(raw)

    cqs = extract_cqs(raw)
    if len(cqs) < 10:
        print(f"WARNING: only {len(cqs)} CQs extracted (expected 10). Check raw output above.", file=sys.stderr)

    append_to_requirements(cqs)


if __name__ == "__main__":
    run()
