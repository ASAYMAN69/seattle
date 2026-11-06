# Task 003 — Sketch-style visual upgrade + motion (make it cooler)

## Context

Task 002 built the SPA (`web/`) as a clean, civic, data-forward app. It functions
perfectly and is verified (build green, 26/26 browser checks). The user now wants
a **visual identity upgrade**: make it *cooler* — **sketch / hand-drawn style,
with motion and playful-cute personality** (friendly & whimsical, **not**
saccharine or stereotypically gendered).

This is a **visual/UX elevation pass over the existing SPA** — do NOT rebuild
architecture, do NOT change data semantics, do NOT touch the API. The four views,
data flow, and behavior stay exactly as they are; you are reskinning and adding
motion/personality.

Read first: `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`,
this task, and the current SPA (`web/src/` — main.ts, style.css, state.ts,
components/*, lib/*).

## Objective

Transform the SPA into a memorable, sketch-aesthetic demo with delightful motion,
while keeping it professional enough for judging (readable data, colorblind-safe
analysis palettes, accessibility, responsive).

## Design direction (user-specified)

1. **Sketch / hand-drawn style**
   - Wobbly/hand-drawn borders and shapes (Rough.js or hand-authored SVG paths)
     for cards, buttons, pills, panels, the drawer, callouts.
   - Paper-like texture/background (subtle; don't hurt text legibility).
   - Hand-drawn doodle accent: a small recurring mascot, e.g. a cute bus
     character (a "wobbly bus") used sparingly in the header, loading screen,
     and empty states. Keep it charming, not childish.
   - Ink-like stroke color for UI chrome; keep data layers clean.
2. **Motion & animations**
   - Animated **loading screen** (the bus doodle driving along a dashed route /
     progress line with playful steps) replacing the current plain text boot
     state.
   - Micro-interactions: button/pill press feedback, drawer slide-in, view
     transitions, metric count-up when a report card or what-if numbers appear.
   - Staggered/reveal transitions where they aid the demo's story.
   - Respect `prefers-reduced-motion` (provide static fallbacks).
3. **Cute but neutral**
   - Warm, friendly palette (paper cream + ink + one or two cheerful accents)
     layered **under** the existing colorblind-safe analysis palettes (which are
     sacred and must remain readable/unchanged as data layers).
   - Rounded, approachable shapes; friendly microcopy tone (e.g. "Wobbly but
     accurate.") — tasteful, not gimmicky.
   - Avoid pink/sparkly/stereotypically "girly" tropes; "cute" here = warm,
     whimsical, approachable.

## Skills — use MORE of your toolkit (explicit instruction)

The user explicitly asked you to bring more skills to bear. Classify this task
(`task_kind: refine_existing` + `motion`, `design_direction:` sketch (map to the
closest available — treat as a custom premium/editorial direction), `target: web`,
`stack: vanilla`) and **load and actively apply every matching skill** in your
router, including at minimum:

- `frontend-design` (baseline) — aesthetic direction, avoiding templated defaults
- `design-taste-frontend` — layout/UX discipline while reskinning
- `high-end-visual-design` or the closest aesthetic-polish skill — craft bar
- `animate` — decide how/where motion earns its place
- `emil-design-eng` — micro-interactions / invisible polish
- `gpt-taste` (if it fits) — motion + editorial layout
- `ui-ux-pro-max` — reference for specific elements (palettes, motion, states)
- `web-design-guidelines` — final compliance self-review (a11y, motion, UX)

Follow the router's discipline (never *all* skills; load those whose triggers
match). The intent is a **deliberately broader skill application**, not a
blanket load.

## Scope

**IN:** `web/` only — `src/style.css` (major), `src/main.ts` (loading/boot
state, shell chrome), `src/components/*` (drawer, pills, callouts, metrics,
empty states), new assets (e.g. mascot SVG, texture, sketch utilities under
`src/lib/`), and `package.json` if you need a small dependency like `roughjs`
(hand-drawn SVG) — minimal, justified, and it must build.

**OUT:** `api/`, `app/`, `scripts/`, `datanova/`, `data/` (all read-only /
untouched). No data-semantics changes. No API contract changes. No new backend.
No git operations.

## Guidelines

1. Keep the four views functional and identical in behavior/data (map layers,
   drilldown, what-if, export). This is a skin + motion pass.
2. The analysis palettes (YlOrBr, Blues, RdBu, A–F grades) and the choropleth
   layers stay readable and unchanged. Sketch styling applies to **chrome**, not
   to confusing the data.
3. Loading screen: replace the plain text with an animated branded one; keep an
   error/retry state that also fits the style.
4. Accessibility: WCAG contrast for text remains; `:focus-visible` remains;
   reduced-motion honored; keyboard operable.
5. Responsive ≤720px must remain clean (drawer becomes bottom sheet, etc.).
6. Perform a full self-verification: `npm run build` passes
   (`tsc --noEmit` + vite build), and live-browser checks (headless Chromium)
   for: boot/loading animation, layers toggle, click-select drilldown, what-if
   slider/metrics, export download, mobile 390px no horizontal overflow, no
   console errors. Keep the existing `AppTest`-style unit coverage passing.
7. Do not break the API contract or the data types.

## Deliverables

- Updated `web/` with the sketch style, motion, mascot, and loading screen.
- `package.json` updated only if adding `roughjs` (or similar) — keep it minimal.
- Completion file with: what you changed, the skill(s) you loaded and how each
  shaped the result, how you preserved data palettes/a11y/responsive, motion
  choices (with reduced-motion fallbacks), build + live verification results,
  and anything you deliberately left.

## Done when

- [ ] `npm run build` passes.
- [ ] Sketch aesthetic evident across chrome (cards/pills/drawer/callouts/header).
- [ ] Animated loading screen with the mascot (and static reduced-motion fallback).
- [ ] Motion/micro-interactions present (drawer, pills, metric count-up, view
      transitions) — tasteful, not distracting.
- [ ] Cute-but-neutral tone: warm, whimsical, friendly; no saccharine/
      stereotypically gendered styling.
- [ ] Analysis palettes and data layers unchanged and readable (colorblind-safe).
- [ ] Accessibility kept: contrast, focus-visible, keyboard, reduced-motion.
- [ ] Responsive ≤720px still clean.
- [ ] All four views function identically (data/behavior unchanged).
- [ ] Live browser self-check passes (list what you tested).
- [ ] No edits outside `web/` (except justified minimal `package.json` dep).
- [ ] Completion written to `agents/picasso/completions/sketch-polish-003.md`.
