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
