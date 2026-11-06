"""Map view for the Seattle Transit Equity Index app."""

from pathlib import Path
from typing import Any

import folium
import geopandas as gpd
import streamlit as st

from app.data_io import BOUNDARY_PATH, PREPARED_DIR
from app.views._ui import (
    GRADE_COLORS as GRADE_COLORS,
    MAP_LEGEND_CSS,
    folium_inject_css,
    grade_legend_html,
)

__all__ = ["PREPARED_DIR", "BOUNDARY_PATH", "load_boundary", "render_map"]

# A–F grade colors (used by the categorical Grade layer). Canonical dict lives
# in app/views/_ui.py; re-exported here for existing callers.

# Real choropleth layers over the block groups. "kind": "choropleth" uses a
# numeric column binned by folium; "kind": "grade" colors by categorical grade.
#
# Color accessibility (colorblind-safe): need/access use *sequential*
# single-hue palettes (YlOrBr, Blues); the gap layer uses a *diverging*
# red-blue palette (RdBu) instead of a red-green one, so it stays readable to
# red-green colorblind viewers. Legend text states the direction explicitly.
ANALYSIS_LAYERS: list[dict[str, Any]] = [
    {
        "key": "need_index",
        "label": "Need Index",
        "column": "need_index",
        "fill_color": "YlOrBr",
        "legend": "Need index (higher = more need)",
        "kind": "choropleth",
    },
    {
        "key": "access_overall",
        "label": "Access (overall)",
        "column": "access_overall",
        "fill_color": "Blues",
        "legend": "Overall access score (higher = better)",
        "kind": "choropleth",
    },
    {
        "key": "gap",
        "label": "Equity Gap",
        "column": "gap",
        "fill_color": "RdBu",
        "legend": "Equity gap (access − need): red = underserved, blue = better served",
        "kind": "choropleth",
    },
    {
        "key": "grade",
        "label": "Grade (A–F)",
        "column": "grade",
        "kind": "grade",
    },
]


def load_boundary() -> gpd.GeoDataFrame:
    """Load the real Seattle boundary GeoJSON.

    Raises:
        FileNotFoundError: if the prepared boundary is missing.
    """
    if not BOUNDARY_PATH.exists():
        raise FileNotFoundError(BOUNDARY_PATH)
    gdf = gpd.read_file(BOUNDARY_PATH)
    if gdf.empty:
        raise ValueError(f"{BOUNDARY_PATH} contains no features")
    return gdf


def _grade_style(properties: dict[str, Any]) -> dict[str, Any]:
    grade = str(properties.get("grade", "")).upper()
    color = GRADE_COLORS.get(grade, "#6b7280")
    return {
        "color": "#1f3a5f",
        "weight": 0.5,
        "opacity": 0.6,
        "fillColor": color,
        "fillOpacity": 0.7,
    }


def _build_map(boundary: gpd.GeoDataFrame) -> folium.Map:
    bounds = boundary.total_bounds  # (minx, miny, maxx, maxy)
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    m = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap")

    folium.GeoJson(
        boundary,
        name="Seattle boundary",
        style_function=lambda _: {
            "color": "#1f3a5f",
            "weight": 2,
            "fillColor": "#d9e2ec",
            "fillOpacity": 0.15,
        },
    ).add_to(m)
    return m


def _add_analysis_layer(
    m: folium.Map, layer: dict[str, Any], equity: gpd.GeoDataFrame
) -> None:
    if layer["kind"] == "grade":
        folium.GeoJson(
            equity,
            name=layer["label"],
            style_function=lambda feature: _grade_style(feature["properties"]),
        ).add_to(m)
        folium_inject_css(m, MAP_LEGEND_CSS)
        m.get_root().html.add_child(folium.Element(grade_legend_html()))
        return

    folium.Choropleth(
        geo_data=equity,
        data=equity,
        columns=("geoid", layer["column"]),
        key_on="feature.properties.geoid",
        fill_color=layer["fill_color"],
        fill_opacity=0.65,
        line_color="#1f3a5f",
        line_weight=0.5,
        line_opacity=0.4,
        nan_fill_color="#eef0f2",
        name=layer["label"],
        legend_name=layer["legend"],
        show=True,
    ).add_to(m)


def render_map(data: dict[str, Any]) -> None:
    """Render the Seattle boundary map with a real choropleth analysis layer.

    Args:
        data: output of :func:`app.data_io.load_prepared` (must contain
            ``boundary`` and ``equity_scores``).
    """
    boundary = data["boundary"]
    equity = data["equity_scores"]

    labels = [layer["label"] for layer in ANALYSIS_LAYERS]
    choice = st.selectbox(
        "Analysis layer",
        labels,
        index=0,
        help="Color each block group by a real equity metric.",
    )
    layer = next(cfg for cfg in ANALYSIS_LAYERS if cfg["label"] == choice)

    m = _build_map(boundary)
    _add_analysis_layer(m, layer, equity)

    folium.LayerControl(collapsed=True).add_to(m)

    # Modern iframe embedding (st.iframe replaced the deprecated components API).
    st.iframe(
        m._repr_html_(),
        height=640,
        alt="Map of the selected Seattle transit equity layer",
    )
