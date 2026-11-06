# Task 001 — Refactor the Streamlit frontend

## Context

The Seattle Transit Equity Index Streamlit app (`app/`) is functionally complete (Tasks 3.1–3.4) and passes 133 tests. But the frontend has accumulated structural debt:

- Scattered inline HTML strings built in Python (`report_card._stats_html`/`_grades_chips_html`, `whatif._action_callout_html`, `map_view._grade_legend_html`), making styling hard to maintain.
- `app/styles.css` exists but is **dead** — `_inject_styles()` in `app/main.py` is a no-op (a prior bug made CSS source text leak into the page; the fix removed injection entirely).
- Deprecated `st.components.v1.html(...)` used in `app/views/map_view.py`.
- Known deferred minors (see `context/decisions.md`): CSS structural best-effort (verify ≤720px live), broad `except` blocks in `_current_selection`/scripts inject.

You are given latitude to decide *how* to refactor. The objective and guardrails are below.

## Objective

Refactor the frontend for **maintainability, consistency, and visual polish** while keeping behavior identical and the test suite green. Deliver a coherent styling story (one mechanism, not three), remove the inline-HTML sprawl where it does not earn its place, fix the deprecated API, and verify responsive/accessibility behavior.

## Scope

**IN:**
- `app/main.py` (routing, styling injection mechanism, selection plumbing)
- `app/views/*` (map_view, report_card, whatif, export)
- `app/styles.css` and `.streamlit/config.toml` (theme)
- `app/data_io.py` only if a *presentational* change is needed (prefer not to touch it)
- Tests under `tests/` that cover the views IF your refactor changes a signature/behavior (update them to match; never delete coverage)

**OUT:**
- `scripts/` (ETL/analysis), `datanova/` (analysis package), `data/` (prepared data — read-only)
- Any backend logic, new data sources, or new paid services
- Git operations (the main agent commits after your completion)
- Deploy/hosting

## Guidelines

1. **Read first:** `context/RULEBOOK.md`, `context/project.md`, `context/decisions.md`, then run your skill router (`skills.json`) and load only matching skills. Classify: `task_kind: refine_existing`, `design_direction: premium` (civic/data-forward), `target: web`, `stack: vanilla`.
2. **Preserve the established visual language:** civic, data-forward, readable. Keep the colorblind-safe decisions (sequential YlOrBr/Blues for need/access, diverging RdBu for gap, the A–F grade palette). Do not introduce a consumer/flashy aesthetic.
3. **One styling mechanism.** Consolidate on a single, safe approach. If you reintroduce custom CSS, it must load **without leaking source text** into the page (the historical bug) — prefer the native theme config + a safe injection path you verify. The dead `styles.css` must either be wired in and verified, or removed — no dead files left behind.
4. **Fix the deprecated API.** Replace `st.components.v1.html(...)` with the modern equivalent and verify the map still renders at full width.
5. **Keep the pure-helper separation.** `get_*`/`build_*` lookups must stay testable without a running Streamlit app.
6. **Verify live:** launch the app (`make app`), click through all 4 views at desktop and ≤720px widths; check focus-visible states, legends, and that no raw HTML/CSS text renders on the page.
7. **Run the suite:** `make test` must pass (it takes ~4.5 min). Fix anything you break.
8. Work incrementally and keep the app bootable after each change.

## Deliverables

- Refactored frontend code (all changes in `app/`, `.streamlit/`, and `tests/` as needed).
- A `context/`-independent summary in your completion file: what you changed, the styling mechanism you chose and why, deprecated-API fix, any tests updated, and anything you deliberately left (with reason).

## Done when

- [ ] `make test` passes (full suite).
- [ ] App boots locally via `make app`; no import/runtime errors.
- [ ] All 4 views (map, report card, what-if, export) work and render cleanly at desktop and ≤720px.
- [ ] No raw CSS/HTML source text visible in the rendered page.
- [ ] No deprecated `st.components.v1.html` usage remains.
- [ ] No dead/unused style files left (either wired in or removed).
- [ ] Colorblind-safe palettes and A–F grade colors unchanged.
- [ ] Inline-HTML sprawl meaningfully reduced or centralized; if some remains, you justify it.
- [ ] Completion file written to `agents/picasso/completions/refactor-frontend-001.md` with an honest Status.
