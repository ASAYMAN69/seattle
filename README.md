# Seattle Transit Equity Index — DataNova 2026

Who in Seattle is disconnected from opportunity? A data-driven analysis of transit access vs. community need, with neighborhood report cards and actionable service recommendations.

Built for the **DataNova 2026 Global Data-thon** (Track: Operations Research & Decision Intelligence / Data Science & Advanced Analytics). Submitted on Devpost — deadline **Nov 11, 2026, 04:00 GMT+6**.

## Status

| Phase | Scope | Status |
|---|---|---|
| 0 | Skeleton — real Seattle boundary (Census TIGER) | ✅ Done |
| 1 | Data ETL — GTFS (KC Metro + Sound Transit), Census ACS, opportunities (LODES jobs + OSM POIs) | ✅ Done |
| 2 | Analysis — transit network/router, accessibility, need index, equity scores/recommendations/sensitivity | ✅ Done |
| 3 | App — Vite + TypeScript + MapLibre GL SPA over a FastAPI backend | ✅ Done |
| 4 | Submission deck + final QA | 🔜 In progress |

## Deployment

The demo is currently served locally (`./start_all.sh` → `http://localhost:4173`).
A **free, static deployment** (SPA + precomputed JSON on GitHub Pages) is in
prep so judges get one zero-friction public URL. Tracked in `CHECKLIST.md` §9.

## Stack

- **Backend:** FastAPI (`api/`) — read-only JSON endpoints over the prepared data; serves the built SPA (`web/dist`) same-origin.
- **Frontend:** Vite + TypeScript + MapLibre GL SPA (`web/`) — sketch-style chrome, colorblind-safe palettes, equity map layers, report cards, what-if explorer, export dashboards.
- **Analysis:** Python — GTFS graph routing (Dijkstra), ACS composite need index, access−need gap → A–F grades, corridor recommendations + sensitivity table.
- Real data only · free tier only · no ML model serving · no mock/synthetic.

## Run it

```bash
./start_all.sh        # one script: checks data, builds, starts backend (:8000) + dev (:5173) + prod (:4173)
```

Or manually:

```bash
make setup            # .venv + requirements
make test             # pytest (full backend suite)
cd web && npm install
npm run dev           # dev server http://localhost:5173 (proxies /api → :8000)
npm run build         # type-check + production build → web/dist
npm start             # production preview http://localhost:4173
```

If `data/prepared/` is empty, run the pipeline first (`./start_all.sh` does this automatically):

```
scripts/fetch_geometry.py → scripts/fetch_gtfs.py → scripts/parse_gtfs.py
scripts/fetch_census.py → scripts/fetch_opportunities.py → scripts/run_analysis.py
```

## Data sources (all real, public, free)

- King County Metro + Sound Transit **GTFS** feeds
- Census **ACS** 5-year block-group demographics + **TIGER** geometry
- LEHD **LODES** jobs (WA)
- OpenStreetMap / Washington Open Data **POIs** (healthcare, schools, food)

## Docs

- Design: `docs/superpowers/specs/2026-11-06-seattle-transit-equity-design.md`
- Implementation plan: `docs/superpowers/plans/2026-11-06-seattle-transit-equity.md`
- Submission checklist: `CHECKLIST.md`
