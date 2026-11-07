# Completion — Task 007: Navbar overhaul + playcards UX optimization

**Agent:** Picasso (frontend) · **Date:** 2026-11-07
**Status:** DONE

## Navbar blueprint (Part A)

The two stacked strips (brand header + separate nav row) are now **one
sticky bar** (`web/src/main.ts` header markup, `style.css` header/nav):

```
[bus][Title / tagline]   [Map explorer | What-if | Export]   [counts · gauge · Copy link]
   brand (left)            segmented group (center)            actions (right)
```

- **Brand left:** mark + title + shortened tagline
  ("Who's disconnected from opportunity?" — no wrap, no ellipsis).
  `.dn-header-inner` is now a 3-column grid (`auto 1fr auto`); ≤720px
  collapses to brand + actions on row 1, nav as a full-width segmented
  row 2 (44px targets, no overflow). The city-summary meta is hidden on
  mobile to prevent truncation (gauge + Copy link remain).
- **View tabs as a segmented control:** `.dn-nav` is one outlined pill
  group (`background: paper-2`, 1.5px ink-soft border, `shadow-paper`,
  `var(--r-pill)`) with 44px buttons, unmistakable ink active pill
  (`aria-current="page"` + visual), hover gated to
  `(hover:hover) and (pointer:fine)`, press `translateY(1px) scale(0.97)`
  140 ms `var(--ease-out)`. Keyboard order follows visual order
  (nav is a DOM-sibling between brand and actions).
- **Actions right:** summary + gauge + Copy link grouped with 44px Copy
  hit target and `aria-live` feedback (unchanged behavior).
- **Map controls belong to the view:** layer tabs + Before/After moved
  into one `.dn-map-controls` column (same paper surface, radius, lift
  shadow, Kalam 0.84rem pills, 44px targets — identical scale/curve to
  the navbar). Each group carries a small `AREA LAYER` / `BEFORE / AFTER`
  kicker label so the relationship reads at a glance. This also fixes
  the Task-006 overlap: the 8-pill bar previously ran under the centered
  Before/After toggle and truncated pills; stacking resolves it.
  Mobile: controls stack full-width under the bar; story/legend offsets
  unchanged.

Single-outline rule preserved (Task 004): navbar segmented group is
CSS-border-only (no Rough.js — small chrome); map-control boxes remain
Rough-only large hosts.

## Playcards (Part B)

### General (all cards)
- **Hit targets ≥ 44px:** nav pills, layer pills, BA buttons, `.dn-btn`
  (incl. secondary variant), Copy link, close ×s (story 30→44,
  tour 34→44, drawer 36→44), select (min-height 44), range slider
  (min-height 44). Tour dots stay decorative (`aria-hidden`).
- **Type scale:** kicker (0.72–0.74 uppercase muted) → title (Kalam
  1.0–1.15) → body (0.84–0.92 ink-soft) → detail (0.76 mono/muted).
  Off-scale labels normalized (`stat/metric-label` 0.78/0.80 → 0.76 +
  weight 600; `rec-pop` 0.78 → 0.76; legend ticks 0.68 → 0.72;
  metric hints now `min-height` to prevent tile-height jump).
- **Primary / secondary:** new `.dn-btn.is-secondary` (paper, ink text).
  Primary stays ink-filled: story CTA "See its report card", tour Next/
  Done, narrator Play, downloads. Secondary: narrator toggle/Back/Next,
  tour Skip/Back. Primary action never hidden by progressive disclosure
  (narrator, snapshot-empty, tour all reveal one step at a time).
- **Cursor:** `cursor:pointer` on pills/buttons/select/range; table rows
  already `cursor:pointer` (they select). Nothing hover-only: every
  affordance works by click/tap/keyboard.

### Per card
- **Story + narrator:** primary CTA vs secondary "Hear the trip";
  narrator Back/Next secondary, Play primary. Dialog contract now
  complete: `role="dialog"`, Esc closes, focus captured on open and
  **returned** on close (stored invoker).
- **Drilldown:** same dialog contract + focus-return on close
  (`returnFocus` stored on first open); anchor note + mascot kept;
  stat tiles tabular, CSS-only borders.
- **What-if:** metric tiles CSS-only with uniform 0.76 labels; select +
  slider now 44px; callout stays Rough-only with estimated hint text
  intact.
- **Export snapshot:** primary download buttons; empty state mascot +
  one-line instruction (primary action is the row click above).
- **Onboarding:** Skip/Back secondary, Next/Done primary; dots
  decorative; Esc/backdrop/arrows + focus-return already present.
- **States:** story-not-found, no-recommendations, corridor-not-found,
  snapshot-empty, boot error all consistent (dashed box + mascot +
  ink title + muted instruction — none color-alone). Data honesty
  unchanged (estimated labels visible on After/callout/legend).

## Skills used

Per `skills.json`: `task_kind: refine_existing`, `design_direction:
premium` (sketch), `target: web`, `stack: vanilla`. Loaded
`frontend-design` (plan first: 3-zone bar, stacked map controls, one
primary per card), `design-taste-frontend` (≥44px targets, full state
cycles, press feedback), `high-end-visual-design` (Segmented control as
the confident centerpiece; single-outline restraint), `impeccable`
(one primary per card; kept the Task-003 amber `border-left` accent on
rec rows as a deliberate, documented deviation from the side-stripe ban
to avoid restyling behavior-adjacent chrome), `emil-design-eng` +
`animate` (120–300 ms, `var(--ease-out)`/`--ease-drawer` only, hover
gating, reduced-motion untouched), `web-design-guidelines` (final pass:
focus, aria, 390px).

## Verification

- `npm run build` passes (`tsc --noEmit` + Vite, 27 modules).
- **43/43 live checks, 0 console/page errors** (headless Chromium vs
  `vite preview` + real-data API; full Task-003→006 suite, no
  regressions): navbar view switching + active/focus states, 8 layer
  pills, access overlays, story + narrator, drawer/Esc/scrim,
  what-if metrics + slider, export table/snapshot, deep-links,
  copy-link, tour (show/step/persist/hide), Before/After label + URL,
  pulse scaling + honest caption, header counts 1,545/40,813 + ring
  0.44, single-treatment audits (large sketch-only, incl. new
  `.dn-beforeafter`; small CSS-only), 390px no overflow.
- Screenshots inspected: desktop single-row bar + stacked labeled map
  controls (no overlap, no truncation); mobile collapsed bar + stacked
  controls.
- Palettes (YlOrBr/Blues/RdBu/A–F), a11y (44px targets, focus-return,
  aria, reduced-motion), ≤720px preserved. No edits outside `web/`,
  no new deps, no behavior/data changes.

## Files changed

`web/src/main.ts` (header/nav markup, map-controls wrapper, tagline),
`web/src/style.css` (navbar, segmented control, map controls, 44px
pass, type scale, secondary buttons, mobile collapse),
`web/src/components/story-panel.ts` (dialog contract, focus-return,
secondary buttons), `web/src/components/drilldown.ts`
(focus-return), `web/src/components/onboarding.ts` (secondary
buttons). Completion: `agents/picasso/completions/navbar-playcards-007.md`.
