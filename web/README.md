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

## Onboarding

A first-visit guided tour walks the 90-second flow (map → report card →
what-if → export) in 4 steps. Dismiss with ×/Skip/Escape; "Don't show
again" persists via `localStorage` (`dn_onboarding_dismissed`). Keyboard
arrows step, focus returns on close. Empty states (no selection, unknown
block group, no recommendations, corridor not found, snapshot empty) all
carry the sketch style + wobbly-bus mascot.

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
