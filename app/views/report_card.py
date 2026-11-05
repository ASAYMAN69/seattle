"""Neighborhood Report Card view (Task 3.2).

Pure data lookups (``get_*``) are kept separate from the Streamlit rendering so
they can be unit-tested against real prepared data without a running app.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

__all__ = [
    "ACS_STAT_FIELDS",
    "GRADE_DIMENSIONS",
    "GRADE_COLORS",
    "UNKNOWN_GRADE_COLOR",
    "lookup_block_group",
    "get_neighborhood_summary",
    "get_grades",
    "get_top_recommendations",
    "render_report_card",
]

# (dimension label, equity_scores column name)
GRADE_DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("Jobs", "jobs_grade"),
    ("Healthcare", "healthcare_grade"),
    ("Schools", "schools_grade"),
    ("Food", "food_grade"),
    ("Overall", "grade"),
)

GRADE_COLORS: dict[str, str] = {
    "A": "#1a7f37",
    "B": "#2d9d4f",
    "C": "#e3b341",
    "D": "#e0762a",
    "F": "#c62828",
}
UNKNOWN_GRADE_COLOR = "#6b7280"

# (label, field on equity_scores, str.format spec for display)
ACS_STAT_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("Population", "pop_total", "{:,}"),
    ("Poverty rate", "poverty_pct", "{:.1%}"),
    ("Zero-car households", "zero_car_pct", "{:.1%}"),
    ("Median income", "median_income", "${:,.0f}"),
)


def _as_str_geoid(geoid: Any) -> str:
    return str(geoid).strip()


def _clean_number(value: Any) -> int | float | None:
    if value is None or pd.isna(value):
        return None
    value = float(value)
    return int(value) if value.is_integer() else value


def _optional_str(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value).strip()


def lookup_block_group(geoid: Any, data: dict[str, Any]) -> pd.Series | None:
    """Return the ``equity_scores`` row for ``geoid`` (or ``None`` if unknown)."""
    equity = data["equity_scores"]
    key = _as_str_geoid(geoid)
    matches = equity.loc[equity["geoid"].astype(str) == key]
    if matches.empty:
        return None
    return matches.iloc[0]


def get_neighborhood_summary(
    geoid: Any, data: dict[str, Any]
) -> dict[str, Any] | None:
    """Raw neighborhood identity + ACS stats for ``geoid``.

    Returns ``None`` when the geoid is unknown (handled gracefully by callers).
    Values are kept raw (numbers, not formatted strings) so tests can compare
    them directly against the ACS source data.
    """
    row = lookup_block_group(geoid, data)
    if row is None:
        return None
    summary: dict[str, Any] = {"geoid": str(row["geoid"])}
    for _, col, _fmt in ACS_STAT_FIELDS:
        summary[col] = _clean_number(row.get(col))
    summary["tract"] = _optional_str(row.get("TRACTCE"))
    summary["block_group"] = _optional_str(row.get("BLKGRPCE"))
    return summary


def get_grades(geoid: Any, data: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Per-dimension letter grades for ``geoid`` (Jobs/Healthcare/Schools/Food/Overall).

    Returns ``None`` for an unknown geoid.
    """
    row = lookup_block_group(geoid, data)
    if row is None:
        return None
    grades: list[dict[str, Any]] = []
    for dimension, col in GRADE_DIMENSIONS:
        raw = row.get(col)
        grade = None if raw is None or pd.isna(raw) else str(raw).strip().upper()
        grades.append({"dimension": dimension, "column": col, "grade": grade})
    return grades


def get_top_recommendations(
    geoid: Any, data: dict[str, Any], k: int = 3
) -> list[dict[str, Any]]:
    """Top ``k`` corridor recommendations serving ``geoid``, by affected population.

    Recommendations are selected from the real ``recommendations`` table whose
    ``geoids`` list includes this block group, ordered by ``affected_pop``
    descending. Returns an empty list when none exist (or geoid unknown).
    """
    recommendations = data["recommendations"]
    if recommendations.empty:
        return []
    key = _as_str_geoid(geoid)

    def _serves(geoids: Any) -> bool:
        if geoids is None:
            return False
        try:
            served = [str(g) for g in geoids]
        except TypeError:
            return False
        return key in served

    matching = recommendations.loc[recommendations["geoids"].apply(_serves)]
    if matching.empty:
        return []
    ordered = matching.sort_values("affected_pop", ascending=False)

    result: list[dict[str, Any]] = []
    for _, row in ordered.head(k).iterrows():
        affected = row.get("affected_pop")
        result.append(
            {
                "corridor": str(row.get("corridor", "")),
                "action": str(row.get("action", "")),
                "affected_pop": (
                    int(affected)
                    if affected is not None and not pd.isna(affected)
                    else None
                ),
            }
        )
    return result


def _stats_html(summary: dict[str, Any]) -> str:
    blocks: list[str] = []
    for label, col, fmt in ACS_STAT_FIELDS:
        value = summary.get(col)
        text = fmt.format(value) if value is not None else "n/a"
        blocks.append(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;'
            'border-radius:8px;padding:8px 12px;min-width:110px;flex:1;">'
            f'<div style="font-size:12px;color:#475569;">{label}</div>'
            f'<div style="font-size:17px;font-weight:700;color:#0f172a;">{text}</div>'
            "</div>"
        )
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 10px;">'
        + "".join(blocks)
        + "</div>"
    )


def _grades_chips_html(grades: list[dict[str, Any]]) -> str:
    chips: list[str] = []
    for item in grades:
        grade = item["grade"] or "—"
        color = GRADE_COLORS.get(grade, UNKNOWN_GRADE_COLOR)
        chips.append(
            '<span style="background:'
            + color
            + ";color:#fff;font-weight:600;font-size:13px;"
            "padding:3px 11px;border-radius:999px;box-shadow:0 1px 2px "
            'rgba(15,23,42,0.25);">'
            f"{item['dimension']} {grade}</span>"
        )
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 12px;">'
        + "".join(chips)
        + "</div>"
    )


def render_report_card(geoid: Any, data: dict[str, Any]) -> None:
    """Render the Equity Report Card for ``geoid`` into the Streamlit UI.

    Handles gracefully: no selection yet (info hint) and an unknown geoid
    (warning). All heavy lifting lives in the ``get_*`` helpers so the
    rendering layer stays thin.
    """
    if geoid is None or _as_str_geoid(geoid) == "":
        st.info(
            "Select a block group on the map (or use the dropdown below) to "
            "see its Equity Report Card."
        )
        return

    summary = get_neighborhood_summary(geoid, data)
    if summary is None:
        st.warning(f"Block group {geoid} was not found in the equity data.")
        return

    identity = f"Block Group {summary['geoid']}"
    if summary.get("tract"):
        identity += f" · Tract {summary['tract']}"
        if summary.get("block_group"):
            identity += f" / BG {summary['block_group']}"
    st.markdown(f"#### {identity}")
    st.markdown(_stats_html(summary), unsafe_allow_html=True)

    grades = get_grades(geoid, data)
    if grades:
        st.markdown("**Grades**")
        st.markdown(_grades_chips_html(grades), unsafe_allow_html=True)

    st.markdown("**Top recommendations**")
    recommendations = get_top_recommendations(geoid, data)
    if not recommendations:
        st.caption("No corridor recommendations currently target this block group.")
    else:
        for rec in recommendations:
            affected = rec["affected_pop"]
            pop_txt = f"{affected:,}" if affected is not None else "n/a"
            st.markdown(
                f"- **{rec['corridor']}** — {rec['action']} "
                f"(≈ {pop_txt} residents affected)"
            )
