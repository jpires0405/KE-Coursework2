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
