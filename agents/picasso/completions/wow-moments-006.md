# Completion — Task 006: Wow moments (narrator, before/after, pulse, gauge)

**Agent:** Picasso (frontend) · **Date:** 2026-11-07
**Status:** DONE

## What was built (frontend-only, `web/`)

### 1. Animated commute narrator (priority #1)
"Hear the trip" expandable inside the story card. The mascot drives the
dashed route (boot-scene motion reused) through 4 steps — Wait / Ride /
Walk / If recommendations ship — from `src/lib/narrator.ts`
(`buildNarratorSteps`), prepared fields only:

- **Wait (real):** anchor 530330305012's recommendation Route 160 —
  headway 2.95 min, +0.74 min wait saving (sensitivity model).
- **Ride (real scores):** jobs / healthcare / food / schools access
  (1.00 / 0.00 / 0.00 / 0.00) — the scores, not a time table, are what
  the data carries.
- **Walk (qualitative):** 37.1% zero-car households (real); no walking-time
  field exists, so none is claimed.
- **After (real + labeled estimate):** Route 160 targets 3,126 residents;
  `est_access_gain_mean` from sensitivity, median income $20,885.

Play/Pause/Next/Back, step dots, `aria-live` captions, keyboard-operable.
`prefers-reduced-motion`: no drive, no auto-advance (static captions).

### 2. Before / After toggle
"Today" vs "If recommendations ship" segmented control (deep-link
`&after=1`, `AppState.beforeAfter` + `state.restore` already supported
atomic patches). `src/lib/before-after.ts` joins recommendations ↔
sensitivity by `route_id` (`routeKey`) into per-geoid gains
(`est_access_gain_mean`, reference 2.0×; max on overlap); MapView clones
features with `gap_after` / `access_after` (`access + gain`, clamped 0–1,
need fixed). Gap + overall-access recolor with an "estimated" legend
(`After = estimated access + corridor gain (no re-routing).`); need/
grade/category stay today's values (honest label, not stale grades).
Opposite-opacity pulse bridges the expression switch; reduced-motion
switches instantly. Visual proof: 14 recommendations / 40,813 residents
(matching `/api/metadata` summary + sensitivity sum), 25 block groups
shifted.

### 3. Isochrone pulse
Click a block group draws a wobbly Rough.js circle (sketch, not GIS) at
the anchor point, radius `60 + score×160` px from the active access
layer (Jobs/Healthcare/Food/Schools pill; otherwise overall access).
Caption always reads "Illustrative coverage — sketch, not a true
isochrone." Projects via `map.project` and follows on move/zoom; one-shot
`ease-out` scale-in (feedback purpose, no looping). Reduced-motion:
instant, no scale.

### 4. Header count-up + equity ring gauge
City-summary counts (1,545 / 40,813) ease-out count up (650 ms, rAF,
cancelling stale tweens — same pattern as `lib/countup`); ring gauge
shows `mean_access_overall` (0.44) as stroke fill with `ease-out`
transition. Both instant under reduced motion.

## Data assumptions (no fabrication)

- No travel-time field anywhere → narrator Walk/Ride are score-based
  qualitative claims; only headway/wait-saving carry minutes (prepared).
- Before/After uses `est_access_gain_mean` only; no re-routing, no
  back-filled `geoids`, no new endpoint. Gains are corridor-level
  estimates applied per block group — labeled estimated everywhere.
- Pulse is an illustrative metaphor (label in the DOM caption itself).
- Time-of-day (Wizard `api/scenarios.py`) untouched; no API changes.

## Skills loaded and how each shaped the result

Per `skills.json`: `task_kind: build_new + refine_existing`,
`design_direction: premium` (sketch), `target: web`, `stack: vanilla`.
Loaded `frontend-design` (all four moments in the approved sketch
language; pulse caption as type-carried honesty, not decoration),
`frontend-ui-engineering` (real buttons for toggle/playback, tolerant
layer/mode state, skeletons N/A), `design-taste-frontend` (toggle shares
the pill interaction cycle; narrator lives in the story card, not a new
view), `high-end-visual-design` (pulse + gauge as craft moments kept
quiet elsewhere), `ui-ux-pro-max` (deep-linking extended with `&after=1`,
progressive disclosure for the narrator), `impeccable` (copy earns its
place; "estimated" labels; no side-stripes), `emil-design-eng` +
`animate` (gates: narrator = rare-tier explanation with user-triggered
play; toggle/pulse = occasional-tier feedback under 300 ms UI, press
`scale(0.97)`, never `scale(0)`; transitions for step changes),
`web-design-guidelines` (final pass: focus, aria, reduced-motion, 390px).

## Verification

- `npm run build` passes (`tsc --noEmit` + Vite, 27 modules).
- **43/43 live checks, 0 console/page errors** (headless Chromium vs
  `vite preview` + real-data API; Task-003→005 suite extended):
  narrator opens + bus + auto-advances; Before/After Estimated label +
  `?after=1` + Today restore; pulse draws with honest caption and scales
  food 120px → jobs 440px (matching `60 + score×160` for 0.0 vs 0.999);
  header counts read "1,545"/"40,813" with ring 0.44; all prior
  behavior (tour, deep-links, overlays, single-treatment audits, mobile
  no-overflow) still green. Screenshots inspected
  (story/narrator, before/after, pulses, mobile).
- Palettes, a11y, reduced-motion, ≤720px preserved. No edits outside
  `web/`, no API change, zero new deps (roughjs + MapLibre only).

## Files changed

New: `src/lib/narrator.ts`, `src/lib/before-after.ts`. Edited:
`src/state.ts` (`beforeAfter` + action), `src/lib/url.ts` (`&after=1`),
`src/lib/colors.ts` (`accessScoreForLayer`), `src/components/map-view.ts`
(gains, mode switch, legend note, pulse), `src/components/story-panel.ts`
(narrator accordion), `src/main.ts` (toggle UI, gauge + count-up,
gains wiring), `src/style.css` (chrome only), `web/README.md` (§6B docs).
Completion: `agents/picasso/completions/wow-moments-006.md`.
