# Seattle Transit Equity Index — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working, deployed "Transit Equity Index" demo for Seattle plus a submission deck by 2026-11-11.

**Architecture:** One-time ETL + analysis pipeline (scripts/) produces small prepared datasets (data/prepared); a Streamlit app (app/) serves them; hosted free-tier on Hugging Face Spaces (fallback Streamlit Cloud). No ML model serving, no mock data.

**Tech Stack:** Python 3.11+, pandas, geopandas, shapely, numpy, networkx, requests, overpy (Overpass), partridge (GTFS parse), pyarrow, Streamlit, folium/pydeck, plotly, pytest, python-pptx (deck). Dependency mgmt via `uv` or pip + `requirements.txt`.

**Spec:** `docs/superpowers/specs/2026-11-06-seattle-transit-equity-design.md`

## Global Constraints

- Real data only — no synthetic/mock values anywhere (per user).
- Free tier only: no paid services, no API keys required (Census bulk CSVs if no key).
- Deadline Nov 11 2026 04:00 GMT+6; plan must leave ≥1 day buffer.
- App must run from prepared files only (no heavy compute at runtime).
- English UI/deck. Default scenario: weekday AM peak.
- Commits after each green test cycle.

## Review Focus

1. **GTFS feed quirks** — a feed that fails to parse must fail loudly with a clear message, not silently produce an empty network.
2. **Missing census cells** — a block group missing a field must be flagged and handled (skip or impute-neighbor), never crash or silently zero.
3. **Zero-opportunity categories** — a category with zero POIs must not produce division-by-zero; score should be "no data / 0 access" with a visible note.
4. **Prepared-file schema drift** — the app must fail with a precise message if a prepared file is missing or has wrong columns, not throw a cryptic KeyError.
5. **Deploy portability** — the app must start with `streamlit run app/main.py` in a clean environment (requirements pinned).

---

## Phase 0 — Foundation & Skeleton

### Task 0.1: Repo scaffold + env + smoke tests

**Files:**
- Create: `requirements.txt`, `pyproject.toml` (or `uv` config), `Makefile`, `.gitignore`, `README.md` (skeleton), `app/main.py` (placeholder), `tests/test_smoke.py`
- Modify: n/a

**Interfaces:**
- Produces: `make setup`, `make test`, `make app` targets; `hello_world()` placeholder.

- [ ] **Step 1: Write smoke test** (`tests/test_smoke.py`) asserting `datanova.version` exists and `app.main` imports.
- [ ] **Step 2: Run test → expect FAIL** (`pytest -q`).
- [ ] **Step 3: Create `datanova/__init__.py` with `__version__` and minimal `app/main.py` stub that renders a Streamlit title.**
- [ ] **Step 4: Run tests → expect PASS; run `streamlit run app/main.py` → page loads.**
- [ ] **Step 5: Commit.**

### Task 0.2: App skeleton with real Seattle base map

**Files:**
- Create: `app/views/map_view.py`, `tests/test_map_view.py`, `scripts/fetch_geometry.py`, `data/prepared/seattle_boundary.geojson`
- Modify: `app/main.py` to render map shell with layer switcher placeholder (no computed layers yet).

**Interfaces:**
- Consumes: `seattle_boundary.geojson`.
- Produces: `fetch_geometry()` → writes boundary GeoJSON.

- [ ] **Step 1: Write `scripts/fetch_geometry.py`** that downloads King County/Seattle TIGER boundary (real) → `data/prepared/seattle_boundary.geojson`.
- [ ] **Step 2: Test**: file exists, is valid GeoJSON, contains Seattle polygon(s).
- [ ] **Step 3: App renders a folium/pydeck map** centered on Seattle with the boundary layer.
- [ ] **Step 4: Verification** — launch app, confirm map renders offline (local tiles fallback).
- [ ] **Step 5: Commit.**

---

## Phase 1 — Data ETL (real data)

### Task 1.1: GTFS download + validate + parse

**Files:**
- Create: `scripts/fetch_gtfs.py`, `scripts/parse_gtfs.py`, `tests/test_gtfs.py`
- Output: `data/raw/kc_metro_gtfs.zip`, `data/raw/sound_transit_gtfs.zip`, `data/prepared/gtfs/{stops,routes,stop_times,calendar}.parquet`

**Interfaces:**
- Produces: `parse_gtfs(zip_path) -> dict[str, pl.DataFrame]`; schema constants `STOPS_COLS`, etc.

- [ ] **Step 1: Write failing tests** — downloader writes a zip; parser returns DataFrames with required columns; stop count > 0; at least 100 routes for the 2 feeds.
- [ ] **Step 2: Implement `fetch_gtfs()`** — download KC Metro + Sound Transit GTFS from official URLs to `data/raw`.
- [ ] **Step 3: Implement `parse_gtfs()`** — use `partridge` or manual CSV read; output parquet.
- [ ] **Step 4: Run tests → PASS.**
- [ ] **Step 5: Commit.**

### Task 1.2: Census block groups + ACS demographics

**Files:**
- Create: `scripts/fetch_census.py`, `tests/test_census.py`
- Output: `data/prepared/census/block_groups.geojson`, `acs_demographics.parquet`

**Interfaces:**
- Produces: `fetch_acs()` returning GeoDataFrame with columns: `geoid, geometry, median_income, zero_car_pct, poverty_pct, minority_pct, elderly_pct, disability_pct, pop_total`.

- [ ] **Step 1: Write failing tests** — geometry count > 0; required columns exist; `pop_total` sum within 10% of Seattle ACS total.
- [ ] **Step 2: Implement `fetch_acs()`** — bulk CSV extract (or API if key present) + TIGER block-group shapes.
- [ ] **Step 3: Run tests → PASS.**
- [ ] **Step 4: Commit.**

### Task 1.3: Opportunity POIs (jobs, healthcare, schools, food)

**Files:**
- Create: `scripts/fetch_opportunities.py`, `tests/test_opportunities.py`
- Output: `data/prepared/opportunities/{jobs,healthcare,schools,food}.geojson`

**Interfaces:**
- Produces: `fetch_opportunities()` → per-category GeoDataFrames with `category, name, weight` (jobs weighted by LODES).

- [ ] **Step 1: Write failing tests** — each category non-empty; jobs weighted sum > 0; geometries in Seattle bounding box.
- [ ] **Step 2: Implement** — LODES (WA) jobs points + Overpass queries for hospitals/clinics, schools, grocery/supermarkets/food banks.
- [ ] **Step 3: Run tests → PASS.**
- [ ] **Step 4: Commit.**

---

## Phase 2 — Analysis Engine

### Task 2.1: Transit network + router

**Files:**
- Create: `datanova/network.py`, `tests/test_network.py`
- Consumes: `data/prepared/gtfs/*.parquet`.

**Interfaces:**
- Produces: `build_network(gtfs) -> Network`; `travel_time(net, origin_xy, dest_xy, depart_time) -> float|None`; `walk_time(origin_xy, stop_xy)`.

- [ ] **Step 1: Write failing tests** — known origin→destination pair returns finite time; direct stop pair within 5% of GTFS stop_times; None when unreachable.
- [ ] **Step 2: Implement `build_network`** — graph of stops + walking edges + transfer edges from a representative weekday AM-peak schedule.
- [ ] **Step 3: Implement `travel_time`** — walking catchment to/from stops + shortest-path over graph (label-correcting / Dijkstra with headways).
- [ ] **Step 4: Run tests → PASS.**
- [ ] **Step 5: Commit.**

### Task 2.2: Accessibility scores per block group

**Files:**
- Create: `datanova/accessibility.py`, `tests/test_accessibility.py`
- Consumes: network, block groups, opportunities.

**Interfaces:**
- Produces: `compute_access_scores(bgs, opps, net) -> pd.DataFrame` (cols: `geoid, jobs_access, healthcare_access, schools_access, food_access`).

- [ ] **Step 1: Write failing tests** — scores in [0,1]; high-access fixture > low-access fixture; zero-opportunity category handled (no NaN).
- [ ] **Step 2: Implement** — thresholded travel times (jobs 45 / health 30 / food 20 / schools 30 min) → normalized access.
- [ ] **Step 3: Run tests → PASS.**
- [ ] **Step 4: Commit.**

### Task 2.3: Need Index

**Files:**
- Create: `datanova/need.py`, `tests/test_need.py`
- Consumes: ACS demographics.

**Interfaces:**
- Produces: `compute_need_index(acs) -> pd.DataFrame` (cols: `geoid, need_index`).

- [ ] **Step 1: Write failing tests** — bounds [0,1]; direction (higher poverty/zero-car → higher need); deterministic.
- [ ] **Step 2: Implement** — normalized composite of poverty, zero-car, minority, elderly, disability shares.
- [ ] **Step 3: Run tests → PASS.**
- [ ] **Step 4: Commit.**

### Task 2.4: Gap score, grades, recommendations, validation

**Files:**
- Create: `datanova/equity.py`, `datanova/recommend.py`, `scripts/run_analysis.py`, `tests/test_equity.py`
- Output: `data/prepared/equity/equity_scores.parquet`, `report_cards.json`, `recommendations.geojson`, `sensitivity/*.parquet`

**Interfaces:**
- Produces: `compute_equity(access, need)` → `equity_score, grade` per geoid; `recommend(equity, net, opps)` → list of recommendation dicts with `route_id, corridor, action, affected_pop`.

- [ ] **Step 1: Write failing tests** — grade derivation matches quartile spec; recommendation list non-empty for high-need fixtures; `affected_pop` sums reconcile with census.
- [ ] **Step 2: Implement scoring/grading** — equity = access − need; bins → A–F.
- [ ] **Step 3: Implement `recommend()`** — rule-based on gap + corridor frequency; attach affected population.
- [ ] **Step 4: Implement validation script** — compare sample travel times to known commute benchmarks; log checks; produce `validation_report.md`.
- [ ] **Step 5: Run full pipeline `python scripts/run_analysis.py` → all prepared files written.**
- [ ] **Step 6: Run tests → PASS.**
- [ ] **Step 7: Commit.**

---

## Phase 3 — App Features (skeleton-first, then pieces)

### Task 3.1: App loads prepared data + map layers

**Files:**
- Modify: `app/main.py`, `app/views/map_view.py`; Create: `app/data_io.py`, `tests/test_data_io.py`

**Interfaces:**
- Produces: `load_prepared()` → typed dict of DataFrames/GeoJSON; raises `PreparedDataError` with precise message on missing/wrong schema.

- [ ] **Step 1: Write failing tests** — `load_prepared()` works on real prepared files; missing-file case raises `PreparedDataError` with clear message.
- [ ] **Step 2: Implement `load_prepared()`.**
- [ ] **Step 3: App renders three layers** (Need, Access, Gap) with a working layer switcher and legend.
- [ ] **Step 4: Run tests + launch app → layers visible.**
- [ ] **Step 5: Commit.**

### Task 3.2: Neighborhood drilldown + Report Card

**Files:**
- Create: `app/views/report_card.py`, `tests/test_report_card.py`

- [ ] **Step 1: Write failing tests** — report-card data renders for a selected geoid; grades show; missing geoid handled gracefully.
- [ ] **Step 2: Implement side panel** — selected neighborhood stats, letter grades, top recommendations with affected-pop estimates.
- [ ] **Step 3: App integration** — click map → panel updates.
- [ ] **Step 4: Run tests + manual click-through.**
- [ ] **Step 5: Commit.**

### Task 3.3: What-if frequency explorer

**Files:**
- Create: `app/views/whatif.py`, `tests/test_whatif.py`; precompute `sensitivity/*` in Task 2.4.

- [ ] **Step 1: Write failing tests** — slider changes affected-pop display; precomputed sensitivity lookup keyed by route_id.
- [ ] **Step 2: Implement UI** — select recommended corridor → slider (frequency multiplier) → updated map highlight + population number.
- [ ] **Step 3: Run tests → PASS.**
- [ ] **Step 4: Commit.**

### Task 3.4: Export + visual polish

**Files:**
- Create: `app/views/export.py`; Modify: styling (CSS/theme), README demo section.

- [ ] **Step 1: Tests** — export produces a downloadable summary (CSV/PDF text) from current view.
- [ ] **Step 2: Implement export + apply visual system** (civic/data-forward: clean typography, consistent choropleth palette, accessibility contrast).
- [ ] **Step 3: Verification** — full app walkthrough, no console errors; mobile graceful degradation check.
- [ ] **Step 4: Commit.**

### Task 3.5: Deploy (free tier)

**Files:**
- Create: `README.md` deploy section, `app/requirements.txt` (pinned), `.streamlit/config.toml`, space config (`README` + `app` dir for HF Spaces).

- [ ] **Step 1: Prepare repo** — ensure prepared files are committed or fetched by a build step (small enough for HF free tier).
- [ ] **Step 2: Deploy to Hugging Face Spaces** (Streamlit SDK) via git push; verify app URL loads.
- [ ] **Step 3: Health check** — layers, drilldown, what-if all functional on deployed URL.
- [ ] **Step 4: Commit + record demo URL in README.**

---

## Phase 4 — Submission

### Task 4.1: Deck (PPT)

**Files:**
- Create: `scripts/build_deck.py`, `output/DataNova_Submission.pptx` (via python-pptx).

- [ ] **Step 1: Write deck builder** with sections: Hook → Problem → Data → Methodology → Results (map screenshots + grades) → Recommendations → Impact → Demo + how-to → Team/credits.
- [ ] **Step 2: Generate PPT; visually verify slides** (export thumbnails).
- [ ] **Step 3: Commit.**

### Task 4.2: Final QA + submission package

**Files:**
- Modify: `README.md` (run instructions, methodology, validation report link), final checklist.

- [ ] **Step 1: Full verification** — `make test` green; demo URL live; all links work.
- [ ] **Step 2: (Optional) 90s screen-record video** walkthrough.
- [ ] **Step 3: Submit on Devpost before deadline** — include title, overview, problem, solution/methodology, demo link, impact/validation, team contributions.

---

## Execution Handoff

- **Recommended:** Subagent-driven execution (tasks have clean interfaces; independent reviews help correctness of data-heavy pipeline). Alternatively Native execution in this session.
- Human gate after Phase 1 (confirm real data looks sane) and before Task 4.1 (deck content sign-off).
