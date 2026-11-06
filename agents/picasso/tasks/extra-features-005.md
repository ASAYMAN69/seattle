# Task 005 — Extra features: story overlay, human anchor, share links (FE)

## Context

The current version of the project is committed. The user approved adding the
six stretch features from `CHECKLIST.md` §6. Five of them are frontend-only and
belong to you (Picasso); the sixth (time-of-day toggle) is being handled in
parallel by the backend agent (Wizard) as an approximate, documented scenario —
you do NOT touch the API contract for that.

Read first: `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`,
this task, and the current SPA (`web/src` — main.ts, state.ts, components/*).

## Objective

Ship features 1, 3, 4, 5, 6 from `CHECKLIST.md` §6 (map them as below), keeping
all existing behavior/data identical. This is an additive frontend pass.

## The five features

1. **Access story overlay** — a fifth layer (or an overlay toggle within the
   layer pills) that visualizes per-category access (Jobs / Healthcare / Food /
   Schools) from the existing `jobs_access`, `healthcare_access`, `food_access`,
   `schools_access` fields already on the equity features. Show the dimension
   select + its choropleth. Palette follows `src/lib/colors.ts` conventions.
2. **Human story anchor** — pick **one real low-income block group** from the
   prepared data (high poverty / zero-car share + long access times) and give it
   a dedicated story panel ("Meet block group … — a real neighborhood where the
   average trip to a job takes ~X minutes"). All numbers are real prepared data;
   no invented figures. Surface it as a prominent, easily-found card (e.g. a
   "featured story" slot in the drilldown and/or a map entry point).
3. **Shareable links** — deep-link the UI state to the URL query string:
   `?geoid=<geoid>&layer=<layer>&view=<view>` (and any existing state you add).
   On load, parse the URL and restore the state. Add a "Copy link" button so
   judges can share a specific neighborhood/layer/view.
4. **Onboarding / empty states / guided tour** — a lightweight first-visit
   overlay (dismissible, "Don't show again" via localStorage) that walks through
   the 90-second judge flow in 3–4 steps. Empty states (no selection, no data,
   no recommendations) must all carry the sketch style + mascot, matching Task 003.
5. **Animated storytelling transitions** — smooth transitions between the
   discovery steps (land → map → drilldown → what-if → export) that aid the demo
   narrative. Respect `prefers-reduced-motion` (static fallbacks).

## Scope

**IN:** `web/` only — `src/state.ts` (extend shared state for deep-links), `src/main.ts`
(URL parsing/restoration + onboarding mount, story anchor mount), `src/components/*`
(overlay, drilldown, whatif, export, onboarding, story panel), `src/lib/*`
(story selection, URL helpers, tour logic), `src/style.css` (chrome only),
`web/index.html` (query-string note if useful), `web/README.md` (document deep-link format).

**OUT:** `api/` (backend/Wizard), `app/` (legacy), `scripts/`, `datanova/`, `data/`
(read-only). No API contract changes. No new data payloads. No new backend. No git.

## Guidelines

1. Read rulebook, context, and the current SPA first.
2. Run your skill router; classify `task_kind: build_new` + `refine_existing`,
   `design_direction: premium` (sketch), `target: web`, `stack: vanilla`.
3. **Zero-broken behavior:** existing tests and the four views keep working.
4. Feature contract notes (don't guess data):
   - Access fields exist per feature: `jobs_access`, `healthcare_access`,
     `food_access`, `schools_access` (0–1 normalized). Use them.
   - `geoid` is a string key across features.
   - For the story anchor, compute the "longest commute" story purely from
     already-prepared fields (no new data). If you reference travel times, use
     only values the prepared data actually carries (check the sensitivity /
     equity features for what exists; otherwise describe access qualitatively).
   - **Time-of-day is NOT your scope.** Do not attempt a time toggle.
5. Deep-links must be tolerant: unknown/malformed params → graceful defaults.
6. Accessibility: keyboard-operable tour, focus on open/close, reduced-motion
   fallbacks for every animation; contrast stays AA; ≤720px stays clean.
7. Self-verify: `npm run build` passes; live-browser checks for each new feature
   (overlay toggles, story panel renders real data, deep-link restores state,
   tour dismisses + persists, mobile 390px clean, zero console errors).

## Deliverables

- Updated `web/` with the five features.
- `web/README.md` updated (deep-link format + onboarding note).
- Completion file: what you built per feature, data assumptions, verification results.

## Done when

- [ ] `npm run build` passes.
- [ ] Access story overlay toggles correctly and renders real category access.
- [ ] Story anchor panel shows a real, data-backed block-group narrative.
- [ ] Deep-links (`?geoid=&layer=&view=`) restore state on load; Copy-link button works.
- [ ] Onboarding overlay dismisses and persists (localStorage); doesn't trap the user.
- [ ] Empty states are consistently styled (sketch + mascot) across views.
- [ ] Storytelling transitions present and reduced-motion-safe.
- [ ] Accessibility & ≤720px responsive preserved.
- [ ] No edits outside `web/`; no API contract change.
- [ ] Completion written to `agents/picasso/completions/extra-features-005.md`.
