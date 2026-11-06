# Task 004 — Fix overlapping double borders (sketch overlay vs CSS border)

## Context

Task 003's sketch reskin introduced a visual defect. The chrome now draws **two
border systems on the same elements**:

1. The CSS border system: `border: 1.5px solid var(--line-soft)` (plus the
   `--r-a`/`--r-b` irregular-radius kit) applied to cards, pills, drawer,
   callouts, legend, stats/metrics, table shell, etc. in `src/style.css`.
2. The Rough.js sketch overlay: `src/lib/sketch.ts` paints a seeded wobbly SVG
   rectangle on top of the same elements (layer-tabs, legend, what-if controls/
   callout/minimap, metrics/stats, table shell + snapshot, drawer, empty states).

The result: a wobbly sketch line **and** a plain CSS border render stacked on the
same piece — they overlap and look messy/ugly. The user has called this out and
wants it fixed.

## Objective

Make the border treatment **singular and coherent**: remove the double-stroke
overlap. Every element should get exactly one visible outline treatment — either
the hand-drawn Rough.js sketch line or the CSS border, never both.

## Scope

**IN:** `web/src/style.css`, `web/src/lib/sketch.ts`, and any component that
configures sketch host elements (`web/src/components/*`, `web/src/main.ts`) —
only insofar as needed to implement the single-treatment rule.

**OUT:** Everything else. No behavior/data/API changes, no new deps, no changes
outside `web/`, no git.

## Guidelines

1. Decide a **consistent rule** per element size/role (this is a design call —
   make it tasteful and uniform):
   - Large chrome (legend, drawer, callout, table shell, what-if minimap/controls,
     boot scene) → keep the **Rough.js hand-drawn stroke** and remove the CSS
     border on those elements (the sketch line is the aesthetic here).
   - Small tiles / dense UI (stats/metrics, pills, nav buttons, small chips) →
     keep the **CSS border** treatment and do **not** paint a Rough.js sketch on
     them (the completion itself noted Rough.js on small tiles read as busy).
   - Ensure the sketch overlay's geometry aligns with the element's box (no
     offset/no double edge) where it is kept.
2. There must be **zero elements** with both a CSS border and a Rough.js sketch
   outline. Audit the full set of sketch hosts in `src/lib/sketch.ts` and every
   `border`/`border-radius` in `src/style.css` for the chrome classes, and make
   them mutually exclusive per element.
3. Keep the visual spirit of Task 003 (hand-drawn, warm, cute-but-neutral). This
   is a cleanup, not a restyle.
4. Preserve: colorblind-safe analysis palettes, accessibility (focus-visible,
   contrast, reduced-motion), responsive ≤720px, and build green.
5. Verify: `npm run build` passes; live-browser check that the main chrome pieces
   (legend, drawer, callout, table, minimap, boot) show exactly one clean outline
   and nothing overlaps; no console errors; mobile 390px clean.

## Deliverables

- Updated `web/` implementing the single-treatment rule.
- Completion file: the rule you chose, exactly which elements now use sketch vs
  CSS border, how you verified no element has both, build + live results.

## Done when

- [ ] `npm run build` passes.
- [ ] No element renders both a CSS border and a Rough.js sketch outline.
- [ ] Large chrome keeps the hand-drawn sketch (cleaned, aligned).
- [ ] Small tiles use the CSS border treatment only.
- [ ] No visual overlap / double lines on any view (verified live).
- [ ] Palettes, a11y, reduced-motion, responsive intact.
- [ ] No edits outside `web/`.
- [ ] Completion written to `agents/picasso/completions/fix-double-borders-004.md`.
