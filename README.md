# KE-Coursework2

London Public Transport Knowledge Graph — 5CCSAKNE Knowledge Engineering Coursework 2

## Setup

```bash
# Clone the repo
git clone https://github.com/jpires0405/KE-Coursework2.git
cd KE-Coursework2

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Also install groq (required for RAG completion and CQ generation steps)
pip install groq
```

**LLM requirements — two providers are used at different stages:**

| Stage | Provider | Setup |
|-------|----------|-------|
| Step 4 — PDF entity extraction | [Ollama](https://ollama.com/) (local) | `ollama serve` + `ollama pull llama3` |
| Steps 9, 10, 11, 12 — RAG completion & CQ generation | [Groq](https://console.groq.com/) (cloud) | `export GROQ_API_KEY="your-key"` |

```bash
# Ollama (keep running in the background for Steps 4 and 5)
ollama serve
ollama pull llama3    # one-time download, ~4 GB

# Groq
export GROQ_API_KEY="your-groq-api-key"
```

---

## Reproducing the Pipeline

Run these commands in order from the project root with the virtual environment activated.

---

### Step 1 — Download raw data

```bash
python src/ingestion/download_gtfs.py
python src/ingestion/download_tfl_report.py
```

`download_gtfs.py` fetches the London GTFS feed (a ZIP archive of CSV files) from the Traveline National Dataset and extracts it. `download_tfl_report.py` downloads the TfL Annual Report 2024/25 PDF directly from the TfL website. The `data/raw/tfl.json` file (727 TfL transport lines) is already committed to the repo.

**Expected output:**
```
data/raw/london_gtfs/
    agency.txt          # 57 transport operators
    stops.txt           # 24,865 stops
    routes.txt          # 1,102 routes
    trips.txt           # 475,000+ trips
    stop_times.txt      # 17.9M stop time records
    calendar.txt        # service calendar entries
data/raw/tfl_annual_report_2024_25.pdf   (~26 MB)
data/raw/tfl.json                        (already present)
```

---

### Step 2 — Extract text from the PDF

```bash
python src/processing/parse_pdf.py
```

Uses `pdfplumber` to read the TfL Annual Report page by page and write all extracted text to a single file. This text is later used as the retrieval corpus for RAG.

**Expected output:**
```
data/processed/tfl_report_text.txt    # 255 pages of plain text (~26 MB)
```

---

### Step 3 — Map structured data to RDF

```bash
python -m src.kg.map_gtfs
python -m src.kg.map_tfl_json
```

`map_gtfs.py` reads all GTFS CSV files and converts them to RDF triples using the London Transport ontology (`lt:` namespace) and the GTFS vocabulary (`gtfs:`). Trips are capped at 10,000 and stop times at 50,000 to keep the graph manageable.

`map_tfl_json.py` reads `data/raw/tfl.json` and creates `lt:TransportLine` instances (including subclasses: TubeLine, BusLine, DLRLine, OvergroundLine, ElizabethLine, TramLine, RiverBusLine, NationalRailLine) for all 727 TfL lines.

**Expected output:**
```
data/kg/gtfs_kg.ttl        # ~443,000 triples
                           # Agencies, Stops, Routes, Services, Trips, StopTimes
data/kg/tfl_lines_kg.ttl   # ~2,291 triples — 727 TransportLine instances
```

---

### Step 4 — Extract entities from the PDF using the LLM

Requires Ollama running locally with `llama3`.

```bash
# Extract from a specific page range (recommended for speed)
python -m src.llm.extract --model llama3 --pages 1-20

# Or extract from all 255 pages (slow — several hours)
python -m src.llm.extract --model llama3
```

Sends each PDF page to the local Llama-3 model with an ontology-aware extraction prompt. The LLM returns structured JSON containing entities (TransportLine, Station, Operator, etc.) and relations (operatedBy, connectsTo, etc.) mentioned on that page.

**Expected output:**
```
data/processed/llm_extractions.json   # JSON array of {page, entities, relations}
                                      # e.g. 3 pages → 8 entities, 8 relations
```

---

### Step 5 — Convert LLM output to RDF

```bash
python -m src.mapping.to_rdf
```

Reads `llm_extractions.json` and converts each extracted entity and relation into RDF triples using the `lt:` namespace. Entities become typed resources; relations become object property assertions.

**Expected output:**
```
data/processed/llm_extracted_graph.ttl   # ~49 triples (8 entities, 8 relations)
```

---

### Step 6 — Merge all graphs into one KG

```bash
python -m src.kg.combine_kg
```

Merges the three source graphs — `gtfs_kg.ttl`, `tfl_lines_kg.ttl`, and `llm_extracted_graph.ttl` — into a single unified knowledge graph.

**Expected output:**
```
data/kg/public_transport.ttl   # ~445,244 triples
```

---

### Step 7 — KG completion analysis

```bash
python -m src.kg.completion_analysis
```

Runs targeted SPARQL queries against `public_transport.ttl` to identify structural gaps in the ontology (TBox) and missing instance data (ABox). Outputs a structured JSON report documenting each gap with evidence counts.

**Expected output:**
```
data/kg/completion_report.json   # 8 ontology gaps + 8 instance gaps documented
```

Sample output (printed to console):
```
[O1] No FareZone class or zone property on stops (query result: 0)
[O2] TransportLine has no hasRoute links defined in practice (query result: 0)
...
[I1] TransportLine instances lack operatedBy (704 lines, 1 with operator)
[I7] TubeLines have no servesStation links (11 lines, 0 with station)
...
```

---

### Step 8 — RAG-based KG completion (Ollama)

Requires Ollama running locally with `llama3`.

```bash
python -m src.llm.rag_completion --model llama3
```

For each identified gap, the pipeline: (1) queries the KG via SPARQL to retrieve incomplete entities, (2) uses TF-IDF to retrieve the most relevant passages from the PDF text, (3) sends KG context + passages to the LLM, and (4) parses the LLM's Turtle response and merges valid triples into the graph.

**Expected output:**
```
data/kg/completed_kg.ttl          # ~446,297 triples (+1,053 from public_transport.ttl)
data/kg/rag_completion_log.json   # log of triples added per gap
```

Sample log:
```json
[
  {"gap": "O1,O3,O4,O5,O6,O7,O8", "task": "Ontology completion", "triples_added": 57},
  {"gap": "I2", "task": "Stop locatedIn", "triples_added": 30},
  ...
]
```

After this step, copy the completed KG to prepare for the Groq RAG steps:

```bash
cp data/kg/completed_kg.ttl data/kg/final_submission_kg.ttl
```

---

### Step 9 — RAG ontology completion (Groq)

Requires `GROQ_API_KEY` to be set.

```bash
python src/kg/rag_ontology_completion.py
```

Reads the full ontology source (`src/kg/ontology.py`) as retrieval context and sends it to Groq's Llama-3.3-70b model with a prompt listing all 8 identified TBox gaps. The model returns OWL/RDF Turtle declaring new classes and properties. The output is validated with `rdflib` before saving.

**Expected output:**
```
data/kg/ontology_extensions_rag.ttl   # New OWL class/property declarations
                                      # e.g. lt:FareZone, lt:Borough,
                                      #      lt:Interchange, lt:modeOfTransport,
                                      #      lt:lineColour, lt:Fare, etc.
```

Console output:
```
Loading ontology context from src/kg/ontology.py ...
  Context loaded (4821 chars)
Calling Groq (llama-3.3-70b-versatile) ...
Response received.
Validating Turtle syntax ...
  Valid — 57 triples parsed.
Saved to data/kg/ontology_extensions_rag.ttl
```

Merge the extensions into the final KG:

```bash
python -c "
from rdflib import Graph
g = Graph()
g.parse('data/kg/final_submission_kg.ttl', format='turtle')
g.parse('data/kg/ontology_extensions_rag.ttl', format='turtle')
g.serialize('data/kg/final_submission_kg.ttl', format='turtle')
print(f'Final KG: {len(g):,} triples')
"
```

---

### Step 10 — Populate ABox instances (Groq)

Requires `GROQ_API_KEY` to be set.

```bash
python src/kg/rag_populate_instances.py
```

Reads `final_submission_kg.ttl` to extract named transport lines and major stations as retrieval context, then calls Groq to generate ABox instance triples that populate the new ontology classes added in Step 9. Specifically: `lt:lineColour` and `lt:modeOfTransport` for all named lines; `lt:FareZone` instances (zones 1–6) linked to 40 major stations; `lt:Borough` instances linked to stations; and `lt:Interchange` typing for major multi-modal stations. Merges the result directly back into `final_submission_kg.ttl`.

**Expected output:**
```
data/kg/rag_instances.ttl          # New ABox triples (saved separately for inspection)
data/kg/final_submission_kg.ttl    # Updated in place with instance triples merged in
```

Console output:
```
Loading data/kg/final_submission_kg.ttl ...
  446,354 triples loaded.
Calling Groq (llama-3.3-70b-versatile) ...
Response received.
Validating Turtle ...
  Valid — 312 new triples.
Saved instances to data/kg/rag_instances.ttl
Merging into data/kg/final_submission_kg.ttl ...
  Final KG now has 446,666 triples.
Done.
```

---

### Step 11 — Populate relations between lines and stations (Groq)

Requires `GROQ_API_KEY` to be set.

```bash
python src/kg/rag_populate_relations.py
```

Extracts the canonical line URIs and major station URIs from `final_submission_kg.ttl` and passes them to Groq as retrieval context. The model uses its knowledge of the real London transport network to generate `lt:servesStation` / `lt:isServedBy` links between tube lines and stations, `lt:intersectsWith` links between lines that share a station, and `lt:connectsTo` links between adjacent stations. Merges results back into `final_submission_kg.ttl`.

**Expected output:**
```
data/kg/rag_relations.ttl          # Relation triples (saved separately)
data/kg/final_submission_kg.ttl    # Updated with line-station and line-line relations
```

Console output:
```
Loading data/kg/final_submission_kg.ttl ...
  446,666 triples loaded.
  Context: 20 lines, 40 stations
Calling Groq (llama-3.3-70b-versatile) ...
Response received.
Validating Turtle ...
  Valid — 187 new triples.
Saved to data/kg/rag_relations.ttl
Merging into data/kg/final_submission_kg.ttl ...
  Final KG: 446,853 triples.
Done.
```

---

### Step 12 — Generate LLM-augmented competency questions (Groq)

Requires `GROQ_API_KEY` to be set. **Run once only** — output is already committed to `docs/requirements.md`.

```bash
python src/llm/generate_augmented_cqs.py
```

Passes the 10 manually authored competency questions (CQ1–CQ10) as context to Groq's Llama-3.3-70b model and instructs it to generate 10 complementary questions (CQ11–CQ20) targeting multi-hop queries, aggregations, and cross-source questions that join GTFS data with TfL Annual Report entities. Appends the results to `docs/requirements.md`.

**Expected output:**
```
docs/requirements.md    # CQ11–CQ20 appended as a markdown table
```

Console output:
```
Calling Groq (llama-3.3-70b-versatile) ...
Response received.

CQ11: What are the most frequently served stations by bus routes ...
...
CQ20: What are the names of all transport operators that operate bus routes ...

Appended 10 CQs to docs/requirements.md
```

---

### Step 13 — Run SPARQL competency questions

```bash
# CQ1–CQ10 (manually authored)
python src/sparql/competency.py

# CQ11–CQ20 (LLM-generated)
python src/sparql/llm_competency.py
```

Both scripts load `data/kg/final_submission_kg.ttl` and execute each competency question as a SPARQL query, printing results to the console.

**Expected output (competency.py):**
```
Executing CQ1: What transport operators are in this ontology?
  -> operatorName: National Express
  -> operatorName: Arriva London
  ...
--------------------------------------------------
Executing CQ2: Names of all tube lines available
  -> lineName: Bakerloo
  -> lineName: Central
  ...
--------------------------------------------------
Executing CQ8: Find the Coordinates of 'Plaistow Green'
  -> lat: 51.5389 | lon: 0.0147
--------------------------------------------------
```

---

### Step 14 — Run evaluation

```bash
# Evaluate the final submission KG (default)
python -m src.evaluation.evaluate

# Or evaluate a specific KG file
python -m src.evaluation.evaluate --kg data/kg/completed_kg.ttl
python -m src.evaluation.evaluate --kg data/kg/final_submission_kg.ttl
```

Loads the KG and computes: (1) performance metrics (file size, parse time, peak memory, total triples), (2) class instance distribution across all tracked ontology classes, (3) property completeness per class (how many instances have each required property), (4) source/integration metrics (entities linked to report, lines with routes, stations with serving routes), and (5) SPARQL competency question results (success rate, answer rate, per-query timing). Saves a full JSON report.

**Expected output (printed to console):**
```
────────────────────────────────────────────────────────────────────
London Transport KG — Evaluation Report
────────────────────────────────────────────────────────────────────
File            : final_submission_kg.ttl
File size       : 68.4 MB
Parse time      : 12.3 s
Peak memory     : 312.5 MB
Total triples   : 446,853

────────────────────────────────────────────────────────────────────
Tracked class distribution
────────────────────────────────────────────────────────────────────
TransportEntity          ...
Stop                     24865
BusStop                  ...
TrainStation             ...
Route                    1102
Trip                     10000
TransportLine            727
TubeLine                 11
...

────────────────────────────────────────────────────────────────────
Competency query summary
────────────────────────────────────────────────────────────────────
Total queries    : 10
Successful       : 10
Answered         : 8
Success rate     : 100.0%
Answer rate      : 80.0%
Average time     : 45.2 ms

────────────────────────────────────────────────────────────────────
Competency query details
────────────────────────────────────────────────────────────────────
ID    Answered  Success  Results  Time(ms)
CQ1   True      True     57       12.3
CQ2   True      True     11       8.1
CQ3   True      True     5        22.4
...
```

**Expected output (file):**
```
data/evaluation/evaluation_report.json   # Full JSON report with all metrics
```

---

## KG Completion Summary

The completion analysis identified 8 ontology gaps and 8 instance gaps:

### Incomplete Ontology Elements

| ID | Gap | Resolution |
|----|-----|------------|
| O1 | No FareZone class (zones 1–9) | Added `lt:FareZone` class + `lt:inFareZone` property |
| O2 | `lt:hasRoute` defined but zero instances use it | Added domain/range constraints; populated via RAG linking |
| O3 | No Borough class for spatial context | Added `lt:Borough` class + `lt:inBorough` property |
| O4 | Accessibility modelled as a single boolean | Added `lt:AccessibilityFeature` class hierarchy |
| O5 | No Interchange class for transfer stations | Added `lt:Interchange` class + `lt:transferTime` property |
| O6 | No modeOfTransport property | Added `lt:modeOfTransport` datatype property |
| O7 | No Fare or pricing class | Added `lt:Fare` + `lt:FareTier` classes with `lt:fareAmount` |
| O8 | No line colour property | Added `lt:lineColour` datatype property |

### Incomplete Instance Elements

| ID | Gap | Scale | RAG Result |
|----|-----|-------|------------|
| I1 | TransportLine missing `operatedBy` | 704 lines, 1 with operator | +1 triple |
| I2 | Stops missing `locatedIn` borough | 24,865 stops, 0 had location | +30 triples |
| I3 | LLM entities disconnected from GTFS data | 8 entities unlinked | +15 triples (`owl:sameAs`) |
| I4 | TransportOperator missing operational links | 57 operators, none linked to lines | +1 triple |
| I5 | Trips missing headsigns | 2,110 trips with no label | +20 triples |
| I6 | Routes missing `lt:hasStop` links | 1,102 routes, 0 linked to stops | 0 (PDF lacks GTFS IDs) |
| I7 | TubeLines missing `servesStation` links | 11 lines, 0 linked to stations | +16 triples |
| I8 | All 24,865 stops marked not accessible (GTFS mapping error) | 0 accessible | +9 corrections |

---

## Project Structure

```
KE-Coursework2/
├── src/
│   ├── ingestion/              # Data download scripts
│   │   ├── download_gtfs.py    # Downloads London GTFS feed ZIP
│   │   ├── download_tfl_report.py  # Downloads TfL Annual Report PDF
│   │   └── tfl_api.py          # TfL API client (requires TFL_API_KEY)
│   ├── processing/             # Data parsing
│   │   ├── parse_gtfs.py       # Parses GTFS CSVs into Python dicts
│   │   └── parse_pdf.py        # Extracts text from PDF (pdfplumber)
│   ├── kg/                     # Knowledge graph construction
│   │   ├── ontology.py         # Ontology definition (extends GTFS + Schema.org)
│   │   ├── map_gtfs.py         # GTFS CSV → RDF (443k triples)
│   │   ├── map_tfl_json.py     # TfL JSON → RDF (2.3k triples)
│   │   ├── combine_kg.py       # Merges all .ttl files → public_transport.ttl
│   │   ├── completion_analysis.py      # SPARQL gap analysis → completion_report.json
│   │   ├── rag_ontology_completion.py  # Groq RAG: fills TBox gaps → ontology_extensions_rag.ttl
│   │   ├── rag_populate_instances.py   # Groq RAG: populates ABox instances → rag_instances.ttl
│   │   └── rag_populate_relations.py   # Groq RAG: adds line↔station relations → rag_relations.ttl
│   ├── mapping/                # LLM output → RDF conversion
│   │   └── to_rdf.py           # JSON extractions → RDF triples
│   ├── llm/                    # LLM pipelines
│   │   ├── extract.py          # PDF → Ollama Llama-3 → structured JSON
│   │   ├── rag_completion.py   # Ollama RAG → completed_kg.ttl
│   │   └── generate_augmented_cqs.py  # Groq → CQ11–CQ20 → docs/requirements.md
│   ├── sparql/                 # SPARQL competency question runners
│   │   ├── competency.py       # Runs CQ1–CQ10 against final_submission_kg.ttl
│   │   └── llm_competency.py   # Runs CQ11–CQ20 against final_submission_kg.ttl
│   └── evaluation/             # KG evaluation
│       └── evaluate.py         # Performance + completeness + CQ evaluation → JSON report
├── data/
│   ├── raw/                    # Source data (GTFS CSVs, tfl.json, PDF)
│   ├── processed/              # Extracted PDF text, LLM JSON, LLM RDF graph
│   ├── kg/                     # Generated .ttl files
│   │   ├── gtfs_kg.ttl
│   │   ├── tfl_lines_kg.ttl
│   │   ├── public_transport.ttl
│   │   ├── completed_kg.ttl
│   │   ├── ontology_extensions_rag.ttl
│   │   ├── rag_instances.ttl
│   │   ├── rag_relations.ttl
│   │   └── final_submission_kg.ttl   # Final output — all steps merged
│   └── evaluation/
│       └── evaluation_report.json
├── docs/
│   ├── requirements.md         # 20 competency questions (CQ1–CQ20)
│   ├── ke_prompts_log.md       # All prompts used and their KE task
│   └── completion_analysis.tex # Completion analysis document (separate submission)
└── requirements.txt
```

---

## Data Sources

| Source | Type | Format | Scale |
|--------|------|--------|-------|
| London GTFS feed | Structured | CSV | 24,865 stops, 1,102 routes, 475k trips, 17.9M stop times |
| TfL API JSON | Structured | JSON | 727 transport lines across all modes |
| TfL Annual Report 2024/25 | Unstructured | PDF | 255 pages — used as RAG retrieval corpus |

---

## Dependencies

### Python packages (`requirements.txt`)
- `rdflib` — RDF graph library for building, querying, and serialising the KG
- `requests` — HTTP requests for data downloads
- `pdfplumber` — PDF text extraction
- `dotenv` — environment variable loading

### Additional install
- `groq` — Groq Python client (`pip install groq`), required for Steps 9–12

### External services
- [Ollama](https://ollama.com/) — local LLM runtime, required for Steps 4 and 8
- [Groq](https://console.groq.com/) — cloud LLM API, required for Steps 9–12 (free tier available)
