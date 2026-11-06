# Task 002 — Approximate time-of-day toggle (off-peak as a documented what-if)

## Context

The user's current version is committed. The user approved adding the six
stretch features from `CHECKLIST.md` §6. Five are frontend-only (Picasso's Task
005); this one — **time-of-day toggle** — is yours (Wizard, backend).

**Key constraint (user-approved, main-agent ruling):** the time-of-day toggle must
be an **approximation**, NOT a full recompute. The analysis currently assumes
weekday AM peak (the feeds lack trips.txt). We will model off-peak as a
documented what-if that applies the existing frequency model over off-peak
assumptions — labeled honestly, never presented as a fresh routed network.

Read first: `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`,
this task, and `app/data_io.py` / `app/views/whatif.py` (the documented
interpolation model).

## Objective

Add a time-of-day dimension to the API that a frontend can toggle between
**AM peak** (current, real) and **off-peak** (approximate, documented). The
endpoint sells the scenario honestly: AM peak returns the prepared equity
numbers; off-peak returns the same equity surfaces with a clearly-flagged
approximate model and methodology note.

## API contract (design this; keep it stable for the frontend)

| Endpoint | Returns |
| --- | --- |
| `GET /api/equity?time_of_day=am_peak` (default; also `off_peak`) | The equity FeatureCollection, plus a `properties.time_of_day` echo + `methodology_note` per feature (or a top-level `properties.methodology_note` on the collection) marking which scenario each feature represents and, for off-peak, the approximation basis. |
| `GET /api/top-underserved?n=25&time_of_day=am_peak` | Same as today for AM peak; for off-peak, the same ranking inputs with an `approximation_note` field. |
| `GET /api/block-group/{geoid}?time_of_day=am_peak` | Same row for AM peak; off-peak adds `approximation_applied: true` + note. |
| `GET /api/metadata` | Add `scenarios: { am_peak: {...}, off_peak: {...} }` describing each: is_full_compute, basis, approximations, narrative. |

Also consider a single helper endpoint:
`GET /api/scenarios` → returns both scenario descriptors (id, label, is_full_compute,
basis, notes). Frontend will call this to render the toggle.

## The off-peak approximation (document precisely what you do)

Apply a **transparent, documented** off-peak adjustment on top of the prepared AM-peak
numbers, using ONLY already-prepared fields (no new data ingestion, no routing):

1. Model an off-peak frequency multiplier (e.g. capped service pattern) and the
   resulting wait saving
   `min((headway/2) * (1 - 1/m), 3.5)` — reuse the what-if formula from
   `app/views/whatif.py` (`wait_saving_min` semantics). Document m.
2. Interpolate an access gain per block group proportionally to category access gaps
   (document the formula; it must reduce to the documented what-if at the reference).
3. Store the adjusted category access values in the feature properties for off-peak
   (so the map can choropleth them), and mark every off-peak feature with
   `approximation_applied: true` and a `methodology_note` naming the off-peak basis.
4. The ranking for top-underserved under off-peak uses the adjusted scores.

Every off-peak payload carries a **visible approximation banner data point** (not just a
footnote): `scenario_id`, `is_full_compute: false`, `basis`, `limitations` in the metadata
/ scenario descriptor, and rendered by the frontend as an explicit label.

## Scope

**IN:** `api/` (endpoints, time-of-day parameters, scenario helpers), `tests/test_api.py`
(extend with time-of-day tests), `requirements.txt` if needed (no new deps expected).

**OUT:** `web/` (frontend agent), `app/` (legacy — read only), `scripts/`, `datanova/`,
`data/` (read-only). **Do not parse raw GTFS or recompute a routed network.** No new
paid services. No git.

## Guidelines

1. Read rulebook, context, and the existing API + loader first.
2. Run your skill router; classify `work_type: api_design` (whole_service scope, low–medium risk).
3. Reuse `app.data_io.load_prepared` as the data source. Do not re-parse raw files.
4. Keep AM-peak responses **byte-identical** to today for the default (no regressions).
5. Validate `time_of_day` values (unknown → 422 with a clear message).
6. Write tests in `tests/test_api.py` covering:
   - Default (no param) returns AM peak and byte-equals today's shape.
   - `off_peak` returns adjusted access values within sane ranges (0–1, finite),
     is deterministically consistent (same params → same values).
   - Scenario/descriptor metadata present and correctly flags `is_full_compute: false`
     for off-peak.
   - Unknown scenario → 422.
7. Run only the affected suites: `.venv/bin/python -m pytest tests/test_api.py
   tests/test_smoke.py -q` and report results. Do not modify existing tests.

## Deliverables

- Updated `api/` with the `time_of_day` dimension + scenario descriptors.
- Extended `tests/test_api.py` (time-of-day coverage).
- Completion file with: exactly the approximation formulas used, what is and is NOT
  recomputed, test results, and contract notes for the frontend agent.

## Done when

- [ ] AM-peak responses unchanged & fully tested.
- [ ] Off-peak responses return adjusted values + explicit approximation metadata.
- [ ] Unknown `time_of_day` returns 422 with a clear message.
- [ ] `tests/test_api.py` (+ smoke) passes.
- [ ] No edits to `web/`, `app/`, `scripts/`, `datanova/`, or `data/`.
- [ ] Completion written to `agents/wizard/completions/time-of-day-002.md`.
