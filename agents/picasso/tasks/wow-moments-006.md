# Task 006 — Wow moments: narrator, before/after, isochrone pulse

## Context

Tasks 004 (double borders) and 005 (extra features 1,3,4,5,6) are committed.
Wizard Task 002 (approximate off-peak) is committed. The user approved adding
**wow moments** to the 90-second judge flow (`CHECKLIST.md` §6B). This is a
frontend-only escalation of Task 003's sketch/motion identity — same cute but
neutral direction, same palettes, same behavior contract. No API changes, no
new data, no backend.

Read first: `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`,
this task, and the current SPA (`web/src` — main.ts, state.ts, components/*,
lib/*).

## Objective

Ship the four CHECKLIST.md §6B wow moments, in priority order, so the judge's
90-second flow has memorable beats:

1. **Animated commute narrator (priority #1).** The sketch bus mascot narrates a
   real door-to-door trip for the anchor block group (530330305012 per Task 005):
   wait/ride/walk style breakdown from **prepared fields only**. No invented
   travel-time numbers — the prepared data carries no travel-time field; if a
   number has no source, describe qualitatively. The bus drives the dashed route
   (you already have this motion in the boot scene), with step captions.
2. **Before / After Seattle toggle.** A "Today" vs "If top recommendations ship"
   binary on the map. The Equity Gap (and/or Need/Access) choropleth morphs with
   a short transition — underserved fields brighten. The visual proof is: all
   14 recommendations affecting 40,813 residents (from `/api/metadata` +
   `/api/sensitivity` semantics — reuse already-loaded payloads, no new endpoint).
3. **Isochrone pulse.** Clicking a block group draws a sketch-style coverage
   pulse outward (wobbly circle scaling). Its radius/behavior responds to the
   selected access layer (Jobs / Healthcare / Food / Schools pills). This is a
   *visual metaphor* of reachable coverage, NOT a GIS isochrone — label it as
   illustrative if displayed, or ensure copy never claims GIS precision.
4. **City-summary count-up + equity-score ring gauge.** Header/summary numbers
   animate (count-up already exists — extend to the header summary). Add a ring
   gauge for the equity score. Both `prefers-reduced-motion`-safe.

## Scope

**IN:** `web/` only — `src/components/*` (story-panel, map-view, whatif, drilldown,
main shell), `src/lib/*` (motion/narrator/geometric helpers), `src/style.css`,
`src/state.ts` (`before_after` state extension only), `src/main.ts` (mount/URL state
for before/after if applicable), `web/README.md` (document §6B).

**OUT:** `api/`, `app/`, `scripts/`, `datanova/`, `data/` (all untouched). No
backend. No new dependencies unless a tiny justified one (prefer zero-new-dep —
motion + SVG + MapLibre GL only). No git.

## Guidelines

1. Read rulebook, context, and current SPA first.
2. Run your skill router; classify `task_kind: build_new` + `refine_existing`,
   `design_direction: premium` (sketch), `target: web`, `stack: vanilla`.
   Load and apply the matching skill set, esp. `animate` (motion gates),
   `emil-design-eng` (micro-interactions), `frontend-design` (aesthetic),
   `design-taste-frontend` (layout discipline).
3. **Zero-broken behavior:** all four views, deep-links, tour, access overlay,
   and time-of-day toggle stay working. Reduced-motion: every wow moment has a
   static/instant fallback — content never blocked.
4. **No fabricated numbers.** Before/After uses the prepared recommendation &
   sensitivity values only. If cross-comparing Today vs After needs a value
   that doesn't exist, use qualitative copy + the documented fields.
5. Isochrone pulse: label honestly. If any caption appears, it must not claim
   GIS-grade precision.
6. Self-verify: `npm run build` passes; live-browser checks for each wow moment
   (narrator plays + readable, before/after morphs Gap layer, pulse scales per
   access layer, header count-up + ring render); mobile 390px clean; zero
   console errors.

## Deliverables

- Updated `web/` with the four wow moments.
- `web/README.md` updated (wow moments section).
- Completion file: what you built per wow moment, data assumptions, verification.

## Done when

- [ ] `npm run build` passes.
- [ ] Narrator: plays the real anchor-block-group trip, data-backed, mascot-led.
- [ ] Before/After: toggle morphs the Gap layer; 40,813 figure consistent with metadata.
- [ ] Isochrone pulse: draws on click; scales per access layer; honestly labeled.
- [ ] Header count-up + equity ring gauge present and animated (reduced-motion-safe).
- [ ] Accessibility + ≤720px responsive preserved.
- [ ] No edits outside `web/`; no API contract change.
- [ ] Completion written to `agents/picasso/completions/wow-moments-006.md`.
