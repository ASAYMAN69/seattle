# Task 009 — Navbar + map-controls redesign (fix the ass layout)

## Context

The SPA (`web/`) works but reads as assembled, not designed. The header
collides at desktop widths: brand (title + tagline) truncates, the nav
segmented control overlaps the city-summary counts, and the map controls
(Scenario + Area layer + Before/After) form a full-width wall of boxes that
covers most of the map. The story card is a permanent text wall. Root cause:
every task bolted another control on without an information architecture.
This is a **layout redesign pass** — same features, same behavior, same
palettes, same single-outline rule — with one job: the map stays the hero and
nothing overlaps at any width.

## Objective

Deliver a coherent navbar + map-controls layout system with the story card
demoted, verified by a programmatic overlap audit (not eyeballs).

## Part A — Navbar (single sticky bar + stat ribbon)

1. **Single sticky bar, three zones**: brand (mark + short title; the
   tagline goes — it is the only thing truncating and it earns nothing)
   | nav segmented control | actions (scenario is NOT in the bar — see Part B;
   actions = stat ribbon anchor + Copy link).
2. **Stat ribbon below the bar**: a slim single-line ticker replacing the
   current city-summary blob — "1,545 block groups · 40,813 in corridors ·
   122 F-grade · 22 high-need/low-access (need ≥0.40, gap <0)". No wrap,
   no count-up (moot motion — numbers must be readable, not animated),
   horizontal scroll if cramped. Every number real (already wired).
3. **Invariants**: segmented tabs keep `aria-current`, 44px targets,
   `--ease-out` 120–300ms, `:hover` gated to `(hover:hover) and
   (pointer:fine)`, full `prefers-reduced-motion` fallback. No overlap at
   widths 1024, 1280, 1366, 1600 (programmatic box-intersection audit
   must pass).

## Part B — Map controls (one cluster, not three islands)

1. **Single compact control card, top-left, max-width 380px** (never
   full-width on desktop), same paper/radius/shadow/type language as the
   navbar. Contents, top to bottom:
   - `AREA LAYER` kicker + 8 pills (industry 4 + access 4, current order).
   - A two-column row: `SCENARIO` (AM peak / Off-peak) | `BEFORE / AFTER`
     (Today / If recommendations ship). Both segmented pairs, 44px.
   - **Delta readout as a real stat**: "24 BGs · +8.3 pp max" as a
     mono chip line inside the card (not a footnote; real numbers from
     `computeGainsByGeoid`).
2. **Honesty banner** (off-peak) stays, but surface it inside/above the
   cluster as a compact line, not a full-width box.
3. The map must occupy ≥ 65% of the viewport width on desktop. Legend,
   zoom, story, drawer keep working; no control may cover the map hero.

## Part C — Story card demoted

1. **Collapsed by default**: bottom-left, 2-line preview — kicker +
   "Meet block group 530330305012" + one stat line
   ("1,505 people · 29.9% poverty · $20,885 income" — real fields).
   `role="dialog"`, Esc closes, focus-return, dismiss X (kept).
2. **Expand on click**: full narrative + narrator accordion + CTA reveal
   (existing content/behavior, one step at a time). Primary CTA stays
   "See its report card".
3. On ≤720px the preview is a bottom peek (≤ 25dvh, scrolls internally);
   expanded state is a bottom sheet (≤ 70dvh, scrolls).

## Part D — Playcard polish sweep

Apply the Part A/B type scale + 44px + primary/secondary discipline
across drilldown, what-if, export, tour (already started in 007 — finish
it here): kicker 0.72–0.74 → title Kalam 1.0–1.15 → body 0.84–0.92 →
detail 0.76 mono/muted. No element under 0.72rem except data ticks
(0.72 min). One primary per card, rest secondary.

## Scope

**IN:** `web/` only — `web/src/main.ts` (header/nav markup, tour mount
unchanged), `web/src/style.css` (biggest change: navbar, controls
cluster, story peek, ribbon, chips), `web/src/components/story-panel.ts`
(collapse/expand), `web/README.md` (layout note if chrome copy changes).
**OUT:** `api/`, `app/`, `scripts/`, `datanova/`, `data/`. No API changes,
no new endpoints, no behavior/data changes, no new dependencies. No git.

## Done when

- [ ] `npm run build` passes.
- [ ] **Overlap audit passes** at 1024×800, 1280×800, 1366×768, 390×844:
      programmatic rectangle-intersection check on
      header/nav/meta/controls/story/legend — zero overlaps, zero
      horizontal overflow, no truncation of controls.
- [ ] Navbar reads as one cohesive bar; stat ribbon is one line; tagline
      gone; no truncated text at any tested width.
- [ ] Map controls are a single ≤380px cluster; map ≥ 65% viewport width.
- [ ] Story card is a collapsed 2-line peek by default, expands with one
      action, Esc/focus-return intact.
- [ ] All 43 existing live checks still pass (tour, deep-links, access
      overlay, narrator, before/after halo + readout, tooltip,
      time-of-day, export, single-treatment audits).
- [ ] Accessibility, reduced-motion, ≤720px preserved.
- [ ] No edits outside `web/`.
- [ ] Completion written to `agents/picasso/completions/navbar-map-redesign-009.md`.
