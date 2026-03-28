# KE-Coursework2

London Public Transport Knowledge Graph — 5CCSAKNE Knowledge Engineering Coursework 2

## Setup

```bash
# Clone the repo and switch to develop branch
git clone https://github.com/jpires0405/KE-Coursework2.git
cd KE-Coursework2
git checkout develop

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt
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

### Step 2 — Extract text from PDF

```bash
python src/processing/parse_pdf.py
```

This saves the extracted text to `data/processed/tfl_report_text.txt`.

### Step 3 — Generate the knowledge graph

```bash
# Map GTFS CSVs to RDF triples (~443k triples)
python src/kg/map_gtfs.py

# Map TfL JSON to RDF triples (~2.3k triples)
python src/kg/map_tfl_json.py
```

Output Turtle files are saved to `data/kg/`.

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
│   │   └── map_tfl_json.py     # TfL JSON → RDF mapping
│   └── llm/                    # LLM extraction pipeline (in progress)
├── data/
│   ├── raw/                    # Source data (GTFS, tfl.json, PDF)
│   ├── processed/              # Extracted PDF text
│   └── kg/                     # Generated .ttl files
├── docs/
│   └── ke_prompts_log.md       # Prompt log for data sourcing
└── requirements.txt
```

## Key Files for Modelling Experts

- **`src/kg/ontology.py`** — The draft ontology. Defines all classes (BusStop, TrainStation, TransportLine, etc.) and properties (operatedBy, hasStop, etc.). Extends GTFS ontology and Schema.org with subclasses and subproperties. Review and refine this.
- **`data/kg/gtfs_kg.ttl`** — Generated KG from GTFS data (stops, routes, agencies, trips, stop times)
- **`data/kg/tfl_lines_kg.ttl`** — Generated KG from TfL API data (transport lines)

## Data Sources

| Source | Type | Format | Description |
|--------|------|--------|-------------|
| London GTFS feed | Structured | CSV | 24,865 stops, 1,102 routes, 475k trips, 17.9M stop times |
| TfL API | Structured | JSON | 727 transport lines across all modes |
| TfL Annual Report 2024/25 | Unstructured | PDF | Official report for LLM-based extraction |

## Dependencies

- `rdflib` — RDF graph library for building and querying the KG
- `requests` — HTTP requests for TfL API
- `pdfplumber` — PDF text extraction
