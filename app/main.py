"""DataNova 2026 — Seattle Transit Equity Index.

Interactive demo app. Run with: streamlit run app/main.py

Task 3.2 wiring: clicking a block group on the folium map selects it (the map
injects a click handler that navigates to ``?selected_geoid=...`` on the top
window; the app reads that query param back into session state). A fallback
dropdown in the sidebar provides an equivalent selection. The sidebar then
renders the neighborhood Equity Report Card
(:func:`app.views.report_card.render_report_card`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import folium
import streamlit as st

# Ensure the repo root is importable regardless of how Streamlit launches this
# script (streamlit run app/main.py does not put the project root on sys.path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datanova import __version__  # noqa: E402
from app.data_io import PreparedDataError, load_prepared  # noqa: E402
from app.views.export import render_export  # noqa: E402
from app.views.map_view import ANALYSIS_LAYERS, GRADE_COLORS  # noqa: E402
from app.views.report_card import render_report_card  # noqa: E402
from app.views.whatif import render_whatif  # noqa: E402

st.set_page_config(page_title="Seattle Transit Equity Index", layout="wide")


def _inject_styles() -> None:
    """Global styling is handled by `.streamlit/config.toml` ([theme]), which
    is native and cannot leak source text into the page. Custom CSS injection
    via st.markdown/st.html was removed (2026-11-06) after users reported the
    stylesheet source rendering as visible text; do not reintroduce a
    `<style>` block through an HTML-String path."""
    return


_inject_styles()

st.title("Seattle Transit Equity Index")
st.caption(
    "Who in Seattle is disconnected from opportunity? "
    f"DataNova 2026 · v{__version__}"
)

# URL query params used by the map-click → selection hand-off.
SELECT_PARAM = "selected_geoid"
LAYER_PARAM = "analysis_layer"


# ---------------------------------------------------------------------------
# Selection plumbing (map click -> session state; fallback dropdown)
# ---------------------------------------------------------------------------
def _read_query_selection() -> None:
    """Move a map-click selection (URL query params) into session state."""
    try:
        qp = st.query_params
    except Exception:  # noqa: BLE001 - bare import / no runtime
        return
    clicked = qp.get(SELECT_PARAM)
    if clicked:
        st.session_state[SELECT_PARAM] = str(clicked)
        try:
            del qp[SELECT_PARAM]
        except Exception:  # noqa: BLE001
            pass
    layer = qp.get(LAYER_PARAM)
    if layer:
        labels = [cfg["label"] for cfg in ANALYSIS_LAYERS]
        if layer in labels:
            st.session_state[LAYER_PARAM] = layer
        try:
            del qp[LAYER_PARAM]
        except Exception:  # noqa: BLE001
            pass


def _current_geoid(data: dict[str, Any]) -> str | None:
    """The session-selected block-group geoid, or None if not selected."""
    selected = st.session_state.get(SELECT_PARAM)
    if not selected:
        return None
    selected = str(selected)
    known = set(data["equity_scores"]["geoid"].astype(str))
    return selected if selected in known else None


# ---------------------------------------------------------------------------
# Interactive map (mirrors app/views/map_view.py, adds click-to-select)
# ---------------------------------------------------------------------------
def _grade_style(feature: dict[str, Any]) -> dict[str, str]:
    grade = str(feature["properties"].get("grade", "")).upper()
    color = GRADE_COLORS.get(grade, "#6b7280")
    return {
        "color": "#1f3a5f",
        "weight": 0.5,
        "opacity": 0.6,
        "fillColor": color,
        "fillOpacity": 0.7,
    }


def _grade_legend_html() -> str:
    rows = "".join(
        '<div style="display:flex;align-items:center;margin-bottom:2px;">'
        '<span style="display:inline-block;width:14px;height:14px;'
        f'background:{color};margin-right:6px;border:1px solid #555;"></span>'
        f"{grade}</div>"
        for grade, color in GRADE_COLORS.items()
    )
    return (
        '<div style="position:absolute;bottom:24px;right:24px;z-index:1000;'
        'background:#fff;padding:8px 10px;border-radius:4px;box-shadow:0 1px 4px '
        'rgba(0,0,0,.3);font:12px/1.4 sans-serif;">'
        "<strong>Grade</strong><br/>" + rows + "</div>"
    )


def _inject_select_script(m: folium.Map, layer_label: str) -> None:
    """Add a click handler so selecting a block group updates the URL query.

    The handler is bound at the map level: any click that lands on a feature
    carrying a ``geoid`` property (block groups) selects it by navigating the
    top window to ``?selected_geoid=...&analysis_layer=...``. Streamlit then
    reruns with the new query params, which ``_read_query_selection`` picks up.
    """
    script = """
    <script>
    function __dn_select_geoid(geoid) {
      var p = new URLSearchParams(window.top.location.search);
      p.set('selected_geoid', geoid);
      p.set('analysis_layer', LAYER_LABEL);
      window.top.location.search = p.toString();
    }
    (function () {
      function bindClicks() {
        try {
          var map = MAP_NAME;
          map.on('click', function (e) {
            if (e.layer && e.layer.feature && e.layer.feature.properties &&
                e.layer.feature.properties.geoid) {
              __dn_select_geoid(String(e.layer.feature.properties.geoid));
            }
          });
        } catch (err) {}
      }
      if (document.readyState !== 'loading') {
        setTimeout(bindClicks, 400);
      } else {
        document.addEventListener('DOMContentLoaded', function () {
          setTimeout(bindClicks, 400);
        });
      }
    })();
    </script>
    """
    script = (
        script.replace("MAP_NAME", m.get_name()).replace(
            "LAYER_LABEL", json.dumps(layer_label)
        )
    )
    m.get_root().html.add_child(folium.Element(script))


def _build_interactive_map(
    prepared: dict[str, Any], layer_label: str
) -> folium.Map:
    """Build the folium map with the selected analysis layer + click-to-select."""
    boundary = prepared["boundary"]
    equity = prepared["equity_scores"]
    layer = next(cfg for cfg in ANALYSIS_LAYERS if cfg["label"] == layer_label)

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

    tooltip_kwargs: dict[str, Any] = {
        "fields": ["geoid", layer["column"]] if layer["kind"] != "grade" else ["geoid", "grade"],
        "aliases": ["Block group", layer["label"]] if layer["kind"] != "grade" else ["Block group", "Grade"],
        "sticky": True,
    }

    if layer["kind"] == "grade":
        folium.GeoJson(
            equity,
            name=layer["label"],
            style_function=_grade_style,
            tooltip=folium.GeoJsonTooltip(**tooltip_kwargs),
        ).add_to(m)
        m.get_root().html.add_child(folium.Element(_grade_legend_html()))
    else:
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
            tooltip=folium.GeoJsonTooltip(**tooltip_kwargs),
        ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    _inject_select_script(m, layer_label)
    return m


# ---------------------------------------------------------------------------
# App body
# ---------------------------------------------------------------------------
# Load all prepared inputs once; show a graceful error panel if any are missing
# or malformed instead of crashing the app.
try:
    data = load_prepared()
except PreparedDataError as exc:
    st.error(f"Prepared data could not be loaded: {exc}")
    st.info(
        "Run the analysis pipeline (`scripts/run_analysis.py`) so the app’s "
        "prepared inputs exist under data/prepared/. Contact the data team if "
        "this persists."
    )
    st.stop()

_read_query_selection()

# Sidebar: neighborhood report card + fallback dropdown selector.
with st.sidebar:
    st.header("Neighborhood Report Card")

    equity = data["equity_scores"]
    options = equity["geoid"].astype(str).tolist()
    grade_by_geoid = dict(zip(options, equity["grade"].astype(str)))

    current = _current_geoid(data)

    def _fmt_option(geoid: str) -> str:
        return f"{geoid} — {grade_by_geoid.get(geoid, '?')}"

    chosen = st.selectbox(
        "Block group",
        options,
        index=options.index(current) if current in options else None,
        format_func=_fmt_option,
        placeholder="Choose a block group…",
        help="Fallback selector — you can also click a block group on the map.",
    )
    if chosen is not None:
        st.session_state[SELECT_PARAM] = chosen
        current = chosen

    render_report_card(current, data)

# Main area: tab 1 = map explorer (analysis layer + interactive map); tab 2
# = what-if frequency explorer (Task 3.3); tab 3 = export & summary
# (Task 3.4).
tab_explore, tab_whatif, tab_export = st.tabs(
    ["Map explorer", "What-if frequency explorer", "Export & summary"]
)

with tab_explore:
    labels = [cfg["label"] for cfg in ANALYSIS_LAYERS]
    layer_choice = st.session_state.get(LAYER_PARAM)
    if layer_choice not in labels:
        layer_choice = labels[0]
    choice = st.selectbox(
        "Analysis layer",
        labels,
        index=labels.index(layer_choice),
        help="Color each block group by a real equity metric.",
    )
    st.session_state[LAYER_PARAM] = choice

    map_html = _build_interactive_map(data, choice)._repr_html_()
    st.components.v1.html(map_html, height=640, scrolling=False)

with tab_whatif:
    render_whatif(data)

with tab_export:
    render_export(data)
