# Task 007 — Navbar overhaul + playcards UX optimization

## Context

The SPA (`web/`) now has the wow moments + extra features committed. The user
flags two UX problem areas for a focused pass — this is a **visual/UX
optimization**, not a behavior rewrite (data, API, views stay identical):

1. **Navbar** (`web/src/main.ts` header + `.dn-nav` strip in
   `web/src/style.css`) is two stacked strips: header (brand + tagline +
   city-summary + gauge + Copy link) on top, then a separate nav row
   (Map explorer / What-if / Export). It eats vertical space, hierarchy is flat,
   and the layer tabs + Before/After toggle float separately over the map with
   no clear relationship to the nav.
2. **Playcards** — the interactive cards users "play with" (story panel +
   "Hear the trip" narrator, drilldown report card, what-if metric tiles,
   export snapshot card, onboarding dialog) — lack consistent affordances:
   unclear what's clickable, small hit targets, hover-dependent cues, and
   visual repetition that doesn't guide the eye.

Read first: `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`,
this task, and the current SPA (`web/src/main.ts`, `web/src/style.css`,
components incl. `story-panel.ts`, `drilldown.ts`, `whatif.ts`, `export-view.ts`,
`onboarding.ts`, `map-view.ts`).

## Objective

Deliver a **cohesive, optimized navbar** and **UX-friendly playcards** that keep
the approved sketch identity, the colorblind-safe palettes, and every existing
behavior intact.

## Part A — Navbar (optimize, don't restyle from scratch)

1. **Integrate header + nav into one cohesive sticky bar** (single row where
   possible; two rows only on narrow widths). Goals:
   - Brand left (mark + title + tagline trimmed so it never truncates awkwardly).
   - View tabs (Map explorer / What-if / Export) as a proper **segmented
     control** integrated into the bar, with clear active + hover + focus states.
   - Header actions (city-summary, equity gauge, Copy link) grouped logically
     on the right; each with proper spacing, hit targets ≥ 44px, and clear
     visual separation.
2. **Relationship between nav and map controls:** the layer pills
   (`.dn-layer-tabs`, 8 pills) and Before/After toggle
   (`.dn-beforeafter`) must read as *map controls belonging to the current
   view*, not floating islands. Align them visually with the navbar's language
   (same type scale, same motion curve, consistent sketch only where it earns).
3. **Affordances:** active state must be unmistakable (aria-current + visual);
   hover is a bonus, never required. Keyboard tab order follows visual order.
4. **Mobile ≤720px:** navbar collapses cleanly (stacked; tabs full-width 44px
   targets; no horizontal overflow; no truncation of controls).
5. **Motion:** keep Task 003/006's curves (`--ease-out`, `--ease-drawer`) and
   120–300 ms durations; hover wobble gated to `(hover:hover) and
   (pointer:fine)`; full `prefers-reduced-motion` fallback.

## Part B — Playcards (make them playable, not just present)

Targets: story panel (`.dn-story*` + narrator accordion), drilldown report
card (drawer), what-if metric tiles + controls + callout + minimap, export
snapshot card, onboarding dialog. For each, apply:

1. **Clear affordance:** the user can tell at a glance what's clickable vs
   informational. Link-styled interactive text, visible press feedback
   (`scale(0.97)`), pointer cursor only on true affordances.
2. **Hit targets ≥ 44px** for all interactive elements (toggles, buttons, dots,
   step controls, close); metric tiles keep tabular numerals.
3. **Type hierarchy:** kicker → title → body → detail size/weight scale applied
   consistently (no ad-hoc 10px labels scattered across cards).
4. **Progressive disclosure:** narrator accordion, "See its report card",
   snapshot-empty, and tour steps must not dump everything at once — reveal
   one thing at a time without hiding the primary action.
5. **States:** loading / empty / error states (story-not-found, no
   recommendations, corridor-not-found, snapshot-empty, boot error) all
   consistent in sketch + mascot language; none rely on color alone.
6. **Drawer & dialog pattern:** story/drilldown/onboarding follow one dialog
   contract (role, Esc-to-close, scrim, focus management, focus-return).
7. **Data honesty preserved:** no invented numbers; "estimated"/"approximate"
   labels for Before/After/off-peak stay visible where shown.

## Scope

**IN:** `web/` only — `web/src/main.ts` (header/nav markup), `web/src/style.css`
(biggest change), components listed above, `web/index.html` if chrome copy
needs it, `web/README.md` if structure changes.

**OUT:** `api/`, `app/`, `scripts/`, `datanova/`, `data/`. No API changes, no
new endpoints, no behavior/data changes, no new dependencies (prefer zero).
No git.

## Guidelines

1. Read rulebook, context, and current SPA first.
2. Run your skill router; classify `task_kind: refine_existing`,
   `design_direction: premium` (sketch), `target: web`, `stack: vanilla`.
3. Load and apply the matching set — `frontend-design` (baseline),
   `design-taste-frontend`, `high-end-visual-design`, `impeccable`,
   `emil-design-eng`, `animate`, `web-design-guidelines` (final pass).
4. Keep: sketch identity, palettes (YlOrBr/Blues/RdBu/A–F), single-outline
   treatment (Task 004 rule — large sketch-only / small CSS-only), tour +
   deep-links + owl features untouched in behavior.
5. Self-verify live: `npm run build` passes; browser checks for navbar
   (all view switching, active/focus states, mobile collapse), playcards
   (story + narrator, drawer, what-if metrics, export snapshot, onboarding,
   empty states, Esc/focus), deep-link restore, before/after, pulse.
   390px no overflow; zero console errors.

## Deliverables

- Updated `web/` with the optimized navbar + playcards.
- Completion file: what you changed (navbar blueprint, per-card UX changes),
  skills used, verification results.

## Done when

- [ ] `npm run build` passes.
- [ ] Navbar reads as one cohesive bar; view tabs are an unmistakable segmented
      control with clear active/focus states; actions grouped readably.
- [ ] Layer tabs + Before/After read as map controls; consistent scale/curve.
- [ ] Every playcard has clear affordance, ≥44px interactive targets, consistent
      type hierarchy, progressive disclosure, and honest labels.
- [ ] Dialog/empty/loading/error states consistent across all cards.
- [ ] No behavior regression (tour, deep-links, before/after, pulse, narrator,
      time-of-day API path, access overlay all still work).
- [ ] Accessibility, reduced-motion, ≤720px preserved.
- [ ] No edits outside `web/`.
- [ ] Completion written to `agents/picasso/completions/navbar-playcards-007.md`.
