# Knowledge Engineering Prompts & Queries Log

This document records the specific queries, prompts, and search strategies used for Knowledge Engineering tasks, as required by the coursework specification. General coding or setup tasks are not logged here.

---

## KE Task 1 — Data Source Identification (Structured)

**Task:** Find a static GTFS dataset for a major city with public transportation data suitable for knowledge graph construction.

**Date:** 2026-03-21

**Search queries used:**
1. `"static GTFS feed" London download open data`
2. `TfL GTFS open data developer portal site:tfl.gov.uk`
3. `UK bus open data GTFS London government download`

**Outcome:**
- **Selected source:** UK Department for Transport — Bus Open Data Service (BODS)
- **Dataset:** London Static GTFS Feed
- **URL:** `https://data.bus-data.dft.gov.uk/timetable/download/gtfs-file/london/`
- **Format:** ZIP (GTFS — General Transit Feed Specification), structured CSV files
- **Rationale:** Official government-maintained dataset covering London bus routes, stops, trips, and schedules. Freely available without API key. Directly suitable for constructing KG instances for routes, stops, and services.
- **Download script:** `data/raw/download_gtfs.py`

---

## KE Task 2 — Data Source Identification (Unstructured Text)

**Task:** Find a recent official report or document (PDF) providing unstructured textual information about public transport developments in London, suitable for LLM-based information extraction.

**Date:** 2026-03-21

**Search queries used:**
1. `TfL annual report 2024 PDF site:tfl.gov.uk`
2. `"Transport for London" annual report statement accounts 2024 filetype:pdf`
3. `TfL publications reports site:content.tfl.gov.uk`

**Outcome:**
- **Selected source:** Transport for London (TfL)
- **Document:** TfL Annual Report and Statement of Accounts 2024/25
- **URL:** `https://content.tfl.gov.uk/tfl-annual-report-and-statement-of-accounts-2024-25.pdf`
- **Format:** PDF (unstructured text — ~25.9 MB)
- **Rationale:** Authoritative official document covering TfL's operational performance, infrastructure developments, service improvements, and strategic plans across all transport modes (Tube, Bus, Elizabeth line, DLR, etc.). Rich source for extracting entities (lines, stations, projects) and relationships for the KG via LLM-based extraction.
- **Download script:** `data/raw/download_tfl_report.py`

---

## KE Task 3 — RAG-Based TBox Completion (Ontology Gap Resolution)

**Task:** Identify TBox gaps in the London Transport ontology and use a RAG pipeline to generate the missing OWL/RDF classes and properties in valid Turtle syntax.

**Date:** 2026-04-05

**Script:** `src/kg/rag_ontology_completion.py`
**Model:** Groq — `llama3-70b-8192`
**Output:** `data/kg/ontology_extensions_rag.ttl`

---

### RAG Strategy

**Retrieval source:** The full source code of `src/kg/ontology.py` is read at runtime and injected verbatim into the LLM prompt as context. This grounds the LLM in the exact namespace (`lt:`), class hierarchy, and existing properties, preventing hallucinated URIs or redundant declarations.

**Why RAG over a plain prompt?** A plain prompt describing the ontology abstractly risks the LLM generating classes or properties that conflict with or duplicate what already exists. Feeding the actual source forces the LLM to extend the graph consistently (correct parent classes, matching namespace, correct subPropertyOf chains).

---

### Identified TBox Gaps

1. No `lt:FareZone` class
2. `lt:hasRoute` exists but has no `rdfs:domain`/`rdfs:range` and is unused
3. No `lt:Borough` class
4. Accessibility is only a boolean (`lt:wheelchairAccessible`) — no structured class
5. No `lt:Interchange` class for multimodal stations
6. No `lt:modeOfTransport` property
7. No `lt:Fare` / `lt:FareTier` pricing class
8. No `lt:lineColour` datatype property

---

### System Prompt

```
You are an expert Knowledge Graph Engineer specialising in public transport ontologies.
You write precise, valid OWL/RDF in Turtle syntax using established ontology engineering principles.
You always declare new classes as owl:Class with rdfs:label and rdfs:comment.
You always declare new properties as owl:ObjectProperty or owl:DatatypeProperty with
rdfs:label, rdfs:comment, rdfs:domain, and rdfs:range.
You use subClassOf and subPropertyOf to integrate new elements into the existing hierarchy.
You output ONLY a single fenced Turtle code block — no prose before or after.
```

### User Prompt (template — ontology source injected at `{ontology_source}`)

```
## Existing Ontology (Retrieval Context)

The following is the complete source of our current London Transport ontology, defined in Python using rdflib.
Read it carefully — all new elements must integrate with the existing namespace, class hierarchy, and property set.

```python
{ontology_source}
```

---

## Task

The ontology above has the following 8 identified TBox gaps that must be resolved:

1. No lt:FareZone class — the KG cannot represent which fare zone a stop belongs to.
2. lt:hasRoute exists but has no domain/range constraints and is unused in instances.
3. No lt:Borough class — the KG cannot link stops or lines to London boroughs.
4. Accessibility is only a boolean (lt:wheelchairAccessible) — no structured lt:AccessibilityFeature class for richer descriptions.
5. No lt:Interchange class — multimodal interchange stations cannot be typed distinctly.
6. No lt:modeOfTransport property — no way to state which transport mode a route or line uses.
7. No lt:Fare or lt:FareTier class — the KG cannot represent fare/pricing information.
8. No lt:lineColour datatype property — TfL lines have official colours that are not captured.

---

## Instructions

Generate valid OWL/RDF Turtle that resolves all 8 gaps. Your output must:

1. Use the namespace prefix `lt: <http://example.org/london-transport#>` (already declared — do not redeclare it).
2. Also use @prefix owl, rdfs, xsd.
3. For each new class: declare rdf:type owl:Class, rdfs:subClassOf (correct parent from existing hierarchy), rdfs:label, rdfs:comment.
4. For each new property: declare rdf:type owl:ObjectProperty or owl:DatatypeProperty, rdfs:subPropertyOf where applicable, rdfs:domain, rdfs:range, rdfs:label, rdfs:comment.
5. For gap 2 (lt:hasRoute unused): add the missing rdfs:domain and rdfs:range constraints.
6. Output ONLY a single ```turtle ... ``` fenced code block. No explanations outside the block.
```

---

### Justification

The RAG approach here directly satisfies the KG completion requirement: rather than manually authoring the missing triples, the LLM is given authoritative context (the ontology source) and asked to reason about the gaps. This is documented as an LLM-assisted completion step with traceable inputs (the ontology file) and a deterministic low-temperature setting (0.1) to ensure reproducible output.

---

## KE Task 4 — RAG-Based ABox Instance Population (Gap Resolution)

**Task:** The previous RAG step added 8 new TBox classes/properties but no ABox instances. This step uses RAG to generate instance triples that populate `lt:FareZone`, `lt:Borough`, `lt:Interchange`, `lt:lineColour`, and `lt:modeOfTransport` for real London transport data.

**Date:** 2026-04-08

**Script:** `src/kg/rag_populate_instances.py`
**Model:** Groq — `llama-3.3-70b-versatile`
**Output:** `data/kg/rag_instances.ttl` (215 triples) merged into `data/kg/final_submission_kg.ttl` (673,971 total)

---

### RAG Strategy

**Retrieval:** Named transport lines and 40 major station URIs + labels are extracted programmatically from `final_submission_kg.ttl` at runtime using rdflib. This gives the LLM exact URI references that match the KG rather than hallucinated identifiers.

**Why RAG here:** Without the actual URIs from the KG (e.g. `lt:stop_940GZZLUKSX` for King's Cross), the LLM would invent URIs that cannot be linked to existing instances. By extracting and injecting them, the generated triples integrate directly with the existing ABox.

---

### System Prompt

```
You are an expert Knowledge Graph Engineer for the London Transport domain.
You write ABox instance triples in strictly valid Turtle syntax.
You use only URIs and properties already declared in the ontology.
You never invent new classes or properties — only new instances and literal values.
You output ONLY a single fenced ```turtle ... ``` code block with no prose outside it.
```

### User Prompt (condensed — full URIs injected at runtime)

```
## Ontology Namespace
All URIs use: @prefix lt: <http://example.org/london-transport#> .
New classes/properties from previous RAG step: lt:FareZone, lt:Borough, lt:Interchange,
lt:Fare, lt:FareTier, lt:modeOfTransport (ObjectProperty), lt:lineColour (DatatypeProperty),
lt:inFareZone (ObjectProperty), lt:locatedIn (ObjectProperty).

## Existing KG Entities (extracted programmatically)
[24 named transport lines with class and label]
[40 major station URIs with labels]

## Task — Generate ABox Instance Triples

1. Line Colours and Modes: For every named line, add lt:lineColour (official TfL hex)
   and lt:modeOfTransport pointing to a new lt:mode_* instance (lt:TransportEntity).

2. Fare Zones: Create lt:fare_zone_1 through lt:fare_zone_6 as lt:FareZone instances.
   Link each sampled station to its correct zone via lt:inFareZone.

3. Boroughs: Create lt:Borough instances for 15 London boroughs.
   Link each sampled station to its correct borough via lt:locatedIn.

4. Interchange: Add rdf:type lt:Interchange for 11 confirmed multi-modal interchange stations.

Output ONLY one ```turtle ... ``` block. Do NOT redeclare existing classes or properties.
```

---

### Results

- **215 new triples** generated and validated with rdflib
- All 24 named lines have `lt:lineColour` and `lt:modeOfTransport`
- 6 fare zone instances created; 40 stations linked to correct zones
- 15 borough instances created; 40 stations linked to correct boroughs
- 11 major interchange stations typed as `lt:Interchange`

---

## KE Task 5 — RAG-Based ABox Relation Population (Network Connectivity)

**Task:** The canonical `lt:line_*` URIs had zero `lt:servesStation` links and `lt:intersectsWith` used string literals rather than URIs, making SPARQL queries return empty results. This step uses RAG to generate object-property relation triples that connect lines to stations and lines to each other.

**Date:** 2026-04-08

**Script:** `src/kg/rag_populate_relations.py`
**Model:** Groq — `llama-3.3-70b-versatile`
**Output:** `data/kg/rag_relations.ttl` (184 triples) merged into `data/kg/final_submission_kg.ttl` (674,113 total)

---

### RAG Strategy

**Retrieval:** The 20 canonical `lt:line_*` URIs (those with `lt:lineColour`) are extracted programmatically from the KG and injected into the prompt. This ensures the LLM generates triples using the exact URIs that exist in the graph rather than hallucinated identifiers.

**Why this matters:** `lt:intersectsWith` already existed in the KG with 61,372 triples, but all used string literals (e.g., `"Bakerloo"`) as objects — not URI references. These cannot be traversed by SPARQL. The RAG prompt explicitly requests URI-to-URI triples, producing graph-traversable relationships.

---

### System Prompt

```
You are an expert Knowledge Graph Engineer specialising in the London transport network.
You have authoritative knowledge of which stations each TfL line serves and which lines
intersect at which stations.
You write strictly valid Turtle using only the URIs provided — never invent new URIs.
You output ONLY a single fenced ```turtle ... ``` code block.
```

### User Prompt (condensed — full URIs injected at runtime)

```
## Namespace
@prefix lt: <http://example.org/london-transport#> .

## Relevant Object Properties (already declared)
- lt:servesStation   domain: lt:TransportLine,  range: lt:TrainStation
- lt:isServedBy      domain: lt:TrainStation,   range: lt:TransportLine
- lt:intersectsWith  domain: lt:TransportLine,  range: lt:TransportLine
- lt:connectsTo      domain: lt:Stop,           range: lt:Stop

## Canonical Transport Line URIs (from the KG)
[20 named lt:line_* URIs with labels]

## Major Station URIs (from the KG)
[40 major station URIs with rdfs:label]

## Task — Generate Relation Triples

1. lt:servesStation and lt:isServedBy:
   For each of the 11 Tube lines and Elizabeth line, generate at least 5 servesStation
   and corresponding isServedBy triples using only station URIs from the list above.

2. lt:intersectsWith (line-to-line, using URIs):
   For pairs of lines sharing stations in the list, generate symmetric intersectsWith
   triples using only canonical line URIs from the list above.

3. lt:connectsTo (station-to-station):
   For adjacent stations on the same line or major interchange points,
   generate at least 15 directional connectsTo pairs.

Output ONLY one ```turtle ... ``` block. Use ONLY URIs provided above.
```

---

### Results

- **184 new triples** — all valid and merged into the final KG
- All 11 Tube lines + Elizabeth line linked to 5+ stations via `lt:servesStation`/`lt:isServedBy`
- Symmetric `lt:intersectsWith` URI triples generated for all intersecting canonical line pairs
- 14 station-to-station `lt:connectsTo` pairs covering the central/eastern network

---

## KE Task 6 — LLM-Augmented Competency Question Generation (CQ11–CQ20)

**Task:** Generate 10 LLM-augmented Competency Questions that complement the 10 manually authored CQs, targeting deeper domain insights and cross-referencing GTFS structured data with TfL Annual Report text.

**Date:** 2026-04-06

**Script:** `src/llm/generate_augmented_cqs.py`
**Model:** Groq — `llama-3.3-70b-versatile`
**Output:** Appended CQ11–CQ20 to `docs/requirements.md`

---

### System Prompt

```
You are an expert Knowledge Engineer specialising in public transport ontologies and SPARQL-queryable Knowledge Graphs.
You have deep familiarity with the London transport network — including TfL's bus, Tube, Overground, DLR, Elizabeth line,
Tram, and River Bus services — and with the GTFS data standard (routes, stops, trips, stop_times, services, agencies).
Your task is to generate Competency Questions (CQs) that are precise, non-trivial, and directly answerable by a SPARQL query
over a Knowledge Graph built from two sources: (1) structured GTFS schedule data and (2) unstructured text from the TfL Annual Report 2024/25.
```

### User Prompt

```
## Context

We are building a London Transport Knowledge Graph (KG) that combines two data sources:
- Structured source: London GTFS feed (routes, stops, trips, stop_times, calendar, agencies)
- Unstructured source: TfL Annual Report 2024/25 (LLM-extracted entities: lines, stations, operators, ridership statistics, projects)

The ontology uses the `lt:` namespace with classes including:
lt:TransportOperator, lt:TransportLine (and subclasses: lt:TubeLine, lt:DLRLine, lt:OvergroundLine,
lt:ElizabethLine, lt:BusLine, lt:TramLine, lt:RiverBusLine), lt:Route, lt:BusRoute, lt:TrainRoute,
lt:Stop, lt:BusStop, lt:TrainStation, lt:Service, lt:Trip, lt:StopTime, lt:Place, lt:Report.

Key properties include: lt:operatedBy, lt:hasRoute, lt:hasStop, lt:onRoute, lt:belongsToService,
lt:stopsAt, lt:connectsTo, lt:servesStation, lt:mentionedInReport, lt:wheelchairAccessible,
lt:latitude, lt:longitude, lt:stopCode, lt:routeNumber, lt:startDate, lt:endDate,
lt:arrivalTime, lt:departureTime, lt:hasRidership, lt:hasFrequency, lt:lineColour.

## Already-authored Manual CQs (DO NOT repeat or closely paraphrase these)

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

## Task

Generate exactly 10 new Competency Questions (CQ11–CQ20) that:

1. Complement the manual CQs above — do not repeat or trivially rephrase them.
2. Target deeper domain insights — e.g. multi-hop queries, aggregations, comparisons across lines or operators.
3. At least 3 questions must require cross-referencing both data sources — combining GTFS schedule facts with entities
   or statistics mentioned in the TfL Annual Report (use lt:mentionedInReport or lt:hasRidership/lt:hasFrequency).
4. At least 2 questions must involve accessibility or interchange (lt:wheelchairAccessible, lt:Interchange,
   or multi-modal connections).
5. Questions must be answerable by SPARQL over the KG — avoid questions that require free-text reasoning.
6. Write each question as a clear, natural-language sentence ending with a question mark.

## Output Format

Return ONLY a numbered list of 10 questions in this exact format:
CQ11: <question text>
...
CQ20: <question text>
No preamble, no explanation, no commentary.
```

---

### Prompt Design Justification

**Why these constraints produce complementary CQs:**

The manual CQs (CQ1–CQ10) are deliberately basic — single-class lookups, single-property filters, and one identifier-resolution query (CQ8). They validate that the KG's core instances are correctly typed and labelled.

The LLM prompt is designed to force a different register of question by imposing three hard constraints:

1. **"Do not repeat or paraphrase"** — the LLM is shown all 10 manual CQs explicitly, preventing it from generating near-duplicates.
2. **"At least 3 cross-source questions"** — this directly targets the coursework requirement to demonstrate value from combining GTFS structured data with TfL Annual Report unstructured text. Questions requiring both `lt:mentionedInReport` and GTFS properties (e.g. frequency, ridership) can only be answered by a KG that integrates both pipelines — they cannot be answered by either source alone.
3. **"At least 2 accessibility/interchange questions"** — these probe the RAG-completed ontology extensions (`lt:Interchange`, `lt:AccessibilityFeature`) and verify that completion step added usable knowledge.

The temperature is set to 0.4 (higher than the ontology completion script) to encourage lexical diversity in the questions while keeping them factual and SPARQL-compatible.

### Generated CQs (CQ11–CQ20)

| ID | Question |
|----|----------|
| CQ11 | What are the most frequently served stations by bus routes operated by Transport for London? |
| CQ12 | Which bus routes have the highest frequency according to the TfL Annual Report? |
| CQ13 | Which transport operators have routes that are both mentioned in the report and have a frequency value? |
| CQ14 | Which bus routes have the highest frequency of service and are mentioned in the TfL Annual Report as having improved reliability? |
| CQ15 | List all bus stops that are not wheelchair accessible but share a name with an interchange station. |
| CQ16 | Which routes are mentioned in the TfL Annual Report and are operated by an operator that also operates a tube line? |
| CQ17 | Which bus services are active during the Easter weekend of 2026 (April 4–5, 2026)? |
| CQ18 | Which transport lines are currently experiencing disruptions, and what are the explicitly stated reasons for these disruptions? |
| CQ19 | What are the names of train stations that are interchanges (lt:Interchange) between at least three different transport lines, and which lines are they? |
| CQ20 | What are the names of all transport operators that operate bus routes, and how many distinct bus routes does each operator manage? |

---
