# Completion — Task 004: Fix overlapping double borders (sketch overlay vs CSS border)

**Agent:** Picasso (frontend) · **Date:** 2026-11-07
**Status:** DONE

## What was fixed

Task 003 rendered two border systems on the same elements: a CSS
`border: 1.5px solid var(--line-soft)` (via `.sketch-card` / `.sketch-tile`
and per-element rules) **plus** a Rough.js wobbly SVG rectangle painted by
`src/lib/sketch.ts`. The fix makes the treatment **singular per element**:
large chrome keeps exactly one hand-drawn stroke; small tiles/dense UI keep
exactly one CSS border. No behavior, data, or API changes; no new deps.

### Chosen rule (per task guideline 1)

**Large chrome → Rough.js hand-drawn stroke only (CSS `border` removed).**
Seeded rectangle inset 2px, aligned to the element box
(`position:relative` anchoring already in `paintSketch`).

**Small tiles / dense UI → CSS border only (Rough.js removed).**
Irregular `--r-b`/`--r-pill` radius kit + 1.5px ink-soft stroke; no SVG
overlay. This matches the Task-003 completion note ("Rough.js on small tiles
read as busy").

### Exactly which elements now use which

| Element | Outline | Changes made |
| --- | --- | --- |
| `.dn-layer-tabs` (group) | **Rough only** | `.sketch-card` border removed; group CSS never had a border — now truly single |
| `.dn-map-legend` | **Rough only** | Same `.sketch-card` removal |
| `.dn-whatif-controls` | **Rough only** | Same |
| `.dn-callout` | **Rough only** | Removed `border` + `border-left: 4px` side stripe; amber `--accent-soft` background carries the accent |
| `.dn-table-wrap` | **Rough only** | `.sketch-card` border removed; `padding: 2px` retained as sketch breathing room |
| `.dn-export-snapshot` | **Rough only** | Same |
| `.dn-minimap` | **Rough only** | Removed `border` (was CSS + sketch-card border, and **not** in sketch targets — now explicitly in `DEFAULT_TARGETS`) |
| `.dn-drawer` (+ ≤720px bottom sheet) | **Rough only** | Removed `border-left` (desktop) / `border-top` (mobile); shadow retained for separation |
| `.dn-metric`, `.dn-stat` | **CSS only** | Removed from sketch targets; borders/radius/shadow moved directly onto `.dn-metric`/`.dn-stat`; dropped `sketch-tile` classes in `whatif.ts`/`drilldown.ts`/`export-view.ts` |
| `.dn-empty` | **CSS dashed only** | Removed from sketch targets + removed explicit `paintSketchBoxes(…, ".dn-empty")` in `drilldown.ts`; dashed border (empty-state affordance) kept as the single outline |
| `.dn-layer-pill`, `.dn-navbtn`, `.dn-chip`, `.dn-rec-list li`, `.dn-select`, `.dn-btn`, `.dn-drawer-close` | **CSS only** (unchanged) | Already single-system; pills/nav/chips never painted |
| `.dn-boot-progress` + `.dn-boot-stamp` | **CSS only** (unchanged) | Small boot UI; hand-drawn SVG dashed route already provides the hand feel — no Rough rectangle added |
| `.dn-legend-swatch` (1px), `.dn-legend-gradient` (1px), table `th`/`td` separators, `.dn-header` bottom rule | **CSS only** (unchanged) | Data encodings / structural rules, never sketch hosts |

### Files changed (all under `web/`)

- `src/style.css` — `.sketch-card` now radius/shadow only (no `border`);
  deleted `.sketch-tile` rule, absorbed into `.dn-metric`/`.dn-stat`;
  removed borders on `.dn-callout`, `.dn-minimap`, `.dn-drawer`
  (+ mobile `border-top`); updated comment to state the rule.
- `src/lib/sketch.ts` — `DEFAULT_TARGETS` now lists only the 8 large
  hosts (added `.dn-minimap`; removed `.dn-empty`, `.dn-metric`, `.dn-stat`);
  header comment documents the single-treatment rule.
- `src/components/whatif.ts` — `dn-metric sketch-tile` → `dn-metric`.
- `src/components/drilldown.ts` — `dn-stat sketch-tile` → `dn-stat`;
  removed the explicit `.dn-empty` sketch paint.
- `src/components/export-view.ts` — six `dn-stat sketch-tile` → `dn-stat`.
- `src/main.ts`, `src/components/map-view.ts` — no edits needed (they only
  attach `sketch-card` to large hosts; the class now carries no border).

## How no element has both (audit method)

Two independent audits:

1. **Code audit:** grepped every `border`/`border-radius` in `style.css`
   and every sketch host/paint call. Large-host rules now declare no
   `border`; `.sketch-card` declares no `border`; `DEFAULT_TARGETS` and all
   explicit `paintSketchBoxes` selectors touch only the 8 large hosts.
   `sketch-tile` has zero references left (`grep sketch-tile web/src` →
   no matches).
2. **Live computed-style audit (headless Chromium, per view):** for every
   large host, `getComputedStyle` border widths (all four sides) are `0px`
   **and** `:scope > svg.dn-sketch` exists; for every visible small tile,
   border width `> 0px` **and** no `svg.dn-sketch`. Runs for `map`,
   `whatif`, and `export` views (drawer + its stats/empty included on map).

## Skills loaded and how each shaped the result

Per `skills.json`: `task_kind: refine_existing`, `design_direction:
premium/editorial (sketch from Task 003)`, `target: web`, `stack:
vanilla`. Loaded `frontend-design` (baseline — kept the approved sketch
direction literally, no restyle), `design-taste-frontend` (component
discipline: single outline per elevation level, no stacked strokes),
`high-end-visual-design` (craft bar: removed the generic 1.5px grey
duplicates so only the hand-drawn line reads as intentional),
`impeccable` (removed the callout's >1px side stripe — replaced by the
amber background tint, per the absolute ban), `emil-design-eng` (kept
drawer curve, press feedback, and stagger untouched — this is a border
cleanup, not a motion change), `ui-ux-pro-max` (contrast/focus/responsive
checklist for the final pass), `web-design-guidelines` (final compliance:
`:focus-visible`, aria, reduced-motion, 390px). No motion/GSAP/Framer
skills (not triggered).

## Preservation

- **Palettes:** `src/lib/colors.ts` untouched; YlOrBr/Blues/RdBu/A–F
  + unknown grey preserved (legend ramps/grade swap re-verified live).
  Callout/graphic data text verbatim.
- **Accessibility:** `:focus-visible` outline untouched (focus indication,
  not decoration); text contrast unchanged; keyboard/Esc/aria unchanged;
  `prefers-reduced-motion` untouched (no motion added/removed).
- **Responsive:** ≤720px rules intact; drawer bottom sheet keeps the
  single Rough outline (no `border-top`); verified 390px no overflow.
- **Behavior:** identical — same data flow, layer toggling, drilldown,
  what-if interpolation, export ranking/CSV, row-select semantics.

## Build + live verification

- `npm run build` passes (`tsc --noEmit` + Vite, 21 modules).
- **Live check: 26/26 PASS, 0 console/page errors** (headless Chromium vs
  `vite preview` + real-data API; Task-003 suite + 6 new single-treatment
  audits: per-view large = sketch-only and small = CSS-only, all pass).
  Sketch counts confirm the new host set (map 2, what-if 3 incl. minimap,
  export 2). Screenshots inspected: drawer (single outer wobble, CSS stats,
  dashed empty), what-if (single wobble on controls/callout, CSS metric
  tiles), export (single wobble on table shell, row separators intact).
  No double lines or offsets on any view.

## Files changed

`web/src/style.css`, `web/src/lib/sketch.ts`, `web/src/components/whatif.ts`,
`web/src/components/drilldown.ts`, `web/src/components/export-view.ts`.
No new deps (Rough.js already present from Task 003), no edits outside
`web/`, no git. Completion written to
`agents/picasso/completions/fix-double-borders-004.md`.
