# Decisions

## Harness / process
- **Parallel subagent execution with disjoint file ownership** — user ruling
  (overrides the skill's default sequential dispatch). File scopes are exclusive
  per task; implementers do NOT run git; the controller commits after review.
- **What-if slider included in MVP** — user-approved.
- **Hosting deferred** — local laptop only for now; deploy task postponed until
  after submission prep.
- **Frontend tech stack (2026-11-07, user-approved):** replace Streamlit with
  FastAPI (backend) + Vite/TypeScript/MapLibre GL (frontend). Old app kept as
  fallback. `npm run dev` (Vite :5173) / `npm start` (vite preview :4173) /
  `npm run build` / `npm install` are the canonical frontend commands; the
  canonical production path is FastAPI :8000 serving `web/dist` + `/api`.
- **Visual direction (2026-11-07, user-approved):** sketch / hand-drawn style +
  motion + cute-but-neutral personality (warm, whimsical, friendly; NOT
  saccharine or stereotypically gendered). Analysis palettes remain
  colorblind-safe and unchanged as data layers.

## Data & methodology
- **GTFS**: merged feed has no trips.txt → frequency = median over the full
  schedule; waiting time = 7 min/journey (not per boarding); static network
  (depart_min unused); (lat, lon) convention pinned for downstream; direct-walk
  fallback; co-located stop 0-weight edges.
- **Census**: API key friction → official table-based ACS Summary File bulk
  (real). B17021/B25044 substituted at BG level for B17001/B08201 (semantics
  equivalent). Geometry 2023 vs ACS 2022 vintage, 100% geoid join. Suppressed
  income sentinel −666,666,666 treated as missing (component skipped).
- **LODES**: current release (LODES8) with C000 ≡ S000; job-count test ceiling
  raised to 2M (real KC jobs ≈1.46M); Overpass rotation/backoff.
- **Recommendations**: primary thresholds (need≥0.6 & gap≤−0.15) unreachable on
  real data → deterministic percentile fallback (need≥p90 & gap<0), documented.
- **AM-peak frequency** approximates all service patterns (no trips.txt weekday
  filter) — accepted; surfaced as a limitation in the deck.

## Deferred minors (not re-litigating)
- 2.4: median_gap uses mean; `_minutes` misnomer; no warning when trip→route map
  missing; 0-trip low-freq labeling overstates headway; sensitivity gains small.
- App: st.components.v1.html deprecation follow-up; CSS structural best-effort
  (verify ≤720px live); broad except in `_current_selection`/scripts inject.
