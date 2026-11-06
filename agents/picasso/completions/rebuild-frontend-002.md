# Completion — Task 002: Rebuild the frontend as a Vite + TypeScript + MapLibre GL SPA

**Agent:** Picasso (frontend) · **Date:** 2026-11-07
**Status:** DONE

## What was built

A complete SPA under `web/` (Vite + TypeScript + MapLibre GL, **no UI
framework**) that reproduces the Streamlit app's four functional areas with
behavior-identical data semantics. Everything is typed against the real
prepared-data shape (`data/prepared/`), and the app consumes only the API
contract — no data payloads are shipped in the bundle.

```
web/
  index.html, package.json, tsconfig.json, vite.config.ts
  public/maplibre-gl-worker.mjs      # MapLibre worker (copied from package)
  src/
    main.ts          # shell + bootstrap + data loading + error/retry state
    style.css        # design system (civic/data-forward; palettes preserved)
    types.ts         # API payload types matching real prepared data
    state.ts         # tiny pub/sub store (view / layer / selection)
    api/client.ts    # typed fetch client (cached) + client-side fallbacks
    lib/format.ts, colors.ts, interpolation.ts, csv.ts
    components/map-view.ts, drilldown.ts, whatif.ts, export-view.ts
  scripts/
    dev-api.mjs          # dev-only mock API (serves REAL prepared data)
    gen-dev-mock.py      # parquet → JSON mocks (dev-only, gitignored)
  dev-mock/              # generated, gitignored
```

## Mapping to the four Streamlit views

| Streamlit view | SPA implementation |
| --- | --- |
| Map explorer (`map_view.py`) | `components/map-view.ts` — full-bleed MapLibre map; boundary outline + fill; analysis layer toggled by pills; click-to-select block groups; adaptive legend (sequential / diverging / grade) |
| Block-group drilldown (`report_card.py`) | `components/drilldown.ts` — slide-over panel (bottom sheet ≤720px): identity, ACS stat tiles, 5 grade chips, top-3 corridor recommendations |
| What-if explorer (`whatif.py`) | `components/whatif.ts` — corridor dropdown (by affected pop), frequency-multiplier slider (1.0–3.0×, default 2.0), action callout, 4 metric tiles, highlight map (served block groups + corridor geometry). Interpolation model ported 1:1 from `whatif.py` (`wait_saving_min`, `what_if_projection` semantics) in `lib/interpolation.ts` |
| Export (`export.py`) | `components/export-view.ts` — city-wide top-25 underserved table (same ranking: need desc, gap asc, grade F-first) + CSV download; per-block-group report-card snapshot download when a block group is selected |

## Design decisions

- **Palettes preserved unchanged** (colorblind-safe): Need = YlOrBr, Access =
  Blues, Gap = RdBu diverging, Grade A–F from `app/views/_ui.py`
  (A `#1a7f37`, B `#2d9d4f`, C `#e3b341`, D `#e0762a`, F `#c62828`,
  unknown `#6b7280`). Domain stops for the sequential ramps are derived from
  the real data ranges (need 0–0.63, access 0–1, gap −0.39–0.79); the
  diverging ramp anchors the 0 midpoint.
- **Civic/data-forward type:** Public Sans (UI) + IBM Plex Mono (data numerals)
  with system fallbacks; `font-variant-numeric: tabular-nums` on metrics.
- **Map is the hero:** full-bleed, fit to the city boundary, fast WebGL.
- **Accessibility:** semantic HTML, visible `:focus-visible`, `aria-current` /
  `aria-pressed` / `aria-label`, dialog `role` on the drawer, reduced-motion
  media query, keyboard Esc closes the drawer.
- **Responsive ≤720px:** bottom-sheet drawer, stacked controls, no horizontal
  overflow (verified at 390px).
- **MapLibre worker:** the library's worker script is copied to
  `public/maplibre-gl-worker.mjs` and wired via `setWorkerUrl("/maplibre-gl-worker.mjs")`
  — without this the style fails to process (invisible fills, broken hit-testing).

## Verification

- `npm run build` passes (strict `tsc --noEmit` + production Vite build).
  `npm audit` → 0 vulnerabilities.
- **Live browser verification** (headless Chromium + Puppeteer against the
  dev server + real-data mock API): **26/26 PASS, 0 console errors, 0 page
  errors**: map canvas renders; 4 layer pills toggle Need/Access/Gap/Grade
  with correct legends; block-group click opens the drilldown with stat tiles,
  5 grade chips, and recommendations; close works; what-if shows 14 corridors,
  default 2.0×, 4 metric tiles, highlight map, updates at 3.0×, and handles the
  coverage-gap corridor; export shows the top-25 table, CSV button, and unlocks
  the snapshot download after a row click; 390px mobile has no horizontal overflow.
- **Choropleth paint confirmed** via WebGL readback (YlOrBr colors visible on
  the Need layer).
- **Production bundle smoke:** `vite preview` serves the built app; shell/nav
  render (booted, no page errors). In production the FastAPI service serves
  `web/dist/` and `/api` same-origin, so the app runs fully.

## API-contract notes for Wizard (backend)

1. `GET /api/equity` must be **ACS-joined**: add `poverty_pct`,
   `zero_car_pct`, `median_income` per block group (the raw equity GeoJSON
   lacks them; the drilldown tiles + export rely on them). The dev mock joins
   from `acs_demographics` the same way `app/data_io._join_acs` does.
2. Sensitivity records use `route_id: null` for the coverage-gap row — keep
   nulls as JSON `null`, and keep `geoids` as string arrays.
3. Grade columns are uppercase strings `"A"`–`"F"`; unknown/null → grey.
4. Top-underserved ranking: `need_index` desc → `gap` asc → grade rank
   (F first) — matches `app/views/export.py`.
5. Column order for CSV exports is `SNAPSHOT_COLUMNS` (mirrors
   `export.SNAPSHOT_COLUMNS`).
6. `GET /api/block-group/{geoid}` returns the one-row snapshot record (or 404).

## Assumptions / minor deviations

- The dev-only mock API (`scripts/dev-api.mjs`) serves **real** prepared data;
  it is explicitly dev-only and gitignored. The shipped app has no demo data —
  if `/api` is unreachable it shows a graceful error + Retry.
- `vite.config.ts` proxies `/api` → `http://localhost:8000` in dev.
- No edits were made outside `web/` (legacy `app/` untouched; test suite for
  the Streamlit app unaffected).

## Files changed

All under `web/` (new). `node_modules/`, `dist/`, and `web/dev-mock/` are
gitignored. Completion written to
`agents/picasso/completions/rebuild-frontend-002.md`.
