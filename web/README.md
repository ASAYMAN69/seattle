# Seattle Transit Equity Index — Web SPA

Vite + TypeScript + MapLibre GL single-page app (no UI framework). Replaces the
Streamlit frontend with the same four functional areas, behavior-identical:

1. **Map explorer** — full-bleed MapLibre map. Layer toggle pills for
   Need Index (YlOrBr), Access (Blues), Equity Gap (RdBu diverging), Grade A–F
   (categorical), plus four per-category Access stories — Jobs / Healthcare /
   Food / Schools access (Blues, 0–1) from the existing `*_access` fields.
   Boundary outline. Click a block group to open its report card. A
   prominent "Meet block group …" card surfaces a real low-income story
   anchor (deterministic pick from prepared data; see `src/lib/story.ts`).
2. **Drilldown** — slide-over / bottom-sheet report card: identity, ACS stat
   tiles (population, poverty %, zero-car %, median income), grade chips
   (Jobs/Healthcare/Schools/Food/Overall), and top corridor recommendations.
3. **What-if explorer** — corridor dropdown (ordered by affected population),
   frequency-multiplier slider (1.0–3.0×, default 2.0), action callout, four
   metric tiles, and a highlight map. The interpolation model is a faithful
   TypeScript port of `app/views/whatif.py` (`wait_saving_min`,
   `what_if_projection` semantics).
4. **Export** — city-wide top-N underserved table (CSV download) plus a
   per-block-group report-card snapshot download when one is selected.

## Quick start

```bash
npm install

# With the FastAPI backend running on :8000 (Vite proxies /api → :8000)
npm run dev

# Or without the backend yet: dev-only mock API serving the REAL prepared data
npm run dev:mock        # generates mocks (needs pyarrow), starts API on :8000 + Vite

# Type-check + production build
npm run build
npm run preview
```

`npm run dev:mock:gen` regenerates `web/dev-mock/*.json` from the real parquet
files (`data/prepared/equity/sensitivity.parquet`,
`data/prepared/census/acs_demographics.parquet`). These mocks are **dev-only**
and gitignored; nothing is fabricated — they are the actual prepared data.
The shipped build contains no data payloads: it talks to `/api/...`, which the
FastAPI service serves (and serves `web/dist/` statically in production).

## API contract (consumed by `src/api/client.ts`)

| Endpoint | Payload |
| --- | --- |
| `GET /api/health` | `{ status: "ok" }` |
| `GET /api/boundary` | GeoJSON FeatureCollection (Seattle boundary) |
| `GET /api/equity` | GeoJSON FeatureCollection, ACS-joined block groups |
| `GET /api/recommendations` | GeoJSON FeatureCollection (corridors) |
| `GET /api/sensitivity` | JSON records (what-if table) |
| `GET /api/report-cards` | `{ generated_at, summary, report_cards }` |
| `GET /api/top-underserved?n=25` | JSON records (snapshot columns) |
| `GET /api/block-group/{geoid}` | one JSON record (snapshot columns) |
| `GET /api/metadata` | `{ generated_at, summary, methodology_note }` |
| `GET /api/scenarios` | scenario descriptors (`am_peak` real, `off_peak` approximate) |

`?time_of_day=` is accepted on `/api/equity`, `/api/top-underserved`, and
`/api/block-group/{geoid}` only (`am_peak` default; `off_peak` = the
documented approximation above, never a fresh routed network).

Types mirror the real prepared data (`data/prepared/`) — see `src/types.ts`.

## Deep-links

Shareable UI state: `?geoid=<geoid>&layer=<layer>&view=<view>` (see `src/lib/url.ts`).

- `view` — `map` (default), `whatif`, `export`.
- `layer` — `need_index` (default), `access_overall`, `gap`, `grade`,
  `access_jobs`, `access_healthcare`, `access_food`, `access_schools`.
- `geoid` — a block-group string (e.g. `530330291023`). Unknown or missing
  geoids fall back to the existing "not found" empty state.

On load the app restores the URL state; every state change keeps the
address bar in sync (`replaceState`, no history spam). "Copy link" in the
header copies the full share URL (with clipboard fallback).

- `after=1` — Before/After "If recommendations ship" mode.
- `time_of_day=off_peak` — off-peak scenario (approximate what-if).

## Onboarding

A first-visit guided tour walks the 90-second flow (map → report card →
what-if → export) in 4 steps. Dismiss with ×/Skip/Escape; "Don't show
again" persists via `localStorage` (`dn_onboarding_dismissed`). Keyboard
arrows step, focus returns on close. Empty states (no selection, unknown
block group, no recommendations, corridor not found, snapshot empty) all
carry the sketch style + wobbly-bus mascot.

## Wow moments (§6B)

1. **Commute narrator** (priority #1): "Hear the trip" in the story card
   walks the anchor block group's wait / ride / walk / after steps with
   the mascot driving the dashed route. Numbers cite prepared fields
   only (headway + wait-saving from its recommendation, 0–1 access
   scores, zero-car share); anything without a field is described
   qualitatively. Reduced motion: static step captions, no drive.
2. **Before / After toggle**: "Today" vs "If recommendations ship"
   (deep-link `&after=1`). After = access + precomputed corridor gain
   (`est_access_gain_mean`, reference 2.0×), need held fixed — Gap and
   overall-access recolor with an estimated label; no re-routing.
   Changed block groups (25) get a strong halo while the rest dim; the
   delta readout names the shift ("25 block groups shift · max +8.3 pp
   · most see no change"); the After legend domain is rescaled to the
   moving range and labelled estimated; the drilldown shows the
   selected block group's `+gain` when it moves.
3. **Score tooltip** (was: decorative isochrone circle, deleted):
   hover/click the map for the active layer's score in plain words
   ("Healthcare access 0.00 — the model finds almost nothing reachable
   by transit"). No fake geography, no invented travel times.
4. **Header counts**: block-group / resident counts count up on load,
   plus F-grade (122) and high-need/low-access
   (`need ≥ 0.40, gap < 0` — threshold named in code) totals from
   live equity + report-cards summary. No ring gauge.

**Time-of-day scenario**: AM-peak (default, real) / Off-peak segmented
control in map controls. Off-peak appends `?time_of_day=off_peak` to
`/api/equity`, `/api/top-underserved`, `/api/block-group/{geoid}` and
shows the `/api/scenarios` honesty banner ("approximate what-if, not a
fresh routed network"). What-if stays AM-peak baseline.

**Drilldown when no corridor serves a block group** (most clicks):
grade-driven "What this area needs" card (worst category grade +
overall grade/gap) plus the **nearest** corridor by centroid distance
(labelled "not serving here" with km) — never a bare empty card, never
a fabricated serving corridor.

### Notes / assumptions for the Wizard (API) agent
- `/api/equity` must be **ACS-joined** (add `poverty_pct`, `zero_car_pct`,
  `median_income` per block group), otherwise the drilldown stat tiles read as
  "n/a". The dev mock joins from `acs_demographics` the same way
  `app/data_io._join_acs` does.
- Sensitivity records use `route_id: null` for the coverage-gap row; keep nulls
  as JSON `null` (never strings), and keep `geoids` as arrays of strings.
- Grade columns are uppercase strings `"A"`–`"F"`; unknown/null → grey.
- Top-underserved ranking: `need_index` desc, then `gap` asc, then grade rank
  (F first) — matches `app/views/export.py`.

## Structure

```
web/
  index.html
  vite.config.ts            # dev proxy /api → localhost:8000
  tsconfig.json
  src/
    main.ts                 # shell + bootstrap
    style.css               # design system (civic, colorblind-safe)
    types.ts                # API payload types
    api/client.ts           # typed fetch client + fallbacks
    lib/format.ts, colors.ts, interpolation.ts, csv.ts
    state.ts                # tiny pub/sub store
    components/map-view.ts, drilldown.ts, whatif.ts, export-view.ts
  scripts/
    dev-api.mjs             # dev-only mock API (real prepared data)
    gen-dev-mock.py         # parquet → JSON mocks
```

Design notes: palettes are preserved from the Streamlit app (`app/views/_ui.py`,
`app/styles.css`). Typography uses Public Sans (UI) + IBM Plex Mono (data
numerals) with system fallbacks; focus-visible, reduced-motion, and ≤720px
responsive behavior are implemented.
