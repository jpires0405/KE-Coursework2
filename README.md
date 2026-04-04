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
```

For Steps 5 and 7 (LLM extraction and RAG completion), you also need [Ollama](https://ollama.com/) running locally:

```bash
ollama serve          # start the server (keep running in background)
ollama pull llama3    # download the model (one-time, ~4 GB)
```

## Reproducing the Pipeline

Run these commands in order from the project root, with the virtual environment activated.

### Step 1 — Download data

```bash
# Download London GTFS feed (~294 MB)
python src/ingestion/download_gtfs.py

# Download TfL Annual Report PDF (~26 MB)
python src/ingestion/download_tfl_report.py
```

The `tfl.json` file should already be in `data/raw/`. If not, download it from the GitHub repo and place it there.

**Output:**
- `data/raw/london_gtfs/` — GTFS CSV files (stops.txt, routes.txt, trips.txt, etc.)
- `data/raw/tfl_annual_report_2024_25.pdf`
- `data/raw/tfl.json` (pre-existing)

### Step 2 — Extract text from PDF

```bash
python src/processing/parse_pdf.py
```

Extracts all text from the TfL Annual Report page by page.

**Output:** `data/processed/tfl_report_text.txt` (255 pages of text)

### Step 3 — Map structured data to RDF

```bash
# Map GTFS CSVs to RDF triples
python -m src.kg.map_gtfs

# Map TfL JSON to RDF triples
python -m src.kg.map_tfl_json
```

**Output:**
- `data/kg/gtfs_kg.ttl` — ~443k triples (agencies, stops, routes, trips, stop times)
- `data/kg/tfl_lines_kg.ttl` — ~2.3k triples (727 transport lines)

### Step 4 — Extract entities from PDF using LLM

Requires Ollama running with `llama3`.

```bash
# Extract from all pages (slow, processes 255 pages one by one)
python -m src.llm.extract --model llama3

# Or extract from a specific page range (faster)
python -m src.llm.extract --model llama3 --pages 1-20
```

Sends each page of the PDF to the LLM with an ontology-aware prompt. The LLM returns structured JSON with entities (TransportLine, Station, Operator, etc.) and relations (operatedBy, connectsTo, etc.).

**Output:** `data/processed/llm_extractions.json`

### Step 5 — Convert LLM output to RDF

```bash
python -m src.mapping.to_rdf
```

Maps the extracted entities and relations from JSON to RDF triples using the London Transport namespace.

**Output:** `data/processed/llm_extracted_graph.ttl`

### Step 6 ��� Merge all graphs into one KG

```bash
python -m src.kg.combine_kg
```

Merges `gtfs_kg.ttl` + `tfl_lines_kg.ttl` + `llm_extracted_graph.ttl` into a single unified knowledge graph.

**Output:** `data/kg/public_transport.ttl` (~445k triples)

### Step 7 — KG completion analysis

```bash
python -m src.kg.completion_analysis
```

Runs SPARQL queries against the merged KG to identify and document incomplete ontology and instance elements. Outputs a structured JSON report with evidence for each gap.

**Output:** `data/kg/completion_report.json`

### Step 8 — RAG-based KG completion

Requires Ollama running with `llama3`.

```bash
# Full run (ontology fixes + RAG instance completion)
python -m src.llm.rag_completion --model llama3

# Ontology-only mode (no LLM needed)
python -m src.llm.rag_completion --skip-llm
```

For each identified gap, the RAG pipeline:
1. Queries the KG (SPARQL) for incomplete entities
2. Retrieves relevant passages from the PDF report text
3. Sends KG context + PDF passages to the LLM
4. Patches the LLM's response back as new RDF triples

**Output:**
- `data/kg/completed_kg.ttl` — the completed knowledge graph (~446k triples, +1,078 new)
- `data/kg/rag_completion_log.json` — log of what was added per gap

## KG Completion Summary

The completion analysis identified 8 ontology gaps and 8 instance gaps:

### Incomplete Ontology Elements

| ID | Gap | Resolution |
|----|-----|------------|
| O1 | No FareZone class (zones 1-9) | Added FareZone class + inFareZone property |
| O2 | hasRoute property unused (0 links) | Populated via RAG entity linking |
| O3 | No Borough class for spatial context | Added Borough class + inBorough property |
| O4 | Accessibility is a single boolean | Added AccessibilityFeature class hierarchy |
| O5 | No Interchange class for transfers | Added Interchange class + transferTime property |
| O6 | No modeOfTransport property | Added modeOfTransport datatype property |
| O7 | No Fare or pricing class | Added Fare class + fareAmount/fareType properties |
| O8 | No line colour property | Added lineColour datatype property |

### Incomplete Instance Elements

| ID | Gap | Before | After RAG |
|----|-----|--------|-----------|
| I1 | TransportLine missing operatedBy | 1/704 had operator | +99 triples |
| I2 | Stops missing locatedIn borough | 0/24,865 had location | +29 triples |
| I3 | LLM entities disconnected from GTFS | 8 entities unlinked | +77 triples |
| I4 | Operators missing names | 1/57 had name | +2 triples |
| I5 | Trips missing headsigns | 0/10,000 had names | +20 triples |
| I6 | Routes missing hasStop links | 0/1,102 linked to stops | +737 triples |
| I7 | TubeLines missing servesStation | 0/11 linked to stations | +48 triples |
| I8 | All stops marked not accessible | 0/24,865 marked true | +9 triples |

## Project Structure

```
KE-Coursework2/
├── src/
│   ├── ingestion/              # Data download scripts
│   │   ├── download_gtfs.py
│   │   ├── download_tfl_report.py
│   │   └── tfl_api.py          # Requires TFL_API_KEY env variable
│   ├── processing/             # Data parsing
│   │   ├── parse_gtfs.py       # Parses GTFS CSV files
│   │   └── parse_pdf.py        # Extracts text from TfL report PDF
│   ├── kg/                     # Knowledge graph construction
│   │   ├── ontology.py         # Ontology definition (extends GTFS + Schema.org)
│   │   ├── map_gtfs.py         # GTFS CSV → RDF mapping
│   │   ├── map_tfl_json.py     # TfL JSON → RDF mapping
│   │   ├── combine_kg.py       # Merges all .ttl files into one KG
│   │   └── completion_analysis.py  # SPARQL gap analysis
│   ├── mapping/                # LLM output → RDF conversion
│   │   └── to_rdf.py           # JSON extractions → RDF triples
│   └── llm/                    # LLM pipelines
│       ├── extract.py          # PDF → LLM → structured JSON
│       └── rag_completion.py   # RAG-based KG completion
├── data/
│   ├── raw/                    # Source data (GTFS, tfl.json, PDF)
│   ├── processed/              # Extracted text, LLM JSON, LLM graph
│   └── kg/                     # Generated .ttl files + completion reports
├── docs/
│   └── ke_prompts_log.md       # Prompt log for data sourcing
└── requirements.txt
```

## Data Sources

| Source | Type | Format | Description |
|--------|------|--------|-------------|
| London GTFS feed | Structured | CSV | 24,865 stops, 1,102 routes, 475k trips, 17.9M stop times |
| TfL API | Structured | JSON | 727 transport lines across all modes |
| TfL Annual Report 2024/25 | Unstructured | PDF | Official report for LLM-based extraction |

## Dependencies

- `rdflib` — RDF graph library for building and querying the KG
- `requests` — HTTP requests for TfL API and Ollama
- `pdfplumber` — PDF text extraction
- [Ollama](https://ollama.com/) — local LLM runtime (for Steps 4 and 8)
