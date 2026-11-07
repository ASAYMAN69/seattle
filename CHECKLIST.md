# DataNova 2026 — Submission Checklist

> **Project:** Seattle Transit Equity Index (DataNova 2026 Global Data-thon)
> **Track:** Operations Research & Decision Intelligence / Data Science & Advanced Analytics
> **Problem statement:** Urban Mobility Pattern Analysis from Transit Data
> **Deadline:** Nov 11, 2026 @ 04:00 GMT+6 (Devpost)
> **Format:** Online

This is a tracking checklist, not a score. Work top-to-bottom: **Draft → Build → Harden →
Package → Submit**. Checked items are ones verified done; unchecked items remain open.

---

## 0. Judging criteria (what you're optimizing for)

| Criterion | Weight | What it rewards |
| --- | --- | --- |
| Technical Implementation | 25% | complexity, quality of execution, appropriate tools, functionality |
| Innovation & Originality | 20% | novelty, creativity, differentiation from existing solutions |
| Problem Relevance | 15% | clear problem statement, importance, track alignment |
| Data & Analytical Rigor | 15% | quality of data usage, methodology, validation, reliability |
| Impact & Feasibility | 15% | practical applicability, scalability, real-world/societal impact |
| Presentation & Documentation | 10% | clarity of explanation, demo quality, complete documentation |

- [x] Every section below maps to at least one criterion above.
- [x] No deliverable ships that doesn't advance a criterion.

---

## 1. Registration & eligibility

- [ ] Registered on Devpost for DATANOVA 2026 GLOBAL DATA-THON.
- [ ] Team registered (team entry, not solo).
- [ ] Eligibility confirmed: above legal age, students only, no companies/professional organizations.
- [ ] Track chosen: Operations Research & Decision Intelligence (or Data Science & Advanced Analytics).
- [x] Problem statement locked: **Urban Mobility Pattern Analysis from Transit Data**
      ("analyze public transit data to uncover mobility patterns, identify underserved
      routes and propose data-driven service improvements").

---

## 2. Project identity (draft → locked)

- [x] Project title finalized.
- [x] One-sentence value proposition ("Who in Seattle is disconnected from opportunity?").
- [x] Target personas defined (judge, transit planner/advocate, resident/civic user).
- [x] Non-novelty check: confirm the Transit Equity Report Card / gap-score / what-if
      explorer differentiate from the saturated churn/fraud/intrusion ideas.
- [x] README updated to reflect final product (stack, status, run instructions, pipeline).

---

## 3. Data — real sources & validation (Data & Analytical Rigor, 15%)

- [x] All data sources documented (real, public, free): King County Metro GTFS, Sound
      Transit GTFS, Census ACS 5-year, LODES jobs, OSM/Washington Open Data POIs, Census TIGER geometry.
- [x] Every source has fetch + parse scripts in `scripts/` (reproducible).
- [x] No mock/synthetic data anywhere (verified, incl. dev-only mock API is clearly labeled & gitignored).
- [x] Row counts / null counts / ranges spot-checked against sources.
- [x] Census vintage documented (geometry 2023 vs ACS 2022) + 100% geoid join.
- [x] Suppressed-income sentinel (−666,666,666) handled as missing and documented.
- [ ] Data licensing/attribution confirmed (Census, LODES, OSM attribution present).

---

## 4. Analysis & methodology (Technical Implementation, 25%)

- [x] GTFS parsed into a routable transit graph (stops, routes, frequencies).
- [x] Accessibility computed per block group: jobs ≤ 45 min, healthcare ≤ 30 min,
      food ≤ 20 min, education ≤ 30 min (transit graph + walking catchments).
- [x] Need Index = composite of poverty, zero-car, minority/elderly/disabled shares (0–1).
- [x] Access Index = normalized composite of category access (0–1).
- [x] Gap (Equity) score = Access − Need, quartile-coded into grades A–F.
- [x] Coverage documented: weekday AM-peak default scenario, static-network approximations.
- [x] Documented deviations are recorded in `context/decisions.md` and surfaced in the deck.
- [x] Validation checks: population sums reconcile with census totals; grades sensitivity
      to thresholds; qualitative map review.
- [x] Reproducibility: pipeline runs end-to-end (fetch → parse → analysis) to regenerate
      all prepared outputs from raw data.

---

## 5. Core features — demo (MVP)

### 5.1 Interactive map (the hero)

- [x] Seattle boundary renders (Census TIGER).
- [x] Layer toggles: Need Index, Access Index (overall), Equity Gap, Grade A–F.
- [x] Equity Gap layer is the default (red = high need + low access) — the "90-second" hook.
- [x] Legends explain each layer's direction; colorblind-safe palettes (YlOrBr / Blues / RdBu / A–F).
- [x] Map feels fast: WebGL (MapLibre GL); no dashboard chrome clutter.

### 5.2 Neighborhood drilldown + Equity Report Card

- [x] Click a block group (map + dropdown) → drilldown panel.
- [x] Report card shows: letter grades (Jobs / Healthcare / Schools / Food / Overall) + ACS stats
      (population, poverty %, zero-car %, median income).
- [x] 2–3 recommendations per neighborhood, each with estimated affected population.
- [x] Unknown geoid / no-recommendation cases handled gracefully.

### 5.3 What-if frequency explorer

- [x] Corridor dropdown (ordered by affected population, 14 corridors).
- [x] Frequency multiplier slider (1.0–3.0×, default 2.0).
- [x] Action callout + reference caption (documented interpolation model).
- [x] Four metric tiles: affected residents, newly benefiting residents, est. wait saving, access improvement.
- [x] Highlight map: served block groups + corridor geometry.

### 5.4 Export & summary

- [x] City-wide top-N underserved table (ranked need desc → gap asc → grade F-first).
- [x] CSV download: city-wide table + per-block-group report-card snapshot.
- [x] Methodology note visible on the export view.

---

## 6. Extra / stretch features (nice-to-have, only after MVP deploys)

- [x] Health / food / jobs access story overlay (narrative layer).
- [x] Time-of-day scenario toggle (weekday AM peak default vs off-peak) — **approximate, documented what-if** (not a fresh routed network; see `api/scenarios.py`, `GET /api/scenarios`).
- [x] Human story anchor: a specific low-income block group with a long real commute.
- [x] Publish-ready shareable links (deep-links to a block group / layer).
- [x] Lightweight onboarding / empty states / guided tour for judges.
- [x] Animated storytelling transitions between discovery steps (beyond current motion).

### 6B. Wow moments (judge 90-second flow — user-approved 2026-11-07)

- [x] **Animated commute narrator:** sketch bus mascot narrates a real door-to-door trip for the anchor block group (wait/ride/walk breakdown from prepared fields only; qualitative where no travel-time field exists).
- [x] **Before / After Seattle toggle:** "Today" vs "If top recommendations ship" — Equity Gap choropleth morphs, underserved fields brighten — visual proof for 40,813 affected residents.
- [x] **Isochrone pulse:** click a block group → score tooltip (honest, "0–1 model value, not a travel time") — sketch pulse circle was deleted as a fake bubble (see Task 008).
- [x] City-summary count-up + equity-score ring gauge on the map header (motion escalation).

---

## 7. Design & UX polish

- [x] Visual direction locked and applied consistently (civic, data-forward; current sketch-style pass).
- [x] Single-outline border treatment per element (no double-line overlap — see Task 004).
- [x] Typography, spacing, color, focus states consistent across views.
- [x] Motion: loading screen, drawer, pills, metric count-up, view transitions; reduced-motion honored.
- [x] Responsive: desktop-first demo screen; ≤720px graceful (bottom-sheet drawer, stacked controls).
- [x] Accessibility: contrast (AA), keyboard operability, aria-current/aria-pressed, visible focus.
- [x] 90-second judge flow: land → map + hook; click → report card; what-if → number; export.
- [x] No raw CSS/HTML source text visible anywhere in the rendered app.

---

## 8. Performance & quality gates (Technical Implementation, 25%)

- [x] Full test suite green (`make test` → 153 passed).
- [x] Prepared payloads sized for fast load (equity GeoJSON ~6 MB — acceptable, cached).
- [x] SPA production build green (`npm run build`).
- [x] API tests green (`tests/test_api.py`).
- [x] Static routes verified (SPA serves final index, `/api/*` unknown → JSON 404, not HTML).
- [ ] Lighthouse/accessibility spot-check on the demo page.
- [x] Code is committed with clean, logical commits (refactor / API / SPA / harness / wow moments / fake-bubble burst / start_all / modularize).

---

## 9. Deployment (working demo link — required deliverable)

- [ ] Host chosen: Hugging Face Spaces (primary) or Streamlit Cloud (backup) — free tier.
- [x] Production path defined: FastAPI serves `web/dist` + `/api` same-origin (single process).
- [ ] Deployed demo URL is public, loads the map with real data, and remains up.
- [ ] Demo URL tested in a fresh browser (not logged in, not local) before submission.
- [x] Environment variables / build steps documented so the deploy is reproducible (see `start_all.sh` + `web/README.md`).

---

## 10. Submission package — PPT (required deliverable)

Structure (order matters — hits the six submission components):

- [ ] Title + team.
- [ ] Problem statement (urban mobility, underserved routes, Seattle context).
- [ ] Solution & methodology (GTFS graph → accessibility → need/gap → grades → recommendations).
- [ ] Data & rigor (real sources, validation, documented deviations/limitations).
- [ ] Results (key numbers: corridors, affected population, gap distribution, grade map).
- [ ] Impact & feasibility (planner-actionable recommendations, quantified).
- [ ] Demonstration (screenshots / live link / walkthrough guide).
- [ ] Limitations & honest caveats (AM-peak approximation, static network).
- [ ] Team contributions (who did what).
- [ ] Deck opens cleanly (no missing fonts/images, no broken links).

---

## 11. Demonstration (required deliverable)

- [ ] Working prototype link live (see Section 9).
- [ ] Optional video walkthrough (short, judge-focused: map → drilldown → what-if → export).
- [ ] Screenshots captured (desktop map, report card, what-if, export, mobile ≤720px).
- [ ] Demo script / talking points for the 90-second flow.

---

## 12. Documentation (Presentation & Documentation, 10%)

- [x] README: accurate status, setup, how to run dev/prod, data sources, methodology, deployment.
- [x] API docs (`/docs`) accurate and complete.
- [x] Repo is public and has a runnable pipeline + clean `context/` / docs (incl. `context/README.md` file-by-file map).
- [x] `CHECKLIST.md` (this file) tracked honestly — never check boxes pre-emit.
- [x] Methodology + validation summary exists in repo (re-runnable).

---

## 13. Final pre-submission verification

- [ ] Demo link opens on a clean browser and shows real data.
- [ ] PPT opens and renders correctly.
- [ ] Video (if included) plays end-to-end.
- [ ] Every link in the Devpost submission works.
- [ ] Submitted before the deadline: **Nov 11, 2026 @ 04:00 GMT+6**.
- [ ] Submission includes all six components: title/overview, problem statement,
      solution & methodology, demonstration, impact & validation, team contributions.

---

## 14. Post-submission (if shortlisted)

- [ ] Be ready to present/demonstrate during evaluation/final rounds.
- [ ] Prep answers for judge Qs: methodology rigor, data assumptions, limitations, scalability, impact.
