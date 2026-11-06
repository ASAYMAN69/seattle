# Completion — Task 005: Extra features (FE: overlay, anchor, share, tour, transitions)

**Agent:** Picasso (frontend) · **Date:** 2026-11-07
**Status:** DONE

## What was built (additive, all under `web/`)

### 1. Access story overlay (CHECKLIST §6 item 1)
Four per-category access layers from the existing `jobs_access` /
`healthcare_access` / `food_access` / `schools_access` fields (0–1):
`access_jobs`, `access_healthcare`, `access_food`, `access_schools` —
sequential **Blues** (`ACCESS_RAMP`, domain [0, 1]) per `lib/colors.ts`
conventions. They appear as four more pills after the existing analysis
pills (8 total; same keyboard/aria pattern). MapLibre fill expression,
legend gradient, and paint path are the existing generic sequential
machinery — no new map code. Data: real prepared fields only.

### 2. Human story anchor (CHECKLIST §6 item 3)
`src/lib/story.ts` — deterministic pick from already-loaded equity
features (no fetch): candidates with `poverty_pct ≥ 25%`,
`pop_total ≥ 500`, `need_index ≥ 0.30`, `gap < 0`; among them lowest
median income, then most negative gap, then highest poverty (relax
25% → 20% → 0% if empty). Live pick: **530330305012** (Tract 030501 / BG 2,
1,505 residents, poverty 29.9%, zero-car 37.1%, income $20,885, need 0.47,
access 0.40, gap −0.07, healthcare/food/schools access near zero, 1
corridor recommendation — Route 160). `StoryPanel` is a prominent,
dismissible card on the map (bottom-left, mascot, real-numbers narrative,
"See its report card" CTA). The drilldown adds an anchor note when the
selected block group is the anchor. **No commute-minutes claim** — the
prepared data carries no travel-time field (only 0–1 access scores and
sensitivity wait-saving), so the narrative is qualitative by design.

### 3. Shareable deep-links (CHECKLIST §6 item 4)
`src/lib/url.ts` — `?geoid=<geoid>&layer=<layer>&view=<view>` (order:
geoid, layer, view; defaults omitted for short links). Tolerant parse:
unknown/malformed view/layer → map / need_index; unknown geoids keep
the drawer "not found" empty state. Boot restores via `state.restore`
(one notification); every state change syncs the address bar via
`replaceState` (no history spam). "Copy link" header button copies the
full URL (clipboard API with `execCommand` fallback) with "Copied!"
feedback. Format documented in `web/README.md` + `index.html` comment.

### 4. Onboarding / empty states (CHECKLIST §6 item 5)
`src/components/onboarding.ts` — 4-step first-visit tour (map → report
card → what-if → export), sketch dialog with mascot, Back/Next/Skip/X/
Done, "Don't show again" persisted to `localStorage`
(`dn_onboarding_dismissed`), focus on open/Escape/focus-return,
arrow-key stepping, backdrop dismiss. All empty states now carry sketch
+ mascot: unknown block group, no recommendations (mascot added),
corridor not found, export snapshot empty (+ boot error already shows
the static bus + stamp).

### 5. Animated storytelling transitions (CHECKLIST §6 item 6)
Extended existing motion (view enter 300 ms + 30–50 ms stagger, drawer
280 ms iOS curve): tour step enter 200 ms `ease-out`, story card enter
240 ms, copy-link press `scale(0.97)` + "Copied!" swap. All
`transform`/`opacity` only, existing `--ease-out`/`--ease-drawer` tokens,
every animation ships with the global `prefers-reduced-motion` fallback
(instant swap, content never blocked). No new motion library.

## Skills loaded and how each shaped the result

Per `skills.json`: `task_kind: build_new + refine_existing`,
`design_direction: premium` (sketch), `target: web`, `stack: vanilla`.
Loaded `frontend-design` (plan first: 8-pill control, bottom-left story
card, centered tour dialog — all in sketch language, no restyle),
`frontend-ui-engineering` (URL state as shareable state, tolerant parse,
real buttons, skeletons N/A, loading/empty/error states complete),
`design-taste-frontend` (access pills share the layer-pill interaction
cycle incl. `:active` press; story card + tour reuse dialog/drawer
states), `high-end-visual-design` (story card as the one memorable
element; tour kept quiet), `ui-ux-pro-max` (deep-linking, progressive
disclosure via tour, empty-states), `impeccable` (tour copy earns its
place; no side-stripe callouts — amber tint only; empty = direction,
not mood), `emil-design-eng` + `animate` (motion gates: occasional-tier
300 ms UI, press 120–160 ms, never `scale(0)`, transitions not
keyframes for step changes), `web-design-guidelines` (final pass:
focus, aria, reduced-motion, 390px).

## Data assumptions (no guessing)

- Access fields exist per feature (`jobs_access`, `healthcare_access`,
  `food_access`, `schools_access`, 0–1 normalized) — used directly.
- ACS fields (`poverty_pct`, `zero_car_pct`, `median_income`) are
  API-joined onto `/api/equity` (per README contract) — story selection
  reads them from the features; missing values read as `n/a` and drop
  out of the pool.
- `geoid` is the string key across features.
- No travel-time number exists → story is qualitative (see §2).
- Time-of-day toggle untouched (parallel Wizard scope); no API,
  payload, or backend changes.

## Verification

- `npm run build` passes (`tsc --noEmit` + Vite, 25 modules).
- **36/36 live checks, 0 console/page errors** (headless Chromium vs
  `vite preview` + real-data API; Task-003/004 suite extended):
  8 pills incl. 4 access stories; Food-access Blues legend toggle;
  story card renders real geoid 530330305012 + CTA opens its report
  card with anchor note; drawer/Escape/scrim unchanged; what-if
  (3 sketches incl. minimap), export (2 sketches), single-treatment
  audits per view (large = sketch-only incl. story, small = CSS-only);
  Copy link → "Copied!" + address bar synced (`?geoid=…`);
  deep-link restore (`?geoid=…&layer=gap&view=map` reopens drawer +
  Gap legend) and tolerant invalid params → defaults; tour shows,
  steps to Done, persists, stays hidden on reload; 390px no
  horizontal overflow. Screenshots inspected (boot, map, story,
  anchor drawer, deep-link, mobile, tour).
- Palettes, a11y (focus/aria/contrast/Escape), reduced-motion, and
  ≤720px preserved. No edits outside `web/`.

## Files changed

New: `src/lib/url.ts`, `src/lib/story.ts`, `src/components/story-panel.ts`,
`src/components/onboarding.ts`. Edited: `src/lib/colors.ts` (4 additive
configs only), `src/state.ts` (`restore` action), `src/main.ts` (URL
restore/sync, Copy link, story + tour mounts), `src/components/drilldown.ts`
(anchor note, rec-empty mascot), `src/style.css` (chrome only),
`web/index.html` (query-string note), `web/README.md` (deep-link format
+ onboarding/access/story docs). No new deps.
