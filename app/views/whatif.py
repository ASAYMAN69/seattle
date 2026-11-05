"""What-if frequency explorer view (Task 3.3).

Lets a user pick a recommended corridor and drag a *frequency multiplier* slider
(1.0–3.0×) to see the estimated affected population and expected access
improvement. All numbers come from the precomputed sensitivity table
(``data/prepared/equity/sensitivity.parquet``, produced in Task 2.4) — there is
**no live routing** and no external API.

Interpolation / extrapolation model (documented)
------------------------------------------------
The sensitivity table stores, per recommended corridor, the estimated
overall-access gain for the reference scenario: **doubling frequency (2.0×)**.
Task 2.4's documented approximation is: doubling frequency halves the expected
wait; with a 7-minute static wait the saving is ``min(headway/4, 3.5)`` minutes,
and the access gain per block group is a weighted sum of category access gaps
times ``min(saving / threshold_c, 1)``.

For an arbitrary multiplier ``m`` we generalize the same model without re-running
routing or the access model:

- wait saving ``s(m) = min((headway/2) * (1 - 1/m), 3.5)`` — this reduces
  exactly to the documented ``min(headway/4, 3.5)`` at ``m = 2.0``.
- access gain ``g(m) = g_ref * s(m) / s_ref`` where ``g_ref``/``s_ref`` are the
  table's reference gain and reference wait saving (2.0×). This is exact while
  the wait saving is below the 3.5-minute cap and each category threshold; where
  a cap binds, the linear scaling is a documented, conservative ceiling (extra
  frequency stops adding benefit once the wait/access improvement saturates).
- affected population: the base ``affected_pop`` (real data) is the catchment
  population of the recommendation's block groups and does not change with
  frequency. The slider also drives a derived **newly benefiting residents**
  figure = ``affected_pop * min(s(m)/s_ref, 1)`` — i.e. the share of the
  catchment realizing an improvement, which equals the full catchment at the
  reference 2.0× and cannot exceed it.

Pure lookups/projections are separated from the Streamlit rendering so they can
be unit-tested against real prepared data without a running app.
"""

from __future__ import annotations

from typing import Any

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st

__all__ = [
    "FREQ_MIN",
    "FREQ_MAX",
    "FREQ_DEFAULT",
    "REFERENCE_MULTIPLIER",
    "MAX_WAIT_SAVING_MIN",
    "route_key",
    "clamp_multiplier",
    "lookup_sensitivity_row",
    "lookup_recommendation",
    "sensitivity_corridors",
    "wait_saving_min",
    "what_if_projection",
    "route_ids_serving_geoid",
    "build_highlight_map",
    "render_whatif",
]

# Frequency-multiplier slider bounds (× current AM-peak frequency).
FREQ_MIN = 1.0
FREQ_MAX = 3.0
FREQ_DEFAULT = 2.0

# The scenario the precomputed sensitivity table documents (Task 2.4).
REFERENCE_MULTIPLIER = 2.0

# Wait-saving cap (minutes) from the Task 2.4 model (static wait 7 min → at
# most 3.5 min saved when frequency is doubled).
MAX_WAIT_SAVING_MIN = 3.5

# Internal sentinel for the route_id=None coverage row (never shown to users).
_COVERAGE_KEY = "__coverage__"


def route_key(route_id: Any) -> str | None:
    """Normalize a route id (``None``/NaN coverage row → ``None``).

    The sensitivity table's coverage-gap row has a ``NaN`` route id; this key
    lets callers look it up with ``None`` and keeps all matching string-safe.
    """
    if route_id is None:
        return None
    try:
        if pd.isna(route_id):
            return None
    except (TypeError, ValueError):
        pass
    text = str(route_id).strip()
    return text or None


def clamp_multiplier(multiplier: float) -> float:
    """Clamp a multiplier into the documented [FREQ_MIN, FREQ_MAX] range."""
    return min(max(float(multiplier), FREQ_MIN), FREQ_MAX)


def _keyed_route_ids(df: pd.DataFrame) -> list[str | None]:
    """Column of normalized route keys (``None`` for the coverage row)."""
    return [route_key(v) for v in df["route_id"]]


def lookup_sensitivity_row(route_id: Any, data: dict[str, Any]) -> pd.Series | None:
    """Return the ``sensitivity`` row for ``route_id`` (or ``None`` if unknown)."""
    df = data["sensitivity"]
    target = route_key(route_id)
    keys = _keyed_route_ids(df)
    matches = [i for i, k in enumerate(keys) if k == target]
    if not matches:
        return None
    return df.iloc[matches[0]]


def lookup_recommendation(
    route_id: Any, data: dict[str, Any]
) -> pd.Series | None:
    """Return the ``recommendations`` row for ``route_id`` (or ``None``)."""
    gdf = data["recommendations"]
    target = route_key(route_id)
    keys = _keyed_route_ids(gdf)
    matches = [i for i, k in enumerate(keys) if k == target]
    if not matches:
        return None
    return gdf.iloc[matches[0]]


def sensitivity_corridors(data: dict[str, Any]) -> list[dict[str, Any]]:
    """All recommended corridors (incl. the coverage-gap row), by affected pop.

    Returns a list of dicts with ``route_id`` (normalized; ``None`` for the
    coverage gap), ``corridor``, ``action``, ``affected_pop``, ordered by
    ``affected_pop`` descending so the dropdown/seed defaults are sensible.
    """
    df = data["sensitivity"]
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        affected = row.get("affected_pop")
        rows.append(
            {
                "route_id": route_key(row.get("route_id")),
                "corridor": str(row.get("corridor", "")),
                "action": str(row.get("action", "")),
                "affected_pop": (
                    int(affected) if affected is not None and not pd.isna(affected) else None
                ),
            }
        )
    rows.sort(key=lambda r: (r["affected_pop"] is not None, r["affected_pop"] or 0), reverse=True)
    return rows


def wait_saving_min(headway_min: Any, multiplier: float) -> float:
    """Estimated wait saving (minutes) at ``multiplier``× frequency.

    Implements ``min((headway/2) * (1 - 1/m), 3.5)``, which equals the documented
    Task 2.4 formula ``min(headway/4, 3.5)`` at ``m = 2.0``. The coverage-gap row
    (no headway) has no wait saving.
    """
    if headway_min is None or pd.isna(headway_min):
        return 0.0
    m = clamp_multiplier(multiplier)
    saving = (float(headway_min) / 2.0) * (1.0 - 1.0 / m)
    return min(saving, MAX_WAIT_SAVING_MIN)


def what_if_projection(
    route_id: Any, multiplier: float, data: dict[str, Any]
) -> dict[str, Any] | None:
    """Project the what-if scenario for ``route_id`` at ``multiplier``×.

    Returns a dict with ``route_id`` (normalized), ``corridor``, ``action``,
    ``affected_pop`` (real catchment population), ``multiplier`` (clamped),
    ``wait_saving_min``, ``gain_mean`` / ``gain_popweighted`` (interpolated or
    extrapolated from the reference 2.0× table values), and ``benefited_pop``
    (≤ affected_pop; equal to it at the reference multiplier). Returns ``None``
    when the route id is unknown (callers handle gracefully).
    """
    row = lookup_sensitivity_row(route_id, data)
    if row is None:
        return None

    m = clamp_multiplier(multiplier)
    headway = row.get("headway_min_current")
    sav = wait_saving_min(headway, m)

    # Reference wait saving: prefer the table's stored 2.0× value; fall back to
    # the model formula when it is missing/NaN.
    sav_ref = row.get("wait_saving_min")
    if sav_ref is None or pd.isna(sav_ref) or float(sav_ref) <= 0:
        sav_ref = wait_saving_min(headway, REFERENCE_MULTIPLIER)

    gain_ratio = (sav / float(sav_ref)) if sav_ref > 0 else 0.0
    benefit_fraction = min(gain_ratio, 1.0)

    affected = row.get("affected_pop")
    affected_pop = int(affected) if affected is not None and not pd.isna(affected) else 0

    def _gain(col: str) -> float:
        ref = row.get(col)
        if ref is None or pd.isna(ref):
            return 0.0
        return float(ref) * gain_ratio

    return {
        "route_id": route_key(row.get("route_id")),
        "corridor": str(row.get("corridor", "")),
        "action": str(row.get("action", "")),
        "affected_pop": affected_pop,
        "multiplier": m,
        "wait_saving_min": sav,
        "reference_wait_saving_min": float(sav_ref),
        "gain_mean": _gain("est_access_gain_mean"),
        "gain_popweighted": _gain("est_access_gain_popweighted"),
        "benefited_pop": int(round(affected_pop * benefit_fraction)),
    }


def route_ids_serving_geoid(
    geoid: Any, data: dict[str, Any]
) -> list[str | None]:
    """Recommended route ids (by affected pop) that serve ``geoid``.

    Matches the ``geoids`` column of the recommendations table (real block-group
    attribution), ordered by ``affected_pop`` descending. Empty when the geoid
    is unknown or served by nothing.
    """
    recommendations = data["recommendations"]
    key = str(geoid).strip()
    hits: list[tuple[str | None, float]] = []
    for _, row in recommendations.iterrows():
        geoids = row.get("geoids")
        if geoids is None:
            continue
        try:
            served = [str(g) for g in geoids]
        except TypeError:
            continue
        if key in served:
            affected = row.get("affected_pop")
            pop = float(affected) if affected is not None and not pd.isna(affected) else 0.0
            hits.append((route_key(row.get("route_id")), pop))
    hits.sort(key=lambda t: t[1], reverse=True)
    return [route for route, _ in hits]


def _boundary_style(_feature: dict[str, Any]) -> dict[str, Any]:
    return {
        "color": "#1f3a5f",
        "weight": 2,
        "fillColor": "#d9e2ec",
        "fillOpacity": 0.15,
    }


def _served_style(_feature: dict[str, Any]) -> dict[str, Any]:
    return {
        "color": "#b45309",
        "weight": 2,
        "fillColor": "#f59e0b",
        "fillOpacity": 0.18,
    }


def _corridor_style(_feature: dict[str, Any]) -> dict[str, Any]:
    return {
        "color": "#b91c1c",
        "weight": 4,
        "opacity": 0.95,
        "fillColor": "#b91c1c",
        "fillOpacity": 0.6,
    }


def build_highlight_map(prepared: dict[str, Any], route_id: Any) -> folium.Map:
    """A folium map highlighting ``route_id``'s corridor + served block groups.

    Draws the Seattle boundary, the recommendation's served block groups (amber
    outline) and the recommended corridor geometry (bold red line; a point for
    the coverage-gap recommendation). Falls back to a boundary-only map when the
    route id is unknown.
    """
    boundary = prepared["boundary"]
    equity = prepared["equity_scores"]
    row = lookup_recommendation(route_id, prepared)

    bounds = boundary.total_bounds  # (minx, miny, maxx, maxy)
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    m = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap")

    folium.GeoJson(
        boundary, name="Seattle boundary", style_function=_boundary_style
    ).add_to(m)

    if row is not None:
        geoids = row.get("geoids")
        if geoids is not None:
            served_keys = {str(g) for g in geoids}
            served = equity.loc[equity["geoid"].astype(str).isin(served_keys)]
            if not served.empty:
                folium.GeoJson(
                    served, name="Served block groups", style_function=_served_style
                ).add_to(m)

        corridor_gdf = gpd.GeoDataFrame(
            {
                "corridor": [str(row.get("corridor", ""))],
                "action": [str(row.get("action", ""))],
                "geometry": [row["geometry"]],
            },
            crs="EPSG:4326",
        )
        folium.GeoJson(
            corridor_gdf,
            name="Recommended corridor",
            style_function=_corridor_style,
            tooltip=folium.GeoJsonTooltip(
                fields=["corridor", "action"],
                aliases=["Corridor", "Action"],
                sticky=True,
            ),
        ).add_to(m)
    else:
        folium.GeoJson(
            equity.head(0),
            name="Recommended corridor",
            style_function=_corridor_style,
        ).add_to(m)

    folium.LayerControl(collapsed=True).add_to(m)
    return m


def _preferred_route_key(prepared: dict[str, Any]) -> str | None:
    """Route key to seed the corridor dropdown (from current map selection).

    If a block group is selected on the map, prefer the corridor serving it;
    otherwise fall back to the corridor with the largest affected population.
    """
    try:
        selected = st.session_state.get("selected_geoid")
    except Exception:  # noqa: BLE001 - bare import / no runtime
        selected = None
    if selected:
        serving = route_ids_serving_geoid(str(selected), prepared)
        if serving:
            return serving[0]
    corridors = sensitivity_corridors(prepared)
    return corridors[0]["route_id"] if corridors else None


def _action_callout_html(action: str) -> str:
    """Styled callout for the recommendation's action text."""
    return (
        '<div style="border-left:4px solid #2563eb;background:#eff6ff;'
        'border-radius:0 8px 8px 0;padding:8px 12px;margin:4px 0 8px;'
        f'font-weight:600;color:#0f172a;">{action}</div>'
    )


def render_whatif(prepared: dict[str, Any]) -> None:
    """Render the What-if frequency explorer into the Streamlit UI.

    Pure lookups/projections are in the helpers above; this is a thin Streamlit
    layer (corridor dropdown, frequency-multiplier slider, metrics, and the
    highlighted corridor map).
    """
    corridors = sensitivity_corridors(prepared)
    if not corridors:
        st.info("No corridor recommendations are available for what-if analysis.")
        return

    options = [(c["route_id"], c["corridor"], c["affected_pop"]) for c in corridors]
    preferred = _preferred_route_key(prepared)
    labels = [opt[0] for opt in options]
    index = labels.index(preferred) if preferred in labels else 0

    def _fmt(opt: tuple[str | None, str, int | None]) -> str:
        corridor, affected = opt[1], opt[2]
        pop = f"{affected:,}" if affected is not None else "n/a"
        return f"{corridor} — ~{pop} residents"

    choice = st.selectbox(
        "Recommended corridor",
        options,
        index=index,
        format_func=_fmt,
        help="Corridors recommended by the equity analysis (Task 2.4).",
    )
    route_id = choice[0]

    multiplier = st.slider(
        "Frequency multiplier",
        min_value=FREQ_MIN,
        max_value=FREQ_MAX,
        value=FREQ_DEFAULT,
        step=0.1,
        help=(
            "× the corridor's current weekday AM-peak frequency. All estimates "
            "are interpolated/extrapolated from the precomputed sensitivity "
            "table — no live routing."
        ),
    )

    proj = what_if_projection(route_id, multiplier, prepared)
    if proj is None:
        st.warning("That corridor was not found in the sensitivity data.")
        return

    st.markdown(_action_callout_html(proj["action"]), unsafe_allow_html=True)
    st.caption(
        f"Reference scenario: {REFERENCE_MULTIPLIER:.1f}× frequency "
        f"(wait saving ≈ {proj['reference_wait_saving_min']:.2f} min). "
        "Gains scale linearly with the wait-saving ratio; affected catchment "
        "population is real data and is independent of frequency."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Affected residents (recommended area)", f"{proj['affected_pop']:,}")
    col2.metric("Newly benefiting residents", f"{proj['benefited_pop']:,}")
    col3.metric("Est. wait saving", f"{proj['wait_saving_min']:.2f} min")
    col4.metric(
        "Access improvement (mean)",
        f"+{proj['gain_mean'] * 100:.2f} pp",
        f"pop-weighted +{proj['gain_popweighted'] * 100:.2f} pp",
    )

    map_html = build_highlight_map(prepared, route_id)._repr_html_()
    st.iframe(map_html, height=480)
