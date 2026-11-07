# Features

Status legend: DONE · IN PROGRESS · PLANNED · DEFERRED

## Phase 0 — Skeleton (DONE)
- App shell renders the real Seattle boundary (Census TIGER).

## Phase 1 — Data ETL (all DONE)
- **1.1 GTFS ETL** — real King County Metro + Sound Transit feeds, parsed to parquet.
- **1.2 Census ETL** — real TIGER block groups + ACS demographics (bulk Summary File fallback).
- **1.3 Opportunities ETL** — real LODES jobs + OSM healthcare/schools/food POIs.

## Phase 2 — Analysis (all DONE)
- **2.1 Transit network + router** — real GTFS graph, Dijkstra-based access.
- **2.2 Accessibility scores** — batched router with pruned-path parity.
- **2.3 Need index** — real ACS composite, normalized 0–1.
- **2.4 Equity scores / recommendations / sensitivity** — gap model, report cards,
  corridor recommendations, sensitivity table.

## Phase 3 — App (all DONE)
- **3.1 App data loader + real equity map layers** (Need / Access / Equity Gap toggles).
- **3.2 Neighborhood drilldown + Equity Report Card** (stats + recommendations).
- **3.3 What-if frequency explorer** (slider on recommended corridors).
- **3.4 Export view + visual polish**.
- *(Original Phase 3 was built as a Streamlit app; it is now retired/fallback.
  All four features are carried over into the current TypeScript SPA in `web/`,
  with the sketch-style polish, wow moments, and time-of-day scenario added on
  top — see `decisions.md` + `progress.md`.)*

## Phase 4 — Submission (NEXT)
- **4.1 Submission deck** (PPT) — planned next.
- **4.2 Final QA** — planned.
- **3.5 Deploy** — DEFERRED by user (local hosting for now; HF Spaces / Streamlit Cloud later).

## Stretch (not committed)
- Health / food / jobs access story overlay.
- Time-of-day scenario toggle.
- Short video walkthrough (optional deliverable).
