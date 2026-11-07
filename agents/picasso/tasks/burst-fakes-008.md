# Task 008 — Burst the fake bubbles: replace or delete

## Context

The user audit-found that several visible UI elements feel fake/hollow:
(1) Before/After toggle appears to do nothing, (2) the "0.44 mean access"
ring at the top looks like a hardcoded decoration, (3) "Top recommendations"
is empty on ~98.4% of clicks, (4) time-of-day is built in the backend but has
no frontend UI (unreachable), (5) the "isochrone pulse" is a decorative
circle. The user instruction: **figure out every empty/placeholder space,
burst them — either replace with something real, or delete.**

This is a frontend-only task except where noted. All data comes from the
existing API (which already ships time-of-day support — no backend change
needed unless you hit a contract wall; if so, stop and note it).

Read first: `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`,
this task, and the current SPA (`web/src` — main.ts, state.ts, components/*,
lib/before-after.ts, lib/narrator.ts, lib/colors.ts).

## The audit (ground truth from the main agent, verified against live API)

1. **Before/After ("no change"):** gains are 0.010–0.083 (max Route 915). Gap
   color domain −0.39–0.79. Shift ≈ 2% of the range, on only 25/1,545
   polygons (1.6%). Arithmetically correct; visually invisible. Verdict:
   **REPLACE the presentation** — make the (real, small) shift perceivable
   without exaggerating it. Required:
   - Highlight the changed polygons only (strong halo/outline of the 25
     covered BGs in After mode; dim the rest). The user must *see* which
     areas move.
   - A delta readout that names the magnitude: "25 block groups shift ·
     max +8.3 pp · most see no change" (computed from `computeGainsByGeoid`
     + live sensitivity — real numbers).
   - Rescale the After legend domain to a tighter range so the shift reads
     (e.g. gap_after range), honestly labeled "estimated".
   - Clicking a changed BG in After mode shows its +gain in the drilldown.
   - Alternative: flyTo/zoom to the densest corridor on first After toggle.
     (Pick halo + readout; zoom is optional flair, not required.)
2. **Header gauge 0.44 + city counts:** `mean_access_overall` 0.4358 is real
   (report_cards summary) but context-free ("0.44 / mean access" on a lonely
   ring). Verdict: **DELETE the ring**, REPLACE header meta with contextual
   counts a judge instantly gets: F-grade block groups (122), high-need-low-
   access count (compute from equity features — define a threshold and label
   it), and keep the 1,545 / 40,813 counts with plain labels. Every number
   must be explainable in one sentence.
3. **Top recommendations empty (98.4% of clicks):** only 25 BGs are in any
   recommendation's `geoids`. Verdict: **REPLACE the empty card** — when a BG
   has no corridor, show a grade-driven "What this area needs" card built
   entirely from that BG's real grades + stats (e.g. Jobs F → "Improving
   job access matters most here"), plus the nearest corridor recommendation
   by distance (you have corridor geometries — use the nearest centroid; or
   if distance math is too much, list the largest corridors in the same
   direction... no — use nearest centroid, it's ~15 lines). Never render a
   bare empty card, and never fabricate a corridor that doesn't serve the BG.
4. **Time-of-day unreachable:** `web/src` has zero references to
   `time_of_day`; the API supports it. Verdict: **WIRE the toggle.** Add a
   small AM-peak/Off-peak segmented control (navbar or map-controls area)
   that appends `?time_of_day=` to `/api/equity`, `/api/top-underserved`,
   `/api/block-group/{geoid}`, and shows the scenario descriptor from
   `GET /api/scenarios` as an honest banner ("approximate what-if, not a
   fresh routed network" for off-peak). Keep AM peak default.
5. **Isochrone pulse:** decorative Rough.js circle honestly labeled
   "Illustrative coverage — sketch, not a true isochrone." Verdict:
   **DELETE the circle.** Replace with a hover/click tooltip on the map that
   explains the active layer's score in plain words ("Healthcare access 0.00 —
   almost nothing within 30 min by this model"). No fake geography.

Also: the boot labels ("Warming up the bus…") and city count-up are
decorative motion, not data claims — keep them; they're not bubbles.

## Scope

**IN:** `web/` only — `web/src/state.ts`, `web/src/lib/url.ts` (deep-link
`time_of_day` if you add state), `web/src/api/client.ts`, `web/src/main.ts`
(header, map-controls, banner), `web/src/components/map-view.ts`,
`web/src/components/drilldown.ts`, `web/src/components/story-panel.ts`,
`web/src/components/whatif.ts`, `web/src/lib/colors.ts`,
`web/src/lib/before-after.ts`, `web/src/lib/narrator.ts` (observable only if
empty-card text needs alignment), `web/src/style.css`, `web/README.md`.

**OUT:** `api/`, `app/`, `scripts/`, `datanova/`, `data/`. No backend edits.
No new data, no new endpoints, no new deps, no git.

## Guidelines

1. Read rulebook, context, and current SPA first.
2. Run your skill router; classify `task_kind: refine_existing`,
   `design_direction: premium` (sketch), `target: web`, `stack: vanilla`.
3. **Zero-broken behavior:** tour, deep-links, access overlay, narrator,
   before/after, pulse-removal menu, and export keep working. The
   single-outline rule (Task 004) and palettes stay.
4. Every surviving number must be traceable to a prepared field or a named
   computation. If a "count" needs a threshold (e.g. "high-need-low-access"),
   define it in code (single constant) and label it in the UI.
5. `prefers-reduced-motion`: all new motion has instant fallbacks.
6. Self-verify live: `npm run build` + browser checks for each verdict item
   (before/after halo + delta readout visible, header counts explainable,
   no empty rec card, time-of-day toggle switches layers live, pulse gone and
   tooltip present, deep-link `time_of_day` restores). 390px mobile clean,
   zero console errors.

## Deliverables

- Updated `web/` implementing all five verdicts (or a documented, reasoned
  deviation per item).
- Completion file: per-item verdict (replace/delete), what you replaced it
  with and where the numbers come from, verification results.

## Done when

- [ ] `npm run build` passes.
- [ ] Before/After: changed polygons visibly highlighted; delta readout shows
      real shift magnitude; After legend rescaled honestly.
- [ ] 0.44 ring deleted; header counts all contextual and explainable.
- [ ] No drilldown ever shows a bare empty rec card — grade-driven fallback
      + nearest corridor replaces it.
- [ ] Time-of-day toggle wired: AM peak default; off-peak recolors layers and
      shows the /api/scenarios honesty banner.
- [ ] Isochrone pulse circle deleted; score tooltip replaces it.
- [ ] No surviving number lacks a source; no behavior regression.
- [ ] Accessibility + reduced-motion + ≤720px preserved.
- [ ] No edits outside `web/`.
- [ ] Completion written to `agents/picasso/completions/burst-fakes-008.md`.
