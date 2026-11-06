"""Export & summary view (Task 3.4).

Provides CSV downloads for the current view:

- a per-block-group **Equity Report Card snapshot** (the selected geoid), and
- a city-wide **top-N underserved areas table** (ranked by real equity data).

Pure builders (``build_report_card_snapshot``, ``build_top_underserved_table``,
``to_csv``) are separated from the thin Streamlit renderer
(``render_export``) so they can be unit-tested against the real prepared data
without a running app (mirrors the Task 3.2/3.3 ``report_card.py`` /
``whatif.py`` pattern).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitAPIException

from app.views.report_card import lookup_block_group

__all__ = [
    "SNAPSHOT_COLUMNS",
    "TOP_N_DEFAULT",
    "GRADE_RANK",
    "METHODOLOGY_NOTE",
    "build_report_card_snapshot",
    "build_top_underserved_table",
    "to_csv",
    "render_export",
]

# Columns shared by the report-card snapshot and the city-wide underserved table.
# Order is intentional: identity + letter grades first, then scores, then ACS
# demographic statistics (all real columns on ``equity_scores``).
SNAPSHOT_COLUMNS: tuple[str, ...] = (
    "geoid",
    "grade",
    "jobs_grade",
    "healthcare_grade",
    "schools_grade",
    "food_grade",
    "jobs_access",
    "healthcare_access",
    "schools_access",
    "food_access",
    "access_overall",
    "need_index",
    "gap",
    "pop_total",
    "poverty_pct",
    "zero_car_pct",
    "median_income",
)

TOP_N_DEFAULT = 25

# Letter-grade rank used to break ties in the underserved ranking (F first).
GRADE_RANK: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}

METHODOLOGY_NOTE = (
    "Methodology: equity scores, letter grades, and ACS statistics are from "
    "the prepared DataNova 2026 transit-equity analysis. The equity gap = "
    "access − need (positive = better served). No live routing or API keys."
)


def _as_str_geoid(geoid: Any) -> str:
    return str(geoid).strip()


def _current_selection() -> str | None:
    """The session-selected block-group geoid, or ``None``.

    Guarded so the module works in bare imports / tests without a running
    Streamlit app (missing session state falls back to "no selection").
    """
    try:
        selected = st.session_state.get("selected_geoid")
    except (AttributeError, StreamlitAPIException):  # bare import / no runtime
        return None
    return _as_str_geoid(selected) if selected else None


def build_report_card_snapshot(
    geoid: Any, prepared: dict[str, Any]
) -> pd.DataFrame | None:
    """One-row DataFrame snapshot of the report card for ``geoid``.

    The row is read from the real ``equity_scores`` table (same source as the
    on-screen report card) via :func:`app.views.report_card.lookup_block_group`.

    Returns ``None`` when the geoid is unknown (handled gracefully by callers).
    """
    row = lookup_block_group(geoid, prepared)
    if row is None:
        return None
    record = {col: row.get(col) for col in SNAPSHOT_COLUMNS}
    return pd.DataFrame([record], columns=list(SNAPSHOT_COLUMNS))


def build_top_underserved_table(
    prepared: dict[str, Any], n: int = TOP_N_DEFAULT
) -> pd.DataFrame:
    """City-wide top ``n`` underserved block groups.

    Ranked by real equity data: ``need_index`` descending, then ``gap``
    ascending (most negative gap first) among ties, then by letter grade
    (F first) as a final tie-break. Returns a plain DataFrame (no geometry).
    """
    equity = prepared["equity_scores"]
    df = equity[list(SNAPSHOT_COLUMNS)].copy()
    df["_grade_rank"] = df["grade"].map(GRADE_RANK).fillna(len(GRADE_RANK))
    ranked = df.sort_values(
        ["need_index", "gap", "_grade_rank"],
        ascending=[False, True, False],
    )
    ranked = ranked.drop(columns=["_grade_rank"]).reset_index(drop=True)
    return ranked.head(int(n))


def to_csv(frame: pd.DataFrame) -> str:
    """Serialize a DataFrame to CSV text (no index column)."""
    return frame.to_csv(index=False)


def render_export(prepared: dict[str, Any], selected_geoid: Any = None) -> None:
    """Render the Export & summary view into the Streamlit UI.

    Always offers the city-wide top-N underserved-table download; additionally
    offers the selected block group's Equity Report Card snapshot when a geoid
    is selected (via the map/fallback selector, or ``selected_geoid``).

    Args:
        prepared: output of :func:`app.data_io.load_prepared`.
        selected_geoid: optional explicit geoid (used by tests / callers that
            already know the selection; defaults to session state).
    """
    if selected_geoid is None:
        selected_geoid = _current_selection()

    st.subheader("Export & summary")
    st.caption(METHODOLOGY_NOTE)

    top = build_top_underserved_table(prepared)
    st.markdown(f"**City-wide top {len(top)} underserved block groups**")
    st.dataframe(top)
    st.download_button(
        "Download city-wide table (CSV)",
        to_csv(top),
        file_name="seattle_top_underserved.csv",
        mime="text/csv",
    )

    if selected_geoid is None:
        st.info(
            "Select a block group on the Map explorer (or the sidebar dropdown) "
            "to also download its Equity Report Card snapshot."
        )
        return

    snapshot = build_report_card_snapshot(selected_geoid, prepared)
    if snapshot is None:
        st.warning(
            f"Block group {selected_geoid} was not found; the city-wide table "
            "above is still available for download."
        )
        return

    st.markdown(f"**Equity report card — block group {selected_geoid}**")
    st.dataframe(snapshot)
    st.download_button(
        "Download report card snapshot (CSV)",
        to_csv(snapshot),
        file_name=f"seattle_report_card_{selected_geoid}.csv",
        mime="text/csv",
    )
