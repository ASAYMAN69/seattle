# Progress

Current state (verified from git history + SDD ledger, 2026-11-06):

- Phase 0 skeleton: DONE (commits d5a377e, af35072).
- Phase 1 ETL: DONE — Tasks 1.1 (GTFS), 1.2 (Census), 1.3 (Opportunities) all
  committed and reviewed.
- Phase 2 analysis: DONE — Tasks 2.1 (network/router), 2.2 (accessibility),
  2.3 (need index), 2.4 (equity/recommend/sensitivity) all committed and reviewed.
- Phase 3 app: DONE — Tasks 3.1–3.4 committed and reviewed.

Key real-data outputs on disk (data/prepared):
- Equity scores (geojson/parquet), report cards (report_cards.json),
  recommendations (14 corridors, 40,813 affected pop), sensitivity table.
- Need index: n=1545, 0 NaNs, [0, 0.63], mean 0.248.

## NEXT
- Task 4.1: whole-branch final review + submission deck (PPT).
- Task 4.2: final QA.
- Deploy (3.5) deferred per user; local hosting for now.

## Dispatch log
- 2026-11-06: Deployed **Picasso** (frontend specialist) from the premade
  template → `agents/picasso/` (tailored AGENT.md). Task 001
  (`agents/picasso/tasks/refactor-frontend-001.md`) written: frontend refactor
  — consolidate styling mechanism, fix deprecated st.components.v1.html, wire or
  remove dead styles.css, verify responsive/accessibility, keep tests green.
  Awaiting human launch + completion.
- 2026-11-06: Task 001 **DONE** (completion in
  `agents/picasso/completions/refactor-frontend-001.md`). Verified: no
  `st.components.v1.html` remains; `styles.css` wired via `_inject_styles()`
  (st.markdown safe path); new `app/views/_ui.py` centralizes palette + HTML
  fragments; `st.iframe` replaces deprecated API; new static regression tests
  added (`tests/test_frontend_refactor.py`); full suite reported 135 passed
  (re-verifying in background). Live Playwright checks 15/15 incl. no leaked
  CSS text, mobile ≤720px clean, zero console errors. Deferred items resolved:
  deprecated API, dead CSS, broad except in app (scripts/ inject out of scope).
  Follow-up: optional `streamlit>=1.45` pin note; commit after review.
- 2026-11-06: Full suite re-verified by main agent: **135 passed, 33 warnings**
  (~6 min). Task 001 formally accepted.
- 2026-11-07: **Stack decision (user-approved):** replace Streamlit app with
  FastAPI (backend) + Vite/TypeScript/MapLibre GL (frontend). Analysis pipeline and
  prepared data untouched; old app kept as fallback until rebuild done.
  Deployed **Wizard** (backend) → `agents/wizard/` (tailored AGENT.md); wrote Task 001
  (`agents/wizard/tasks/fastapi-service-001.md`) and Task 002 for Picasso
  (`agents/picasso/tasks/rebuild-frontend-002.md`). Parallel dispatch, disjoint scope
  (`api/` vs `web/`). Awaiting human launch + completions.
- 2026-11-07: **Both completions received.** Wizard Task 001 DONE (`api/`
  FastAPI service: 9 endpoints, data loaded once at import, CORS for Vite dev,
  SPA static serving w/ index.html fallback; `tests/test_api.py` 18 tests).
  Picasso Task 002 DONE (`web/` Vite+TS+MapLibre SPA: map layers, drilldown,
  what-if, export; npm run build passes; live browser 26/26; dev-only mock
  serves real data; no edits outside web/). Main-agent verification found **one
  real defect**: once `web/dist` existed, unknown `/api/*` paths returned 200
  (SPA index.html) instead of JSON 404 — fixed in `api/main.py`
  (SPAStaticFiles no longer swallows api/* paths); re-verified 18 passed + live
  404/200 serving. Full suite re-run in progress.
- 2026-11-07: **Full suite final: 153 passed, 1 skipped, 34 warnings** (legacy
  Streamlit tests + 18 API tests + smoke tests together). The 1 skip is the
  known real-`web/dist` branch test (covered by a temp-dist test). Both rebuild
  tasks formally accepted. Services verified running: FastAPI backend :8000,
  Vite dev :5173 (`npm run dev`), prod preview :4173 (`npm start`); `/api`
  proxied in both frontend modes; real data confirmed via metadata (1,545 BG,
  grade counts A 629/B 388/C 213/D 193/F 122).
- 2026-11-07: **Dispatch — Picasso Task 003** (`agents/picasso/tasks/sketch-polish-003.md`):
  sketch-style visual upgrade + motion + cute-but-neutral personality over the
  existing SPA. Explicit instruction to load/apply a broader matching skill set
  (animate, emil-design-eng, design-taste-frontend, high-end-visual-design,
  ui-ux-pro-max, web-design-guidelines). Data semantics, API contract, and
  analysis palettes must stay untouched. Awaiting human launch + completion.
- 2026-11-07: **Picasso Task 003 DONE** (completion received; verified build
  green, 20/20 live checks). User-observed defect: double borders on chrome —
  Rough.js sketch overlay + CSS border stacked on same elements (ugly overlap).
  **Dispatch — Picasso Task 004** (`agents/picasso/tasks/fix-double-borders-004.md`):
  singular border treatment per element (sketch for large chrome, CSS for small
  tiles; zero elements with both). Awaiting human launch + completion.
- 2026-11-07: **Committed the full current stack (user-approved prereq for extra
  features):** 3 commits — (1) Streamlit frontend refactor, (2) FastAPI + SPA
  rebuild (incl. Task 003 sketch pass), (3) harness/CHECKLIST/context/README.
  Working tree clean. User approved adding the 6 stretch features next.
- 2026-11-07: **Dispatch for the 6 extra features** (user approved, time-of-day =
  approximate): Picasso Task 005 (`agents/picasso/tasks/extra-features-005.md`)
  — access story overlay, human story anchor, shareable deep-links, onboarding/
  empty states, animated transitions (5 FE features, web/ only). Wizard Task 002
  (`agents/wizard/tasks/time-of-day-002.md`) — approximate off-peak scenario in
  the API (documented what-if, no recompute; api/ only). Parallel, disjoint
  scope; API contract fixed in both briefs. Awaiting human launch.
- 2026-11-07: **Committed both agents' work** (ff7d45f FE 004+005, 8b497cd BE 002;
  verified: build green, API tests 21 passed, /api/scenarios live, off-peak
  flagged + 422 on unknown). Updated CHECKLIST.md §6 all-done + §7 border fix
  done; added §6B Wow Moments (narrator, before/after, isochrone pulse,
  count-up/ring). **Dispatch — Picasso Task 006**
  (`agents/picasso/tasks/wow-moments-006.md`, FE-only). Wizard parked (no
  backend work for wow moments). Awaiting human launch.
- 2026-11-07: **Picasso Task 006 DONE** (completion received; verified: build
  green 27 modules, backend/dev/prod 200, narrator numbers match live API for
  anchor 530330305012 + Route 160, before/after gain join + 40,813 honest,
  pulse caption 'Illustrative coverage — sketch, not a true isochrone' in
  DOM). Committed ff7d45f→95f840f (95f840f = wow moments). CHECKLIST §6B
  marked done. Wizard unchanged (Task 002 still current).
