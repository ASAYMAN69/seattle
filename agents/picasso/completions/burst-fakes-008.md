# Completion — Task 008: Burst the fake bubbles

**Agent:** Picasso (frontend) · **Date:** 2026-11-07
**Status:** DONE

## Per-item verdicts

### 1. Before/After → REPLACE presentation (halo + readout + rescale)
Small shift (gains 0.010–0.083, 25/1,545 polygons) is now perceivable:
- `after-halo` line layer (strong outline, 0.95 opacity) + `after-dimmer`
  paper fill (0.52) on the 25 changed block groups (`changedFilter`).
- Delta readout in the Before/After box: "25 block groups shift · max
  +8.3 pp · most see no change" from `computeGainsByGeoid` (real).
- After gap domain rescaled to the changed `gap_after` range
  (`changedGapAfterRange`), honestly labeled "estimated" + "Scale fits
  the moving block groups." No exaggeration beyond the real range.
- Drilldown shows "+0.74 pp access (estimated, no re-routing)" for a
  changed BG in After mode (`gains` prop).
Zoom-to-corridor optional flair not implemented (halo + readout picked).

### 2. Header gauge → DELETE ring, contextual counts
Ring deleted. Header meta now: `1,545 block groups · 40,813 in
recommended corridors · 122 F-grade · 22 high-need / low-access
(need ≥0.40, gap <0)` — every number traceable: summary counts +
`grade_counts.F` (report-cards) + equity-feature count with the single
named threshold (`HIGH_NEED_MIN`, `LOW_ACCESS_MAX` in main, labeled in UI).

### 3. Top recommendations → REPLACE empty card
Never empty: grade-driven "What this area needs" (worst category grade +
overall grade/gap) + **nearest** corridor by centroid distance
(bounding-box centroid, equirectangular km) labelled "not serving here"
with km (never a fabricated serving corridor). All fields prepared.

### 4. Time-of-day → WIRE
AM-peak default; Off-peak segmented control (map controls). `timeOfDay`
in state + `?time_of_day=` only when off-peak (defaults omitted).
Appended to `/api/equity`, `/api/top-underserved`,
`/api/block-group/{geoid}` (`api/client.ts` query helpers; cache keys
include the query). `/api/scenarios` descriptor renders the honesty
banner ("approximate what-if, not a fresh routed network: …") with a
static fallback when the endpoint is unavailable (dev mock). Toggle
refetches equity, swaps MapView/drilldown/export data in place
(`setEquity` / `setEquityById` / `refreshTop`), keeps viewport.
What-if stays AM-peak baseline (documented in README). Deep-link
restores `time_of_day`.

### 5. Isochrone → DELETE circle, tooltip replaces it
Rough.js circle, `showPulse`, and rough import removed. Hover/click
score tooltip (`.dn-tip`, `role="status"`): "[Category] access 0.00 —
the model finds almost nothing reachable by transit. Score is a 0–1
model value, not a travel time." No fake geography, no invented
minutes. Task-suggested "30 min by this model" wording deliberately
**not** used: the prepared access scores are composites, not measured
30-min reach — claiming it would fabricate. Documented deviation.

## Data assumptions
- `est_access_gain_mean` = corridor reference gain (2.0×), max on
  overlap; gains ≤ 0.083.
- Off-peak access comes from the backend `scenarios.adjusted_equity_frame`
  (m=0.5, scale 0.5, grades/need not recomputed) — frontend labels it
  via `/api/scenarios` and never re-implements the model.
- Nearest-corridor km is equirectangular approx for ranking/display
  ("≈"), honest label.

## Skills
`refine_existing` / `premium` / `web` / `vanilla`: `frontend-design`,
`design-taste-frontend`, `high-end-visual-design`, `ui-ux-pro-max`,
`impeccable` (states/direction), `emil-design-eng` + `animate`
(gates: toggle/tooltip = occasional feedback; halo/dimmer transitions
150 ms, tooltip 125–200 ms, no scale(0), reduced-motion instant),
`web-design-guidelines` (final pass).

## Verification
- `npm run build` passes (27 modules).
- **43/43 live checks, 0 console errors** (headless Chromium vs
  `vite preview` + dev-api): After estimated label + halo/dimmer +
  readout + `?after=1`; header 1,545/40,813/122/22 (no ring);
  needs-card + nearest corridor on non-covered BG; time-of-day toggle
  recolors + banner + deep-link restore; tooltip honest caption (pulse
  gone); all prior behavior (tour, narrator, pulses removed, audits,
  mobile 390px clean). Screenshots inspected.

## Files changed
`web/src/state.ts`, `web/src/lib/url.ts`, `web/src/api/client.ts`,
`web/src/main.ts`, `web/src/components/map-view.ts`,
`web/src/components/drilldown.ts`, `web/src/components/export-view.ts`,
`web/src/style.css`, `web/README.md`. No new deps, no backend/git.
