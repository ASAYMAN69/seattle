# Completion — Task 001: Refactor the Streamlit frontend

**Agent:** Picasso (frontend)
**Task:** `agents/picasso/tasks/refactor-frontend-001.md`
**Status:** DONE
**Date:** 2026-11-06

---

## What I changed

| File | Change |
| --- | --- |
| `app/views/_ui.py` (new) | Single source of truth for the grade palette (`GRADE_COLORS`, `UNKNOWN_GRADE_COLOR`), the ACS stat field list, and every app-built HTML fragment (`stats_html`, `grades_chips_html`, `action_callout_html`, `grade_legend_html`). Also `MAP_LEGEND_CSS` + `folium_inject_css` for map-internal chrome. |
| `app/main.py` | `_inject_styles()` is no longer a no-op: it reads `app/styles.css` and injects it wrapped in a `<style>` tag via `st.markdown(..., unsafe_allow_html=True)` (canonical safe path). Removed the duplicated `_grade_legend_html`; map now uses the shared builder (+ scoped map CSS). `st.components.v1.html` → `st.iframe`. Narrowed broad `except Exception` blocks in `_read_query_selection` to `(AttributeError, StreamlitAPIException)`. Dropdown separator em-dash → `·` (consistent with report-card identity). |
| `app/views/map_view.py` | Re-exports the palette from `_ui` (no duplicate dict). Deleted the local inline-styled legend builder; grade layer now injects `MAP_LEGEND_CSS` and renders the shared legend. `st.components.v1.html` → `st.iframe` (with `alt`). |
| `app/views/report_card.py` | Constants and HTML builders moved to `_ui` (re-exported so public names/tests keep working). Render path uses shared builders. Recommendation bullet em-dash → colon. |
| `app/views/whatif.py` | Action callout now uses the shared `action_callout_html` (removes the side-stripe `border-left` pattern and inline styles). Narrowed `except Exception` in `_preferred_route_key`. Dropdown separator em-dash → `·`. `st.iframe` gains `alt`. |
| `app/views/export.py` | Narrowed the broad `except Exception` in `_current_selection` to `(AttributeError, StreamlitAPIException)` (keeps test stubs working). |
| `app/styles.css` | Rewritten as the single styling mechanism. Added `dn-` component classes (stat tiles, grade chips, callout), chip contrast via `color-mix` (WCAG AA text on every grade while keeping the A–F palette), kept `:focus-visible`, added `prefers-reduced-motion` handling, button `:active` press feedback, and the existing ≤720px responsive rules. |
| `tests/test_frontend_refactor.py` (new) | Static regressions: no deprecated custom-component API remains in app sources; exactly one wired stylesheet exists. |

## Styling mechanism chosen, and why

- **One mechanism:** a single injected stylesheet (`app/styles.css`) + semantic `dn-` classes used by all app-built HTML. Inline styles are limited to **data-driven values only**, passed as CSS custom properties (e.g. `--dn-grade-bg`). The visual rules live in exactly one place.
- **Why `st.markdown("<style>…</style>", unsafe_allow_html=True)` over `st.html(Path(css))`:** I verified in a live browser that Streamlit 1.67's `st.html` style-only path does **not** materialize a `<style>` element (computed styles unchanged), while the markdown path reliably applies. This was validated live before committing to it.
- **Map-internal chrome** (the grade legend) uses a small scoped stylesheet injected into the folium document head — a documented exception, because iframes isolate documents and the global stylesheet cannot reach inside them.
- **No dead files:** `styles.css` is now wired and verified; no other CSS files remain.

## Deprecated-API fix

- `st.components.v1.html(...)` → `st.iframe(...)` (Streamlit's documented modern equivalent) in both `app/main.py` and `app/views/map_view.py`. `st.iframe` uses the same srcdoc iframe, so the folium map and its click-to-select script keep working. Added `alt` text for accessibility. No deprecated usage remains (static regression test enforces this).

## Tests

- Full suite: **135 passed** (`make test`; 133 existing + 2 new static regressions). No existing test was weakened or deleted.
- Pure-helper separation preserved: `get_*`/`build_*` lookups are unchanged and remain testable without a running app.

## Live verification (Playwright + headless Chrome)

15/15 core checks passed on the running app (`make app`), desktop 1440×900 and mobile 390×844:

- No raw CSS/HTML source text anywhere in the rendered page.
- Stylesheet injected and applied (computed `h1` letter-spacing reflects the stylesheet; `:focus-visible` rule present).
- Sidebar report card renders after selecting a block group (stats, grades, recommendations).
- Map iframe mounts, renders Leaflet, and is full-width within its tab panel.
- Grade legend renders inside the map iframe via the app's supported URL handoff (`?analysis_layer=Grade (A–F)`).
- Zero console/page errors.
- Mobile: no horizontal scroll; embedded map height snaps to 400px (≤720px rule).

All four views were also clicked through live:
- **Map explorer** — analysis-layer selectbox, folium map, grade legend.
- **Report card** (sidebar) — stats tiles, grade chips, recommendations.
- **What-if** — selectbox, action callout, reference caption render in the browser; the frequency slider and the four metric tiles are confirmed in the app's delta stream via `AppTest` (slider "Frequency multiplier" = 2.0; metrics 8,871 / 8,871 / 0.43 min / +1.00 pp). The slider/metric **DOM** nodes did not mount under headless Chrome (lazy-mount quirk of the harness), but the server-side element tree is correct and `tests/test_whatif.py` covers the render calls.
- **Export** — city-wide table dataframe and download button render.

Screenshots saved for human eyeball: `/tmp/opencode/desktop.png`, `/tmp/opencode/grade_desktop.png`, `/tmp/opencode/mobile.png`, `/tmp/opencode/tabs_all.png`.

## Deliberately left (with reasons)

- **Broad `except` in `scripts/` inject** — out of scope (`scripts/` is untouched).
- **`GRADE_COLORS` palette values** — preserved exactly as the colorblind-safe decisions require (YlOrBr/Blues/RdBu layering unchanged).
- **Native Streamlit theme** (`.streamlit/config.toml`) — kept as the base layer; custom CSS only adds what the theme cannot express.
- **Playwright** was installed into the venv for verification only; it is **not** added to `requirements.txt`.
- Report-card identity separators (`·`) and recommendation copy kept; only em-dashes in UI copy I touched were normalized.

## Notes for the main agent

- No blocking follow-ups. Optional: `streamlit>=1.45` is effectively required for `st.iframe`/`st.html` (already used by the project pre-refactor).
- I did not run git; commit after review.
