# Completion — Task 001: FastAPI service (backend for the new web app)

**Agent:** Wizard (backend)
**Task:** `agents/wizard/tasks/fastapi-service-001.md`
**Status:** DONE
**Date:** 2026-11-07

---

## What I changed

| File | Change |
| --- | --- |
| `api/__init__.py` (new) | Package marker. |
| `api/data.py` (new) | Wraps `app.data_io.load_prepared` (the sanctioned loader) and loads the prepared data exactly once at import time. Also defines `WEB_DIST` (`web/dist`). |
| `api/serialization.py` (new) | JSON-safe serialization helpers: `clean_value` (numpy→native, NaN/inf→null, ACS suppressed-income sentinel `-666,666,666`→null), `geometry_to_geojson`, `gdf_to_featurecollection`, `frame_to_records`. No Streamlit imports — the API survives the Streamlit app's retirement. |
| `api/endpoints.py` (new) | All `/api/*` endpoints. Includes local mirrors of `app/views/export.py`'s top-underserved ranking and `app/views/report_card.py`'s block-group lookup (not imported from the retiring Streamlit views). |
| `api/main.py` (new) | App factory + module-level `app` for `uvicorn api.main:app`. CORS for the Vite dev origins, `/api` router first, then static SPA serving (with `index.html` fallback) when `web/dist` exists, else a clean HTML fallback page. |
| `tests/test_api.py` (new) | 18 tests against the real prepared data via FastAPI `TestClient`. |
| `requirements.txt` | Added `fastapi>=0.115`, `uvicorn>=0.32` (API), `httpx>=0.27` (dev/test; required by TestClient). |

No edits to `web/`, `app/`, `scripts/`, `datanova/`, or `data/`. Existing tests untouched. No git run.

## Endpoints

| Endpoint | Returns |
| --- | --- |
| `GET /api/health` | `{"status":"ok"}` |
| `GET /api/boundary` | Seattle boundary as GeoJSON FeatureCollection (1 feature, EPSG:4326) |
| `GET /api/equity` | equity_scores as GeoJSON FeatureCollection (1,545 features, ACS demographics joined via `load_prepared`) |
| `GET /api/recommendations` | recommendations as GeoJSON FeatureCollection (14 features; 13 LineString + 1 Point) |
| `GET /api/sensitivity` | Plain JSON records (14 rows; `geoids` lists; no geometry) |
| `GET /api/report-cards` | Root object of `report_cards.json` (`generated_at`, `summary`, per-BG `report_cards`) |
| `GET /api/top-underserved?n=25` | Top-N underserved block groups as plain records (no geometry), ranked `need_index` desc → `gap` asc → grade F-first. Optional `n` validated `1..5000` (invalid → 422) |
| `GET /api/block-group/{geoid}` | One block group's full equity row (all columns incl. ACS stats) as a single GeoJSON feature; `404` JSON for unknown geoid |
| `GET /api/metadata` | Small footer object: `app`, `generated_at`, `summary`, `data_counts`, `methodology_note` |

## Data loading / caching

- **One load at import time** (`api.data.PREPARED = load_prepared()`), shared by every endpoint — no per-request reads, no re-parsing of raw files. Matches the task's preferred option.
- **Trade-off (reported honestly):** the loaded GeoDataFrames stay resident in memory for the process lifetime. The equity GeoDataFrame is ~6 MB on disk; trivial for a local demo server. If `load_prepared` fails (missing/corrupt file), the app fails fast at boot (import error) with the loader's precise `PreparedDataError` message rather than on first request.

## Serialization semantics

- All data stays EPSG:4326 (GeoJSON-native; verified CRS on load).
- **ACS suppressed-income sentinel** (`-666,666,666`, present in 51 rows of `median_income`): serialized as `null`, per `context/decisions.md` ("treated as missing"). This was the only intentional value normalization; everything else is raw real data. The legacy Streamlit app displays the sentinel literally — this endpoint surfaces its documented missing semantics instead.
- NaN/inf and pandas missing values → `null`; `geoids`/list columns → JSON arrays. GeoJSON payloads are guaranteed valid JSON (no `NaN` literals) — enforced by a recursive test.

## Static serving

- **When `web/dist` exists:** mounted at `/` with `html=True` and an SPA fallback (`SPAStaticFiles` serves `index.html` for unknown non-file paths, so client-side routes work). The `/api` router is registered first, so API routes always win under the `/` mount.
- **When absent (current state):** `/` and any non-API path return a clean HTML fallback page ("API is live", links to `/api/health` and `/docs`); unmatched `/api/*` paths return JSON 404. The SPA-serving branch is exercised deterministically in tests via a temporary `dist` (never touching `web/`), so it is verified regardless of Picasso's parallel progress.
- **Robustness note:** Starlette 1.10 signals missing static files by *raising* `starlette.exceptions.HTTPException` (not returning a 404 response, and not `fastapi.HTTPException`, which is a subclass). The fallback handles both raising and response-return behavior.

## CORS

- Allows `http://localhost:5173` and `http://127.0.0.1:5173` (Vite dev server), methods `GET`/`OPTIONS`, `max_age=600`. Verified by a preflight test.

## Tests

- `tests/test_api.py`: **18 passed** (health, every endpoint's shape/counts against real data, top-N ordering & `n` validation, known/unknown block group, sentinel→null, metadata, CORS preflight, fallback page, and the temp-dist SPA-serving proof). 1 test skipped on the real `web/dist` branch (correct — it doesn't exist yet; the temp-dist test covers that logic).
- `tests/test_smoke.py`: **3 passed** (unchanged).
- Combined run: **21 passed, 1 skipped**.
- `pip check`: no broken requirements.
- Boot verified: `uvicorn api.main:app` starts and shuts down cleanly (no import errors).

## Notes for the frontend agent (Picasso)

- Everything is read-only JSON; all geometry is EPSG:4326 lon/lat.
- `GET /api/equity` is the full map layer (1,545 features; ~6 MB). `GET /api/top-underserved` and `GET /api/sensitivity` are plain records — no geometry.
- Block-group keys are **strings** (`geoid`); the report-card page key in `/api/report-cards` matches those geoids.
- `median_income` may be `null` (suppressed census data) — format as "n/a" rather than a number.
- `recommendations` features carry `geoids` (array of strings) per feature; `sensitivity` records also carry `geoids`.
- `GET /api/metadata` is the footer endpoint (`generated_at`, `summary`, counts, methodology note).

## Notes for the main agent

- I did not run git; commit after review.
- Optional follow-ups (not done — out of scope): `httpx` vs the newer `httpx2` deprecation warning emitted by Starlette's TestClient import (cosmetic; tests pass). No other blocking items.
