# Task 002 — Rebuild the frontend as a Vite + TypeScript + MapLibre GL SPA

## Context

The user has approved replacing the Streamlit frontend with a bespoke web app.
Stack (user-selected): **Vanilla TypeScript + Vite + MapLibre GL**, with a thin
FastAPI backend (built in parallel by the Wizard agent) serving the precomputed data.
You own the frontend half: everything under a new `web/` directory.

The four functional areas from the Streamlit app must carry over **behavior-identical**:
map layers, block-group drilldown report card, what-if frequency explorer, and export.

Read first: `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`,
`context/features.md`, this task, and the existing app views for reference
(`app/views/map_view.py`, `report_card.py`, `whatif.py`, `export.py`, and `app/styles.css`)
— you are porting their *behavior and data semantics*, not their code.

## The API (being built in parallel by Wizard — contract)

`GET /api/health` · `GET /api/boundary` (GeoJSON) · `GET /api/equity` (GeoJSON, ACS-joined)
· `GET /api/recommendations` (GeoJSON) · `GET /api/sensitivity` (JSON records)
· `GET /api/report-cards` (JSON) · `GET /api/top-underserved?n=25` (JSON records)
· `GET /api/block-group/{geoid}` (one row) · `GET /api/metadata` (JSON)

During development, run `vite` with a proxy: `/api` → `http://localhost:8000`
(the FastAPI port). In production the API serves `web/dist/` statically.

## Objective

Build a single-page app in `web/` (Vite + TypeScript, no UI framework) that replaces the
Streamlit app's four views:

1. **Map explorer** — full-bleed MapLibre GL map of Seattle. Layer toggle pills/segmented
   control for: **Need Index** (YlOrBr sequential), **Access** (Blues sequential),
   **Equity Gap** (RdBu diverging), **Grade A–F** (categorical palette). Boundary outline.
   Clicking a block group selects it (see drilldown).
2. **Drilldown panel** — slide-over/panel for the selected block group: identity, ACS stat
   tiles (population, poverty %, zero-car %, median income), grade chips (Jobs/Healthcare/
   Schools/Food/Overall), and top recommendations (corridor, action, affected population).
3. **What-if explorer** — corridor dropdown (ordered by affected pop), frequency-multiplier
   slider (1.0–3.0×, default 2.0), action callout, four metric tiles (affected residents,
   newly benefiting residents, est. wait saving, access improvement), and a map view
   highlighting the corridor + served block groups. Reuse the documented interpolation model
   from `app/views/whatif.py` (`wait_saving_min`, `what_if_projection` semantics — port it
   to TypeScript).
4. **Export** — city-wide top-N underserved table (with CSV download) and a per-block-group
   report-card snapshot download when one is selected.

## Design direction (preserve the established visual language)

- **Civic + data-forward.** Professional, readable, trustworthy. Not flashy/consumer.
- **Colorblind-safe, unchanged:** YlOrBr/Blues sequential; RdBu diverging for gap; the
  A–F grade palette from `app/views/_ui.py` (A #1a7f37, B #2d9d4f, C #e3b341,
  D #e0762a, F #c62828, unknown #6b7280).
- Typography, spacing, focus-visible, reduced-motion, and ≤720px responsive behavior should
  meet or exceed the quality bar set in the Task 001 refactor (`app/styles.css`).
- The map is the hero. It should feel fast and fluid (MapLibre WebGL).

## Scope

**IN:** `web/` (new): Vite project scaffold, TypeScript source, MapLibre GL integration,
styles, proxy config, and minimal README for running it. You may add small dev
dependencies (vite, typescript, maplibre-gl, vite proxy). **Do not add a UI framework.**

**OUT:** `api/` (backend agent), `app/` (legacy Streamlit — do not edit), `scripts/`,
`datanova/`, `data/` (read-only), git operations.

## Guidelines

1. Read the rulebook, context, and the existing app views first — you are porting behavior.
2. Run your skill router; classify `task_kind: build_new`, `design_direction: premium`
   (civic/data-forward), `target: web`, `stack: vanilla`. Load only matching skills.
3. **Contract-first:** implement against the API contract above. If the API is not ready
   yet, stub the data layer with a typed `api.ts` module so swapping to the real endpoints
   is a one-line change. Never fabricate demo numbers in the shipped app — if you need
   placeholder data for development only, keep it clearly marked and dev-only.
4. Type the API payloads (GeoJSON FeatureCollection shapes, sensitivity records, etc.).
5. Keep the SPA dependency-light and fast. Use MapLibre GL's GeoJSON sources; no framework.
6. Accessibility: keyboard-focusable controls, visible focus, semantic HTML, alt text.
7. Responsive: mobile ≤720px must remain usable (stacked panels, readable map).
8. Verification: build with `npm run build` (type-check + production build). Run the app
   against the API if available; otherwise verify against your typed stubs. Check the page
   renders, layers toggle, click-select works, and what-if/export render.
9. **You may NOT modify `app/`, `api/`, `scripts/`, `data/`, or anything outside `web/`.**
   You may add a `web/README.md` explaining how to run/build.

## Deliverables

- `web/` complete Vite + TS + MapLibre app (source, styles, config, README).
- Completion file: what you built, how it maps to the four Streamlit views, the design
  decisions, build/test verification results, and any API-contract notes/assumptions for
  the Wizard agent.

## Done when

- [ ] `npm run build` passes (type-check + production build) in `web/`.
- [ ] SPA renders: map loads, boundary + at least one analysis layer visible.
- [ ] Layer toggle switches Need/Access/Gap/Grade correctly.
- [ ] Clicking a block group opens the drilldown panel with stats, grades, recommendations.
- [ ] What-if explorer: corridor dropdown, slider, metrics, highlight map all function.
- [ ] Export view shows the top-N table and provides CSV download.
- [ ] No fabricated production data — data comes from the API/stubs only.
- [ ] Colorblind-safe palettes and grade colors preserved.
- [ ] Basic accessibility (focus, semantic HTML) and ≤720px responsive working.
- [ ] `web/README.md` documents run/build steps.
- [ ] No edits outside `web/`.
- [ ] Completion written to `agents/picasso/completions/rebuild-frontend-002.md` (Status honest).
