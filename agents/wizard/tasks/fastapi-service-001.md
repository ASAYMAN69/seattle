# Task 001 — FastAPI service (backend for the new web app)

## Context

The Streamlit app (`app/`) is being replaced by a proper web app. The user-approved stack:
**FastAPI (backend) + Vite/TypeScript/MapLibre GL (frontend)**. You own the backend half:
a thin FastAPI service that serves the precomputed prepared data and the built SPA.
The analysis is fully precomputed — **no live computation**, no routing, no ML.

A parallel frontend agent (Picasso) is building the SPA in `web/` against your API. Your
contracts must be stable: Picasso builds against the endpoints you define. Coordinate via
the task files only — do not modify `web/`.

Read first: `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`, and
`app/data_io.py` (the existing loader you should wrap, not reimplement).

## Objective

Build a FastAPI service in a new `api/` directory that:

1. Exposes read-only JSON endpoints over the prepared data (below).
2. Serves the built SPA static files (`web/dist/`) when present (production mode), with a
   clean fallback page when the SPA build is absent.
3. Adds tests under `tests/` covering every endpoint against the real prepared data.
4. Adds the FastAPI dependencies to `requirements.txt`.

## API contract (design to this; you may add response-model niceties)

| Endpoint | Returns |
| --- | --- |
| `GET /api/health` | `{"status":"ok"}` |
| `GET /api/boundary` | Seattle boundary as GeoJSON FeatureCollection |
| `GET /api/equity` | equity_scores as GeoJSON FeatureCollection (with ACS demographics joined — reuse `load_prepared`/`_join_acs` semantics) |
| `GET /api/recommendations` | recommendations as GeoJSON FeatureCollection |
| `GET /api/sensitivity` | sensitivity table as JSON (records array) |
| `GET /api/report-cards` | the `report_cards.json` root object |
| `GET /api/top-underserved?n=25` | top-N underserved block groups (ranked by need_index desc → gap asc → grade F-first; mirror `app/views/export.py` logic) |
| `GET /api/block-group/{geoid}` | one block group's full equity row (with ACS stats) or `404` |
| `GET /api/metadata` | small object: generated_at, summary from report_cards, data versions/notes useful for a footer |

Notes:
- Coordinate systems stay EPSG:4326 (GeoJSON-native).
- Keep payloads reasonably sized: the map needs full geometry; the top-underserved and
  sensitivity endpoints should return plain tabular records (no geometry) unless tiny.
- CORS: allow `http://localhost:5173` (Vite dev server) during development.
- Static serving: mount `web/dist` (if it exists) at `/` with `html=True` fallback to
  `index.html` (SPA routing).

## Scope

**IN:** `api/` (new), `requirements.txt` (add fastapi/uvicorn if not present),
`tests/test_api.py` (new), and any small helper module under `api/` for ranking/serialization.

**OUT:** `web/` (frontend agent), `app/` (legacy Streamlit — do not edit), `scripts/`,
`datanova/`, `data/` (read-only), git operations.

## Guidelines

1. Read the rulebook, project context, decisions, and `app/data_io.py` first.
2. Run your skill router; classify `work_type: api_design` (with the whole_service scope),
   load only matching skills.
3. Reuse `app/data_io.load_prepared` as the data source. Do not re-parse raw files.
4. Prefer loading prepared files once at startup (module-level) rather than per-request;
   report memory/loading trade-offs honestly (e.g. GeoDataFrames held in memory).
5. Keep endpoints read-only and dependency-light. No auth needed (public demo).
6. Write `tests/test_api.py` using FastAPI's TestClient against the REAL prepared data
   (they exist on disk). Assert shapes (feature counts, required keys), not fabricated values.
7. Do not run the full `make test` if it is slow — at minimum run
   `.venv/bin/python -m pytest tests/test_api.py -q` and the smoke test; report results.
8. Do not modify existing tests. Do not run git.

## Deliverables

- `api/` FastAPI app (modular: main app, endpoints, response/serialization helpers).
- `requirements.txt` updated (fastapi, uvicorn; keep versions permissive).
- `tests/test_api.py` (new).
- Completion file with: endpoint list, how data is loaded/cached, static-serving behavior,
  test results, and any contract notes for the frontend agent.

## Done when

- [ ] `api/` app boots under `uvicorn api.main:app` with no import errors.
- [ ] Every endpoint returns correct data against the real prepared files (tested).
- [ ] `tests/test_api.py` passes.
- [ ] `tests/test_smoke.py` still passes.
- [ ] Static serving of `web/dist` works when present; clean fallback otherwise.
- [ ] CORS configured for the Vite dev origin.
- [ ] No edits to `web/`, `app/`, `scripts/`, `datanova/`, or `data/`.
- [ ] Completion written to `agents/wizard/completions/fastapi-service-001.md` (Status honest).
