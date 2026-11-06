"""Shared presentational helpers for app-built HTML fragments.

One styling story: every custom HTML fragment rendered into the Streamlit DOM
uses semantic classes defined in ``app/styles.css`` (``dn-`` prefix). Inline
styles are limited to data-driven values (per-grade colors) passed through CSS
custom properties, so the visual rules live in a single stylesheet and source
text can never leak into the page.

Folium maps render in their own iframe document, so map-internal chrome (the
grade legend) carries a tiny scoped stylesheet injected into the map's header —
the one intentional exception to the single-stylesheet rule, because the iframe
isolates documents.
"""

from __future__ import annotations

from typing import Any

import folium

# A–F grade colors — single source of truth for the app (re-exported by
# map_view and report_card so existing imports keep working).
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


def grade_color(grade: Any) -> str:
    """The canonical fill color for a letter grade (unknown -> gray)."""
    return GRADE_COLORS.get(str(grade or "").strip().upper(), UNKNOWN_GRADE_COLOR)


def stats_html(summary: dict[str, Any]) -> str:
    """ACS stat tiles for the Equity Report Card (``.dn-stat`` grid)."""
    blocks: list[str] = []
    for label, col, fmt in ACS_STAT_FIELDS:
        value = summary.get(col)
        text = fmt.format(value) if value is not None else "n/a"
        blocks.append(
            '<div class="dn-stat">'
            f'<div class="dn-stat-label">{label}</div>'
            f'<div class="dn-stat-value">{text}</div>'
            "</div>"
        )
    return '<div class="dn-stat-grid">' + "".join(blocks) + "</div>"


def grades_chips_html(grades: list[dict[str, Any]]) -> str:
    """Per-dimension letter-grade chips (``.dn-chip`` pills)."""
    chips: list[str] = []
    for item in grades:
        grade = item.get("grade") or "—"
        color = grade_color(grade)
        chips.append(
            f'<span class="dn-chip" style="--dn-grade-bg:{color}">'
            f"{item['dimension']} {grade}</span>"
        )
    return '<div class="dn-chips">' + "".join(chips) + "</div>"


def action_callout_html(action: str) -> str:
    """Tinted callout for a recommendation's action text (``.dn-callout``)."""
    return f'<div class="dn-callout">{action}</div>'


def grade_legend_html() -> str:
    """Grade legend overlay for the folium maps (render inside the iframe)."""
    rows = "".join(
        '<div class="dn-map-legend-row">'
        f'<span class="dn-map-legend-swatch" style="background:{color}"></span>'
        f"<span>{grade}</span></div>"
        for grade, color in GRADE_COLORS.items()
    )
    return (
        '<div class="dn-map-legend">'
        '<span class="dn-map-legend-title">Grade</span>'
        + rows
        + "</div>"
    )


# Scoped styles for map-internal chrome (rendered inside the folium iframe;
# see module docstring).
MAP_LEGEND_CSS = """
.dn-map-legend{position:absolute;bottom:24px;right:24px;z-index:1000;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;box-shadow:0 1px 4px rgba(15,23,42,.12);font:12px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:#0f172a;}
.dn-map-legend-title{display:block;font-weight:700;margin-bottom:4px;}
.dn-map-legend-row{display:flex;align-items:center;gap:6px;margin-top:2px;}
.dn-map-legend-swatch{flex:none;width:14px;height:14px;border:1px solid #94a3b8;border-radius:3px;}
"""


def folium_inject_css(m: folium.Map, css: str) -> None:
    """Inject a ``<style>`` block into a folium map's document head."""
    m.get_root().header.add_child(folium.Element(f"<style>{css}</style>"))
