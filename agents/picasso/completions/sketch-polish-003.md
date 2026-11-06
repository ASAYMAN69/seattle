# Completion — Task 003: Sketch-style visual upgrade + motion (make it cooler)

**Agent:** Picasso (frontend) · **Date:** 2026-11-07
**Status:** DONE

## What was built

A visual/UX elevation pass over the Task-002 SPA (`web/`). Architecture, data
flow, API contract, and the four views' behavior are unchanged — this is a
reskin + motion layer. The chrome is now a **sketch / hand-drawn** system on
warm paper with a wobbly-bus mascot and playful-but-civic microcopy
("Wobbly but accurate.", "Warming up the bus…", "Roadblock. Retry to roll
again."), while the data layers keep their colorblind-safe palettes untouched.

### Files changed (all under `web/`)

- `index.html` — added Kalam (hand-drawn display) to the font stack; amber
  favicon + `theme-color` to match paper/ink chrome.
- `src/style.css` — full chrome reskin: paper `#F6F0E4` / paper-2 `#FBF7EE` /
  ink `#2C2822` / muted `#6A6156` / accents amber `#C4622D` + green
  `#31785E`; hand-drawn radius kit (`--r-a/--r-b` irregular multi-radius +
  1.5px ink strokes at 38% opacity); paper grain via fixed
  SVG-turbulence overlay (pointer-events-none, multiply, 0.05 opacity);
  sketch overlays (`.dn-sketch`), boot scene, drawer + scrim, stagger +
  view-enter keyframes, press feedback everywhere, reduced-motion
  block, ≤720px rules (drawer becomes bottom sheet, 44px pill targets).
- `src/lib/mascot.ts` (new) — hand-authored "wobbly bus" SVGs (front-facing
  mascot with eyes/smile + simplified header mark). Dependency-free.
- `src/lib/sketch.ts` (new) — Rough.js overlay painter. Deterministic
  seeded `rectangle(2,2,w-4,h-4)` per host, `position:relative` anchoring,
  `ResizeObserver` repaints with a stable seed. Targets only chrome:
  layer-tabs, legend, what-if controls/callout/minimap, metrics/stats,
  table shell + snapshot, drawer, empty states.
- `src/lib/countup.ts` (new) — rAF ease-out count-up (rAF + ease-out cubic,
  650 ms default). Reduced-motion → instant final value. Cancels the
  prior tween on the same element (slider drags).
- `src/main.ts` — bus header mark; branded boot scene (bus driving a dashed
  route + progress bar + "Wobbly but accurate." stamp + error state with
  "Roadblock. Retry to roll again." + focusable Retry); scrim element with
  click-to-close; staggered view enter (30–50 ms cascade); `paintSketchBoxes`
  on mount / view switch / resize.
- `src/components/drilldown.ts` — hand-drawn × close icon; mascot in the
  "not found" empty state; sketch tiles; stat count-up on open (population,
  poverty %, zero-car %, income — `n/a` for missing, no tween); dashed
  recommendations empty (same "no recommendations" semantics); scrim sync.
- `src/components/whatif.ts` — sketch controls/callout/minimap + sketch
  metric tiles; count-up on corridor change / first render, instant update
  on slider drag (no tween lag); mascot in corridor-not-found empty.
  Interpolation model and metric values identical.
- `src/components/export-view.ts` — sketch table shell + snapshot panel;
  sketch tiles; mascot + dashed empty in the snapshot-empty state
  ("Select a block group…"). Ranking, columns, and CSV bytes unchanged;
  row-click semantics unchanged (select only, no view switch).
- `src/components/map-view.ts` — map background tinted to paper `#F2ECE0`
  (chrome, not data); legend gets a sketch outline. Fill expressions,
  selection, and layers untouched.
- `package.json` (+ lock) — added `roughjs@4.6.6` (only new dependency;
  hand-drawn SVG). `npm audit` clean.

## Skills loaded and how each shaped the result

Per `skills.json`: classified `task_kind: refine_existing + motion`,
`design_direction: sketch → premium/editorial`, `target: web`,
`stack: vanilla`. Loaded every matching trigger (skipped `gpt-taste` —
GSAP-only, stack is vanilla):

- `frontend-design` (baseline) — design plan before code: tokens, type
  (Kalam display over Public Sans; IBM Plex Mono kept for numerals), layout
  (shell unchanged, paper + ink chrome), and anti-template check. Avoided the
  Anthropic cream/terracotta tell by following the brief's sketch direction
  literally; boldness spent on the boot mascot + wobble, restraint
  everywhere else (data layers, typography, spacing).
- `design-taste-frontend` — layout/UX discipline in the reskin: no
  center-bias changes, grid metrics unchanged, full state cycles
  (loading/empty/error all sketch-styled), tactile `:active`
  `scale(0.95–0.98)`, mobile single-column collapse kept, backdrop-blur
  only on floating groups (layer tabs / legend), z-index discipline
  (header 40 / scrim 25 / drawer 30 / boot 50 / grain 60).
- `high-end-visual-design` (closest craft bar for custom editorial) —
  applied the premium surface vocabulary in paper language: irregular
  hand-rolled radii instead of generic 8–12px radii, ink strokes instead of
  grey hairlines, stamped badge + doodle accents, spring-like drawer curve
  kept, staggered entry (30–50 ms), mobile-first collapse. No banned
  fonts/shadows/glows.
- `ui-ux-pro-max` — used as element-level reference: 4.5:1 text contrast
  (muted `#6A6156` on paper passes AA), 44px touch targets, focus
  visibility, tab order, reduced-motion, no-emoji SVG icons, tabular
  numerals. No direct search.py run needed; the skill's quick-reference
  checklist drove the final pass.
- `animate` — motion gates applied explicitly: boot = rare/first-time
  delight budget (linear route, ease-in-out travel, constant progress);
  view enter + stagger = preventing-a-jarring-change (300 ms, 30–50 ms
  cascade); drawer/slider/metrics = occasional-tier (drawer 280 ms
  iOS curve, press 120–160 ms ease-out, count-up 650 ms ease-out on
  corridor change only — slider drag renders instantly so it never
  blocks). Cheapest tool per need (CSS transitions; WAAPI not needed);
  `transform`/`opacity` only; never `scale(0)`.
- `emil-design-eng` — micro-interaction bar: strong custom curves
  (`--ease-out 0.23 1 0.32 1`, `--ease-drawer 0.32 0.72 0 1`), never
  `ease-in` on entrances; `scale(0.97)` press, `scale(0.95)` on pills;
  popover origin not needed (no popovers); transitions-not-keyframes
  for interruptible state; blur not needed; hover gated to
  `(hover:hover) and (pointer:fine)`; reduced-motion ships with every
  animation (opacity/color only, no travel).
- `web-design-guidelines` — final compliance self-review pass: a11y,
  motion, focus, touch, responsive (see below); findings applied before
  the build (44px mobile pills, scrim `aria-hidden`, focus on retry).

## Palettes, accessibility, responsive — preserved

- **Analysis palettes untouched:** `src/lib/colors.ts` was not edited —
  YlOrBr (`#ffffd4…#8c2d04`), Blues (`#eff3ff…#084594`), RdBu
  (`#b2182b…#2166ac`), A–F (`#1a7f37/#2d9d4f/#e3b341/#e0762a/#c62828`),
  unknown `#6b7280`, map line/fill, served/corridor paints. Sketch strokes
  apply to chrome only; choropleth fills and legend ramps are unchanged
  (verified visually: Need YlOrBr gradient, RdBu diverging, grade swap
  still correct). Data text (callout `action`, metric hints, ACS values,
  ranking) is verbatim.
- **Accessibility:** body text `#2C2822` on `#F6F0E4` and muted `#6A6156`
  on paper both AA (≥4.5:1); `:focus-visible` is a 2.5px ink outline with
  offset; `aria-current`/`aria-pressed`/`role=dialog`/Escape-to-close/scrim
  aria-hidden, keyboard-operable nav/pills/slider/select/buttons all kept;
  reduced-motion honored (see below); mascot SVGs are decorative
  (`aria-hidden`, `focusable=false`).
- **Responsive ≤720px:** header stacks, nav reflows, layer pills are
  full-width 44px targets, legend bottom sheet, drawer bottom sheet
  (`min(70dvh, 560px)`, `translateY(102%)` → `0`), what-if controls stack,
  minimap 320px, metrics 2-up. Verified at 390×844: `scrollWidth == clientWidth`
  (no horizontal overflow).

## Motion choices (with reduced-motion fallbacks)

| Moment | Motion | Reduced-motion fallback |
| --- | --- | --- |
| Boot | Bus `translateX` 0 → scene width (2.4 s `ease-in-out`), dashed route, progress `width` 2.4 s linear, stamp/shadow pop | Bus + route hidden; progress shown at 92%; label + stamp static |
| View switch | Enter 300 ms ease-out `translateY(10px)` + staggered 45 ms children `translateY(8px)` | Durations collapsing to 0.01 ms (global block); content instantly visible |
| Drawer | Slide 280 ms `--ease-drawer` (`translateX(102%)` → 0 / bottom-sheet on mobile) + scrim fade 260 ms | Same as above (instant) |
| Pills/nav/buttons | Press `translateY(1px) scale(0.95–0.97)` 120–160 ms ease-out; hover wobble (fine pointers only) | Pressure kept (Comprehension aid), travel removed |
| Metrics | Count-up 650 ms ease-out on corridor change / drawer open (starting at 0, cancelling stale tweens) | Instant final formatted value |
| Wheels | Continuous 900 ms linear spin (boot only) | Static (hidden with bus) |

Reduced-motion block sets `animation/transition-duration: 0.01ms`,
`scroll-behavior: auto`, and the boot static layout. Genuinely felt like it
needed a slow-motion / next-day eye (opacity+height balance in the stagger
and the count-up's start-at-0) — noted below rather than guessed.

## Build + live verification

- `npm run build` passes (`tsc --noEmit` + Vite build, 21 modules).
  `npm audit` → 0 vulnerabilities. No new paid services; no API contract
  or data-type changes; `src/lib/colors.ts`, `types.ts`, `api/client.ts`,
  `state.ts`, `lib/format.ts`, `lib/interpolation.ts`, `lib/csv.ts`
  behaviorally untouched.
- **Live browser self-check** (headless Chromium via CDP, production
  `vite preview` on :4174 + pre-existing FastAPI/dev-api on :8000 serving
  real prepared data): **20/20 PASS, 0 console errors, 0 page errors** —
  boot scene (bus + route + stamp) appears then hides; 4 layer pills toggle
  Need/Access/Gap/Grade with correct legends; map-centre click opens the
  drawer + scrim with count-up stats, grade chips, and empty state; Escape
  closes; what-if shows 14 corridors, 4 metrics, sketch outlines, updates at
  3.0×, callout changes on corridor switch; export shows 25 rows, both CSV
  buttons, sketch shells, row-click selects and stays on Export; drawer
  persists across view return; 390×844 mobile has no horizontal overflow.
  Screenshots inspected for each view (boot, map, gap, drawer, what-if,
  export, mobile).
- Repo `make test` (Streamlit suite) not re-run — no `app/`/`datanova/`
  changes by this task; the pre-existing `git status` Streamlit diffs were
  already in the tree before dispatch and were left untouched.

## Deliberately left out

- **No Rough.js on small tiles by default** — `.dn-stat`/`.dn-metric` are
  "sketch tiles" via CSS irregular radii + ink strokes; only large chrome
  gets wobbly SVG lines. Painting every 150px tile in Rough.js read as
  busy/childish in screenshots; the CSS treatment carries the line without
  the noise.
- **No laptop-eccentric motion** (magnetic buttons, gooey menus, scroll
  hijacks) — judged distracting for a 90-second civic demo; motion budget
  is boot + view enter + drawer + press + count-up only (per `animate` gate).
- **No change to the export row-click** (stays select-only, no view jump)
  and **no change to the hotspot map paint** (served fill + corridor line
  untouched; only the page background tinted to paper).
- **Count-up starts at 0 per tile** (rather than from the previous value)
  — simpler to reason about and cancelling-safe for slider drags; feel
  should be re-checked with fresh eyes at 2–5× in DevTools when the
  main agent next opens it.

## Files changed

All under `web/` (`src/style.css`, `src/main.ts`, `src/components/*`,
new `src/lib/mascot.ts`, `src/lib/sketch.ts`, `src/lib/countup.ts`,
`index.html`, `package.json` + lock for `roughjs`). `node_modules/` and
`dist/` are gitignored. No edits outside `web/` (legacy `app/`, `api/`,
`scripts/`, `datanova/`, `data/` untouched; no git operations).
Completion written to `agents/picasso/completions/sketch-polish-003.md`.
