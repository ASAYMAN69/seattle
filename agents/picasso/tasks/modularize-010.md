# Task 010 — Modularize the SPA (break big files into smaller chunked files)

## Context

The user wants the codebase modularized: break the big frontend files into
smaller, focused modules. This is a **behavior-preserving refactor only** —
no feature changes, no data/API changes, no CSS changes, no new deps. The
split must follow real seams (concern/domain), not arbitrary line counts.

Read first: `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`,
this task, and the current SPA (`web/src`). Prefer reading the files before
moving any code.

## Current structure (line counts)

```
web/src/
  main.ts                        585   (boot, nav, layer tabs, time-of-day,
                                        scenario banner, city summary, count-up,
                                        mount, delta readout)
  state.ts                        64
  types.ts                       193
  api/client.ts                  141
  lib/  colors 205 · story 137 · sketch 128 · interpolation 106 · url 103
        narrator 98 · mascot 69 · countup 65 · before-after 54 · format 42 · csv 26
  components/  map-view 547 · export-view 376 · drilldown 356 · whatif 311
               story-panel 258 · onboarding 161
```

## Objective

Reduce the largest files to focused modules, each under ~250–300 lines where
possible, without changing any behavior. All existing imports must resolve;
the bundle must build; all live behavior must be unchanged.

## Suggested seams (verify by reading; adjust if a better seam exists)

1. **`main.ts` (585)** → split by concern:
   - `src/boot.ts` — boot flow, loadData, validateBundle, mount (or keep
     mount in main and only extract helpers — your call, but main.ts must
     shrink materially).
   - `src/nav.ts` — buildNav/updateNav (view switching) or fold into state.
   - `src/layers.ts` — buildLayerTabs/updateLayerTabs + the LAYERS wiring.
   - `src/scenario.ts` — time-of-day toggle + scenario banner + refreshEquity
     + delta readout (the Before/After readout logic).
   - `src/header.ts` — city summary, count-up animation (move `animateCount`,
     `countUpFrames`, `prefersReducedMotion`), gauge (deleted — remove dead
     code if any), copy-link wiring.
2. **`components/map-view.ts` (547)** → split:
   - `components/map-view.ts` — the MapView class (map lifecycle, layers,
     mode, selection, tooltip).
   - `lib/map-style.ts` — `buildColorExpression`, `gradientCss`,
     `prefersReducedMotion`, `MISSING_FILL`-adjacent helpers, fill/legend
     builders used by the class. (Keep any private helpers that only MapView
     uses as module functions in this new file; export for the class.)
   - If `showPulse`/`paintPulseCircle` still exist in any form, they were
     deleted in Task 008 — do NOT reintroduce.
3. **`components/export-view.ts` (376)** → split:
   - `components/export-view.ts` — the ExportView shell (table render, row
     selection, download orchestration).
   - `components/export-charts.ts` — `renderGradeChart` + `renderScatterChart`
     (pure SVG builders) and the chart card layout.
   - `components/export-snapshot.ts` — snapshot render + CSV/PNG download
     helpers + `buildReportCardSvg`.
   - `lib/export-format.ts` — `formatCell` + column helpers (if they are
     export-specific).
4. **`components/drilldown.ts` (356)** → split if a clean seam exists (e.g.
   stats tiles vs grades vs recommendations/nearest-corridor helpers). If the
   class coheres, it's acceptable to leave it as one file if it stays under
   ~300 lines — do not force a split that hurts readability.
5. **`components/whatif.ts` (311)** — same logic: split only if a natural
   seam exists (e.g. model/interpolation already lives in `lib/interpolation.ts`).
6. **Comments:** the user (via the main agent) agreed to **honest, useful**
   comments only — module-boundary rationale, links to `context/decisions.md`
   for documented deviations, real TODOs tied to actual open items. **Never**
   add fake "human" comments, jokes, or filler. Preserve all existing
   necessary comments. Do not strip the module docstrings.

## Rules (hard)

- No behavior changes. No class/function signature change that breaks a
  caller; if you must move a symbol, update every importer.
- No changes to `api/`, `app/`, `scripts/`, `data/`, `datanova/`, `state.ts`
  (unless a tiny import fix), `types.ts`, or `style.css`.
- Keep the single-outline sketch rule and palettes as-is (they live in
  `lib/sketch.ts` + `lib/colors.ts` — do not churn them).
- No new dependencies. No git operations.
- All `export`ed symbols that were already public must stay exported
  (from somewhere) so imports resolve.

## Verification (required)

1. `npm run build` passes (strict `tsc --noEmit` + vite build).
2. Live browser smoke (headless Chromium against `vite preview` + backend):
   map layers toggle, click→drilldown, what-if slider, export table + charts
   + downloads present, time-of-day toggle, Before/After halo, header ribbon,
   deep-links, 390px mobile no overflow, zero console errors.
3. Confirm main.ts dropped materially in size and no file exceeds ~300 lines
   (except where you argue it coheres).
4. Grep check: no leftover references to moved helpers at old paths.

## Deliverables

- `web/src/` reorganized with the new modules.
- Completion file listing: every new file, what moved where, why that seam,
  and the verification results.

## Done when

- [ ] No file is a monolith anymore (main.ts and map-view.ts split).
- [ ] `npm run build` passes.
- [ ] Live browser checks pass (no regression).
- [ ] Existing comments preserved; no fabricated comments added.
- [ ] No edits outside `web/src/` + `web/README.md` (if you update the
      module map there).
- [ ] Completion written to `agents/picasso/completions/modularize-010.md`.
