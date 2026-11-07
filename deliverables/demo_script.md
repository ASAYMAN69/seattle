# Demo Script — 90-Second Judge Flow

> Live demo: **http://45.76.2.228:8080** (public, no login, real data)
> Companion deck: `deliverables/seattle_pitch.pptx`
> Screenshots: `deliverables/screenshot_*.png`

## Hook (0–10s)
- "Who in Seattle is disconnected from opportunity?" — that's the question this tool answers.
- The map loads on the **Equity Gap** layer: red = high need + low access.

## Map (10–40s)
- Point to the red South-Seattle corridor. "These are places with high need — poverty, zero-car households — but weak transit access. That's the gap."
- Click a red block group → the **Equity Report Card** slides open: letter grades for Jobs / Healthcare / Schools / Food, plus population, poverty, zero-car share, median income.
- "A school report card — for transit equity."

## What-if (40–70s)
- Switch to the **What-if** tab. Pick a recommended corridor (e.g. Route 160).
- Drag the **frequency slider** 1.0× → 3.0×.
- Watch the metrics: affected residents, newly benefiting residents, estimated wait saving, access gain.
- "A transit planner can literally ask: what happens if we run this route twice as often? The answer pops out — computed from real schedules."

## Before / After (70–85s)
- Back on the map, toggle the **Before/After** control → "If recommendations ship".
- The 25 covered block groups get a halo and the gap layer visibly shifts; the readout says the max gain.
- "All 14 recommendations together touch ~40,813 residents. This is what service changes would actually do."

## Export & close (85–90s)
- Open **Export**: the top-25 underserved table is right there with CSV download.
- Close: "Real GTFS + Census + job data. Reproducible pipeline. And the report card is a format that makes equity concrete — not a number in a spreadsheet, but a grade a community can act on."

## Judges' likely questions — quick answers
- **Why Seattle?** Real documented need + clean free data (GTFS, ACS, LODES, OSM). The pipeline generalizes to any region with GTFS + census data.
- **Is the routing real?** Yes — real GTFS feeds parsed into a graph, Dijkstra access by category thresholds. But it's a representational network, not live routing; off-peak is a documented approximation.
- **How is a grade set?** Access − Need residual quartiles → A–F per dimension.
- **What's the estimate honesty?** All numbers are prepared data; the what-if/before-after use the documented sensitivity model and are labeled "estimated".

## Tech facts (for follow-up)
- FastAPI backend serves the SPA + `/api` same-origin (one process, one port).
- SPA: Vite + TypeScript + MapLibre GL. Sketch-style chrome, colorblind-safe palettes.
- 153 backend tests pass. Lighthouse: accessibility 100, SEO 91.
