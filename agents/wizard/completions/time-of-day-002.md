# Completion — Task 002: Approximate time-of-day toggle (off-peak as documented what-if)

**Agent:** Wizard (backend)
**Task:** `agents/wizard/tasks/time-of-day-002.md`
**Status:** DONE
**Date:** 2026-11-07

---

## What I changed

| File | Change |
| --- | --- |
| `api/scenarios.py` (new) | Scenario descriptors + documented off-peak approximation model (parameters, wait-saving, access adjustment, validation helpers). |
| `api/endpoints.py` | Added `time_of_day` (`am_peak` default / `off_peak`) query param to `/api/equity`, `/api/top-underserved`, `/api/block-group/{geoid}` (unknown → 422); extended `/api/metadata` with `scenarios`; added `GET /api/scenarios`. `build_top_underserved` now accepts `time_of_day`. |
| `tests/test_api.py` | Unchanged (existing tests still pass). |

No edits to `web/`, `app/`, `scripts/`, `datanova/`, or `data/`. Existing tests untouched. No git run.

## Approximation formulas (off-peak)

All inputs are prepared fields only; no routing, no new data.

- Off-peak frequency multiplier `m = 0.5` (half of AM-peak frequency).
- Headway `H = 14.0` min (implied by the documented 7-min static wait: wait = headway/2).
- Wait saving `s(m) = clamp((H/2) * (1 - 1/m), -3.5, 3.5)` minutes — signed generalisation of `min((headway/2)*(1-1/m), 3.5)` from `app/views/whatif.py` (`wait_saving_min`). For off-peak: `s(0.5) = -3.5` min.
- Reference saving `s_ref = s(2.0) = 3.5` min.
- Access ratio `r = s(m) / s_ref = -1.0` for off-peak.
- Per block group, per category access `a`: `a' = clamp(a + r * 0.5 * (1 - a), 0, 1)` — proportional to the category access gap `(1 - a)`. Reduces to identity (`r = 0`, i.e. `m = 1.0`, AM peak).
- `access_overall'` recomputed as the mean of the four adjusted category accesses.
- `gap' = access_overall' - need_index` (need unchanged).
- Grades and `need_index` are NOT recomputed (documented limitation).

## What is and is NOT recomputed

- Recomputed: category access values, `access_overall`, `gap`.
- NOT recomputed: grades, `need_index`, `pop_total`, ACS stats, geometry, recommendations, sensitivity.
- No GTFS parsing, no routing, no new data ingestion.

## API contract notes for frontend agent

- `GET /api/equity?time_of_day=am_peak` (default) and `off_peak`. Default is byte-identical to today's shape (no extra props). Off-peak adds per-feature `time_of_day`, `scenario_id`, `approximation_applied: true`, `methodology_note`, and adjusted access values.
- `GET /api/top-underserved?n=25&time_of_day=...`. Off-peak uses adjusted scores for ranking and adds `approximation_note` column.
- `GET /api/block-group/{geoid}?time_of_day=...`. Off-peak adds `approximation_applied: true` + `methodology_note` and adjusted access values.
- `GET /api/metadata` now includes `scenarios: { am_peak, off_peak }`.
- `GET /api/scenarios` returns both descriptors (id, label, is_full_compute, basis, approximations, limitations, narrative).
- Unknown `time_of_day` → 422 with a clear message.
- Off-peak payload carries `is_full_compute: false` in its scenario descriptor.

## Tests

- `tests/test_api.py` + `tests/test_smoke.py`: **21 passed, 1 skipped**.
- Manual verification: default == am_peak byte-identical; off-peak adjusted values in [0,1], finite; deterministic across calls; 422 for unknown scenario; scenarios/metadata flags correct.

## Notes for the main agent

- I did not run git; commit after review.
- No new dependencies required.