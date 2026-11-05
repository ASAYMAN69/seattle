# Seattle Transit Equity Index — Design Document

> DataNova 2026 Global Data-thon — Submission project design
> Track: Operations Research & Decision Intelligence / Data Science & Advanced Analytics
> Date: 2026-11-06 | Deadline: 2026-11-11

## 1. Goal (one sentence)

Build an interactive, data-driven **Transit Equity Index for Seattle** that reveals which communities are underserved by transit relative to their need, quantifies the gap, and recommends concrete, defensible service changes — delivered as a working web demo plus a submission deck.

## 2. Why this wins — judged by their own rubric

| Criterion | Weight | How we hit it |
|---|---|---|
| Technical Implementation | 25% | Real GTFS network analysis (routing/reachability), reproducible Python pipeline, clean architecture, working deployed demo. |
| Innovation & Originality | 20% | "Transit Equity Report Card" per neighborhood (letter grades), accessibility-vs-need gap scoring, and a **what-if service-change explorer** — none of the saturated churn/fraud/intrusion ideas. |
| Data & Analytical Rigor | 15% | Only real public data (GTFS, Census ACS, LODES jobs, OpenStreetMap POIs); documented methodology, validation checks, reproducible scripts. |
| Impact & Feasibility | 15% | Quantified underserved populations, actionable recommendations a transit planner could actually use; feasible because it targets a real, documented Seattle need. |
| Problem Relevance | 15% | Maps directly onto the Urban Mobility problem statement and the Operations Research / Decision Intelligence track. |
| Presentation & Documentation | 10% | One-screen demo with a compelling story, a clean deck, and clear documentation. |

## 3. Differentiators (what makes us stand out)

1. **Equity Report Card** — each neighborhood gets letter grades (A–F) across dimensions (Jobs access, Healthcare access, Food access, Education access, Service frequency). Judges can instantly compare neighborhoods.
2. **Gap score** — we don't just map access; we compute **Access − Need** residual and highlight "high need, low access" corridors (transit deserts with names and faces).
3. **What-if service explorer** — precomputed sensitivity results let a user simulate a frequency boost on a corridor and see the affected population and access change. (Lightweight — no heavy simulation at runtime.)
4. **Human story layer** — a real narrative (e.g., a specific low-income block group with a 75-minute commute) to anchor the demo.
5. **Decision-intelligence framing** — output is not just analysis but *recommendations*: "Increase route 40 frequency 6–9 AM; affects ~12,400 residents in Highline/White Center."

## 4. Product & UX

### 4.1 Personas
- **Judge / demo viewer** — 90 seconds to "get it". Needs instant clarity, a map, a wow moment, and a story.
- **Transit planner / advocate** — wants rigor: filters, methodology, exportable numbers.
- **Resident / civic user** — wants to see *their* neighborhood's grade and what's being recommended.

### 4.2 Primary user journey (judge flow)
1. Land on demo page → full-screen Seattle map with a clear legend and a one-line hook: *"Who in Seattle is disconnected from opportunity?"*
2. Default layer: **Equity Gap** choropleth (red = high need + low access). Instant visual story.
3. Click any neighborhood → side panel opens with the **Equity Report Card** (grades), key stats, and 2–3 **recommendations** each with estimated affected population.
4. Open the **What-if** tab → drag a slider to simulate a frequency increase on a suggested corridor → map and affected-population number update.
5. One-click **Export summary** (for their own use; optional).

### 4.3 Feature list
**MVP (must have):**
- Interactive Seattle map with layer toggles: Need Index, Access Index, Equity Gap.
- Neighborhood drilldown panel with Report Card + stats + recommendations.
- What-if frequency slider on recommended corridors.
- Clean, professional visual design consistent with the DataNova brand (data-forward, civic).

**Stretch (if ahead of schedule):**
- Health / food / jobs access story overlay.
- Time-of-day scenario toggle (weekday AM peak default vs. off-peak).
- Optional short video walkthrough (deliverable).

## 5. Data sources (all real, all free, ~no keys)

| Data | Source | Format | Purpose |
|---|---|---|---|
| Transit schedules | King County Metro GTFS | ZIP/GTFS | Bus network, stops, frequencies |
| Transit schedules | Sound Transit GTFS | ZIP/GTFS | Link light rail / regional service |
| Demographics | Census ACS 5-year, block-group level | CSV/API | Income, zero-car households, poverty, race, disability, age |
| Jobs | Census LEHD/LODES (WA) | CSV | Employment opportunity locations/weights |
| Healthcare / schools / food | Washington Open Data + OpenStreetMap (Overpass) | GeoJSON | Opportunity points (hospitals, clinics, schools, grocery) |
| Neighborhood/block geometry | Census TIGER/Line | Shapefile/GeoJSON | Spatial units for scoring |

All sources are public; only Census may optionally want an API key (we can use bulk CSV extracts instead if needed).

## 6. Methodology (conceptual)

1. **Network build** — parse GTFS into a routable transit graph (stops, routes, frequencies; representative weekday; default AM peak).
2. **Accessibility** — for each block group (origin), compute door-to-door travel time to each opportunity category within thresholds (jobs ≤ 45 min, healthcare ≤ 30 min, food ≤ 20 min, education ≤ 30 min) using the transit graph + walking catchments.
3. **Need Index** — composite of block-group indicators (poverty rate, zero-car share, minority/elderly/disabled shares), normalized 0–1.
4. **Access Index** — normalized composite of category access scores, 0–1.
5. **Gap (Equity) score** = Access − Need residual; quartile-coded into grades A–F per neighborhood and per dimension.
6. **Recommendations** — rule-based over the gap model: high-need low-access areas with low corridor frequency → suggest frequency boost; uncovered areas → suggest new stop/corridor. Attach estimated affected population.
7. **Validation** — sanity checks: travel times vs. known commute patterns; population sums reconcile with census totals; sensitivity of grades to thresholds; qualitative map review.

## 7. Architecture

```
[Real data sources] → [scripts/ ETL] → data/raw  (GTFS, census, POIs)
                                 ↓
                    [scripts/ analysis] → data/prepared (parquet/GeoJSON: scores, grades, recommendations, sensitivity)
                                 ↓
                    [app/ Streamlit app] → deployed demo (Hugging Face Spaces or Streamlit Cloud, free tier)
                                 ↓
                    [Submission package] → PPT deck + demo link (+ optional video)
```

- Heavy computation runs once, here, producing small prepared files.
- The deployed app only reads prepared files → light, fast, free-tier friendly, no ML model hosting.

## 8. Tech stack (all free)

- **Python 3.11+**, `uv` or pip + `requirements.txt`
- Data: `pandas`, `geopandas`, `shapely`, `pyarrow`, `requests`, `overpy` (or requests to Overpass), `partridge` or custom GTFS parser
- Analysis: `networkx` (graph), `r5py` or a lightweight custom RAPTOR-style router (decision in plan), `numpy`, `scipy`
- App: **Streamlit**, `folium` or `pydeck` maps, `plotly`
- Hosting: **Hugging Face Spaces** (free) primary; **Streamlit Community Cloud** (free) backup; GitHub for code
- Docs/deck: Markdown + `python-pptx` for the deck

## 9. Deliverables checklist

- [ ] Working demo link (deployed Streamlit app)
- [ ] GitHub repository with reproducible pipeline (scripts + README)
- [ ] PPT deck (title, problem, data, methodology, results, recommendations, impact, demo, team)
- [ ] (Optional) short video walkthrough
- [ ] Submitted on Devpost before **Nov 11, 2026, 4:00 AM GMT+6**

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| GTFS feed quirks / merged feeds | Validate early (Day 1); fall back to single-agency scope (KC Metro only) if needed |
| Routing library heavy (r5py needs Java) | Plan a lightweight custom router fallback using `networkx` over GTFS graph |
| Census API key friction | Use bulk CSV extracts / TIGER shapes; no key required |
| Streamlit deploy friction | HF Spaces first; demo can also be served from local/VPS if needed |
| Scope creep | Strict MVP-first; stretch features only after MVP deploys |
| Sunk time on data plumbing | Freeze dataset versions in `data/raw`; document schema immediately |

## 11. What I need from you (free-tier only)

1. **A GitHub repo** for this project (create one — public is fine) — or authorization to push to a repo you create; link it to HF Spaces / Streamlit Cloud when we deploy.
2. **Hugging Face account access** (you have one) — or confirm we'll use Streamlit Community Cloud via GitHub OAuth.
3. *(Optional)* If Census API is preferred over bulk CSVs: a free Census API key — not required.
4. Final sign-off on scope and the demo's visual direction (I'll propose a clean civic/data-forward design).

## 12. Assumptions

- English-language app and deck.
- Demo targets desktop browsers (judges screen-share); mobile graceful-degradation only.
- Weekday AM peak as the default scenario; other scenarios are stretch.
- No paid services, no ML model serving, no mock/synthetic data anywhere.
