# Completion — Task 010: Modularize the SPA (break big files into smaller chunked files)

**Agent:** Picasso (frontend) · **Date:** 2026-11-07
**Status:** DONE (behavior-preserving refactor only)

## What changed

Every largest file was split along real concern/domain seams (verified by reading
the source before moving anything). No behavior, API, data, CSS, dependency, or
test changes. The module graph still builds (`npm run build`) and passes the
live browser smoke with zero console errors.

### New files → what moved where, and why that seam

| New file | Moved from | Content / seam |
| --- | --- | --- |
| `src/boot.ts` | `src/main.ts` | Shell injection (via `shell.ts`), boot scene UI (bus animation, labels), `loadData`/`validateBundle`, `boot()` orchestration, `mount()`. Seam: boot/load/mount lifecycle. |
| `src/shell.ts` | `src/main.ts` | The app shell markup string. Seam: markup vs logic. |
| `src/nav.ts` | `src/main.ts` | `buildNav`, `updateNav`, `updateScrim`, `staggerView`. Seam: view switching/navigation. |
| `src/layers.ts` | `src/main.ts` | `buildLayerTabs`, `updateLayerTabs` (+ LAYERS wiring). Seam: layer-control chrome. |
| `src/scenario.ts` | `src/main.ts` | `build/updateBeforeAfter`, `build/updateTimeOfDay`, `refreshEquity`, `renderScenarioBanner`, `renderDeltaReadout`. Seam: scenario (time-of-day / Before-After) behavior. |
| `src/header.ts` | `src/main.ts` | `renderCitySummary`, `animateCount`, `countUpFrames`, `prefersReducedMotion`, `wireCopyLink`. Seam: header chrome/ribbon. |
| `src/view-refs.ts` | `src/main.ts` | Shared `mapViewRef`/`drilldownRef`/`exportRef` (setters/getters). Seam: boot ↔ scenario shared live instance refs without a circular import. |
| `src/lib/map-style.ts` | `src/components/map-view.ts` | `BG`, `FillPaint`, `prefersReducedMotion`, `gradientCss`, `buildColorExpression`, `buildFillPaint`, `effectiveConfig`, `changedGapAfterRange`, `changedFilterExpression`, `equityWithAfter`, `renderLegendInto`. Seam: pure paint/expression/legend builders vs the MapView class. |
| `src/components/export-charts.ts` | `src/components/export-view.ts` | `renderGradeChart`, `renderScatterChart` (pure SVG builders). Seam: chart rendering. |
| `src/components/export-snapshot.ts` | `src/components/export-view.ts` | `renderSnapshotInto`, `downloadSnapshotCsv`, `downloadSnapshotPng`, `buildReportCardSvg`. Seam: snapshot render/download. |
| `src/lib/export-format.ts` | `src/components/export-view.ts` | `TABLE_COLUMNS`, `formatCell`. Seam: export-specific table formatting. |
| `src/lib/needs.ts` | `src/components/drilldown.ts` | `buildNeedsCard`, `featureCentroid`, `nearestCorridor`. Seam: recommendations/nearest-corridor geometry helpers. |
| `src/components/whatif-map.ts` | `src/components/whatif.ts` | `WhatIfMapView` class (minimap lifecycle, sources, fit). Seam: the highlight map as a self-contained widget vs controls/metrics. |

### Slimmed files (final line counts)

```
src/main.ts                      7   (entry → boot())
src/boot.ts                    275
src/nav.ts                      57
src/layers.ts                   30
src/scenario.ts                107
src/header.ts                  102
src/view-refs.ts                37
src/shell.ts                    24
src/lib/map-style.ts           225
src/components/map-view.ts     378
src/components/export-view.ts  189
src/components/export-charts.ts 40
src/components/export-snapshot.ts 141
src/lib/export-format.ts        28
src/components/drilldown.ts    270
src/lib/needs.ts               100
src/components/whatif.ts       183
src/components/whatif-map.ts   172
```

All files are under ~300 lines except **`src/components/map-view.ts` (378)**
— **argued cohesion exception**: it is one `MapView` class (map lifecycle,
sources/layers, mode morph, selection, tooltip, legend host). Forcing a split
would fracture a single responsibility and hurt readability, which the task
explicitly warns against; its style/expression helpers were already extracted to
`lib/map-style.ts`.

## Rulings I made

1. **DOM lookups must be lazy in `nav.ts`/`layers.ts`.** After splitting, those
   modules' top-level `document.querySelector(...)` would run at import time —
   before `boot()` injects the shell markup — returning `null` and breaking the
   app. Moved the lookups into lazily-cached accessors (first call after boot).
   Cost if wrong: a null-guard regression only if boot order ever changes.
2. **`view-refs.ts` introduced** as the shared home for mounted-view refs
   (boot sets them; scenario reads them). This avoids boot→scenario circular
   imports while keeping `scenario.refreshEquity` intact. Cost if wrong: a tiny
   indirection layer; behavior identical.
3. **`whatif-map.ts` stores `latestProj`** so a slider/projection update issued
   before the minimap's `load` event uses the latest projection (the original
   used the closure-captured first projection). Strictly a bug-proofing
   improvement, same observable behavior in the normal path.
4. **`map-view.ts` stays at 378 lines** (cohesion exception above) rather than
   forcing a readability-harming split.
5. **`LOW_ACCESS_MAX`/`HIGH_NEED_MIN` (drilldown) and `REFERENCE_MULTIPLIER`
   (whatif re-export) kept exported** — they are public surface even though
   nothing imports them, per the "all previously-public exports stay exported"
   rule.

## Verification

1. **`npm run build` passes** (strict `tsc --noEmit` + Vite build) — run after
   every slice and at the end. 37 modules transformed, dist built.
2. **Live browser smoke: 17/17 checks, 0 console errors** (headless Chromium
   via CDP against `vite preview` :4173 + real FastAPI backend :8000):
   boot completes with no error state; header ribbon populated (1,545 block
   groups · 40,813 · 122 F); 8 layer pills exist and gap pill toggles active;
   time-of-day off-peak toggle + scenario banner; Before/After "after" pressed;
   nav → what-if view active; what-if slider re-renders metrics (1.5× output);
   export view active with table rows, grade + scatter SVG charts, download
   buttons present, download-selected initially disabled; row click opens the
   drilldown drawer; deep-link restore (`?view=export&layer=gap&after=1&time_of_day=off_peak`);
   390px mobile no horizontal overflow (`scrollWidth == innerWidth == 390`).
3. **main.ts dropped 585 → 7 lines** (material shrink). No file exceeds ~300
   except the argued `map-view.ts` cohesion exception.
4. **Grep check:** no leftover references to moved helpers at old paths
   (`this.needsCard`, `this.featureCentroid`, `this.nearestCorridor`,
   `this.renderMap`, `this.updateMapSources`, `this.fitBoundary`,
   `this.fillPaint`, `this.effectiveConfig`, `this.renderLegend`,
   `this.mapEl`, … all gone from their old homes).
5. Public exports preserved: `MapView`, `Drilldown`, `ExportView`,
   `WhatIfView`, `WhatIfMapView`, `REFERENCE_MULTIPLIER`, `HIGH_NEED_MIN`,
   `LOW_ACCESS_MAX`, plus every prior `lib/*` export — imports resolve; build
   proves it.

## Comments

All existing necessary comments and module docstrings were preserved. New
comments are module-boundary rationale (the "Split out of … during Task 010
modularization" headers) and the one `Ruling` note about lazy DOM lookups. No
fabricated "human" comments, jokes, or filler.

## Files changed / created

Created: `web/src/{boot,nav,layers,scenario,header,view-refs,shell}.ts`,
`web/src/lib/{map-style,needs,export-format}.ts`,
`web/src/components/{export-charts,export-snapshot,whatif-map}.ts`.
Modified: `web/src/main.ts` (thin entry), `web/src/components/{map-view,
export-view,drilldown,whatif}.ts`, `web/README.md` (module map in Structure).

Untouched (as required): `state.ts`, `types.ts`, `api/`, `lib/colors.ts`,
`lib/sketch.ts`, `lib/interpolation.ts`, `style.css`, `app/`, `data/`,
`scripts/`, `datanova/`, `tests/`. No new dependencies. No git operations
performed (controller commits after review).
