# Seattle Transit Equity Index — DataNova 2026

Who in Seattle is disconnected from opportunity? A data-driven analysis of transit access vs. community need, with neighborhood report cards and actionable service recommendations.

## Status
- **Phase 0 (skeleton): done** — app shell renders the real Seattle boundary (Census TIGER).
- **Phase 1 (data ETL): in progress** — real GTFS (King County Metro + Sound Transit), Census ACS block groups, and opportunity POIs (LODES jobs, OSM healthcare/schools/food).

## Setup
```bash
make setup      # create .venv + install requirements
make test       # run pytest
make app        # streamlit run app/main.py (local hosting)
```

## Pipeline
```
scripts/fetch_geometry.py       -> data/prepared/seattle_boundary.geojson
scripts/fetch_gtfs.py           -> data/raw/gtfs/*.zip
scripts/parse_gtfs.py           -> data/prepared/gtfs/*.parquet
scripts/fetch_census.py         -> data/prepared/census/*
scripts/fetch_opportunities.py  -> data/prepared/opportunities/*
scripts/run_analysis.py         -> data/prepared/equity/* (Phase 2)
```

## Docs
- Design: `docs/superpowers/specs/2026-11-06-seattle-transit-equity-design.md`
- Implementation plan: `docs/superpowers/plans/2026-11-06-seattle-transit-equity.md`
- Submission deadline: **Nov 11, 2026, 04:00 GMT+6** (Devpost).

## Principles
Real data only · no mock/synthetic · free tier only · no ML model serving.
