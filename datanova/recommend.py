"""Rule-based transit recommendations (Task 2.4, Seattle Transit Equity Index).

Recommends concrete, deterministic service actions for block groups that are
both *high need* (``need_index >= 0.6``) and *low access* (``gap <= -0.15``),
grounded in the real GTFS network. When no block group meets the brief
thresholds (as on the prepared 2026 King County data), selection falls back to
a distribution-anchored rule — see :func:`_select_candidate_mask`:

* Each candidate block group is attributed to the dominant route serving its
  nearest stops (``network.get_closest_stops``).
* Route attribution uses a real trip→route map: ``trips.parquet`` inside the
  prepared GTFS dir when present, otherwise the raw GTFS zips'
  ``trips.txt`` (read-only; the prepared dataset intentionally omits trips).
* Frequency is measured as the number of distinct weekday AM-peak trips
  (departures 06:00–09:00) per route.
* Recommendations are aggregated per route (corridor) and ranked by affected
  population (sum of ``pop_total`` over the candidate block groups).

Public API
----------
``recommend(equity, bg_gdf, net, gtfs_dir) -> list[dict]`` — one dict per
recommendation with ``route_id, corridor, action, affected_pop, geoids`` plus
extra attributes for the app / sensitivity output.
``estimate_access_gain(rec, equity) -> float`` — analytic what-if estimate of
the overall-access gain from doubling frequency on a recommended corridor.
``recommendations_geodataframe(recs, net, equity, ...) -> gpd.GeoDataFrame``
— point / line geometries for the recommendations GeoJSON layer.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

from datanova.accessibility import ACCESS_THRESHOLDS_MIN
from datanova.equity import ACCESS_WEIGHTS, CATEGORY_ORDER
from datanova.network import get_closest_stops

# -- selection thresholds (brief: need >= 0.6 and gap <= -0.15) --------------
NEED_THRESHOLD = 0.6
GAP_THRESHOLD = -0.15
# Minimum candidate block groups for the brief thresholds to be used as-is.
# On the prepared 2026 King County data the composite need index never
# reaches 0.6 with a negative gap, so the adaptive fallback in
# ``_select_candidate_mask`` takes over (documented there).
MIN_CANDIDATES = 3

# AM-peak window (minutes since midnight): 06:00–09:00.
AM_PEAK_START_MIN = 360
AM_PEAK_END_MIN = 540

# Below this many weekday AM-peak trips / 3 h (~>15-min headway) a route is
# flagged as low frequency and the action text calls it out explicitly.
LOW_FREQ_TRIPS = 12

# Stop attribution radius around a block-group centroid (matches the network's
# walking catchment default).
STOP_ATTRIBUTION_RADIUS_M = 800.0

# Conventional ACS demographics path relative to the project root (used when
# equity has no ``pop_total`` column). ``gtfs_dir`` is
# ``<root>/data/prepared/gtfs``, so the project root is three levels up.
_ACS_RELATIVE = ("data", "prepared", "census", "acs_demographics.parquet")


def _default_acs_path(gtfs_dir: Path) -> Path:
    """Resolve the conventional ACS demographics path from a prepared GTFS dir.

    ``gtfs_dir`` is ``<root>/data/prepared/gtfs``; the project root is three
    levels up (``parents[2]``). Returns ``<root>/data/prepared/census/
    acs_demographics.parquet`` — without duplicating the ``data`` segment.
    """
    root = Path(gtfs_dir).parents[2]
    return root.joinpath(*_ACS_RELATIVE)

# ---------------------------------------------------------------------------
# Light GTFS loading helpers (prepared parquet + optional raw-zip fallback)
# ---------------------------------------------------------------------------


def _minutes_of(value) -> float:
    """'HH:MM:SS' -> minutes since midnight (hours may exceed 23)."""
    parts = str(value).split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    s = int(parts[2]) if len(parts) > 2 else 0
    return h * 60 + m + s / 60.0


def _load_routes(gtfs_dir: Path) -> pd.DataFrame:
    routes = pd.read_parquet(gtfs_dir / "routes.parquet")
    for col in ("route_id", "route_short_name"):
        if col not in routes.columns:
            raise ValueError(f"routes.parquet missing column {col!r}")
    routes["route_id"] = routes["route_id"].astype(str)
    return routes


def _load_stop_times(gtfs_dir: Path) -> pd.DataFrame:
    st = pd.read_parquet(gtfs_dir / "stop_times.parquet")
    if not {"trip_id", "stop_id", "stop_sequence", "departure_time"} <= set(st.columns):
        raise ValueError("stop_times.parquet missing required columns")
    st["trip_id"] = st["trip_id"].astype(str)
    st["stop_id"] = st["stop_id"].astype(str)
    return st


def _load_calendar(gtfs_dir: Path) -> pd.DataFrame | None:
    cal_path = gtfs_dir / "calendar.parquet"
    if not cal_path.exists():
        return None
    cal = pd.read_parquet(cal_path)
    cal["service_id"] = cal["service_id"].astype(str)
    return cal


def _load_trips_map(gtfs_dir: Path) -> pd.DataFrame | None:
    """trip_id -> route_id map: prepared trips.parquet, else raw zips.

    The prepared GTFS intentionally drops ``trips.txt``; we read it read-only
    from the raw zips when present so route attribution stays real.
    """
    prepared = gtfs_dir / "trips.parquet"
    if prepared.exists():
        t = pd.read_parquet(prepared)
        t["trip_id"] = t["trip_id"].astype(str)
        t["route_id"] = t["route_id"].astype(str)
        return t[["trip_id", "route_id"]].drop_duplicates()

    raw_gtfs = gtfs_dir.parent.parent / "raw" / "gtfs"
    frames = []
    if raw_gtfs.is_dir():
        for zp in sorted(raw_gtfs.glob("*.zip")):
            try:
                with zipfile.ZipFile(zp) as z:
                    if "trips.txt" not in z.namelist():
                        continue
                    with z.open("trips.txt") as fh:
                        trips = pd.read_csv(fh)
            except (zipfile.BadZipFile, OSError):
                continue
            if not {"trip_id", "route_id"} <= set(trips.columns):
                continue
            frames.append(trips[["trip_id", "route_id"]].astype(str))
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def _weekday_service_ids(cal: pd.DataFrame | None) -> set[str] | None:
    """service_ids active on any weekday; None = all trips treated as weekday."""
    if cal is None or cal.empty:
        return None
    day_cols = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    present = [c for c in day_cols if c in cal.columns]
    if not present:
        return None
    weekday = cal[present].fillna(0).astype(int).sum(axis=1) > 0
    return set(cal.loc[weekday, "service_id"].astype(str))


def _route_am_peak_trips(
    stop_times: pd.DataFrame,
    trips_map: pd.DataFrame | None,
    weekday_service_ids: set[str] | None,
) -> dict[str, int]:
    """Distinct weekday AM-peak trips per route (int per route)."""
    if trips_map is None:
        return {}
    st = stop_times[["trip_id", "stop_id", "departure_time"]].copy()
    st["dep_min"] = st["departure_time"].map(_minutes_of)
    st = st[(st["dep_min"] >= AM_PEAK_START_MIN) & (st["dep_min"] < AM_PEAK_END_MIN)]
    m = st.merge(trips_map, on="trip_id", how="inner")
    if weekday_service_ids is not None and "service_id" in trips_map.columns:
        m = m[m["service_id"].astype(str).isin(weekday_service_ids)]
    counts = m[["route_id", "trip_id"]].drop_duplicates().groupby("route_id").size()
    return counts.astype(int).to_dict()


def _build_stop_routes(
    stop_times: pd.DataFrame, trips_map: pd.DataFrame | None
) -> dict[str, list[str]]:
    """stop_id -> sorted unique route_ids serving it."""
    if trips_map is None:
        return {}
    m = stop_times[["trip_id", "stop_id"]].merge(
        trips_map, on="trip_id", how="inner"
    )
    m = m.drop_duplicates(subset=["stop_id", "route_id"])
    by_stop: dict[str, list[str]] = {}
    for stop_id, group in m.groupby("stop_id")["route_id"]:
        by_stop[str(stop_id)] = sorted(set(group.astype(str)))
    return by_stop


def _representative_stop_order(
    route_id: str,
    stop_times: pd.DataFrame,
    trips_map: pd.DataFrame | None,
    weekday_service_ids: set[str] | None,
) -> list[str]:
    """Ordered stop_id list for a route (representative weekday trip)."""
    if trips_map is None:
        return []
    t = trips_map[trips_map["route_id"] == route_id]
    if weekday_service_ids is not None and "service_id" in trips_map.columns:
        t = t[t["service_id"].astype(str).isin(weekday_service_ids)]
    if t.empty:
        return []
    trips_of_route = set(t["trip_id"])
    st = stop_times[stop_times["trip_id"].isin(trips_of_route)].copy()
    st["dep_min"] = st["departure_time"].map(_minutes_of)
    trip_start = st.groupby("trip_id")["dep_min"].min()
    rep = trip_start.idxmin()
    seg = st[st["trip_id"] == rep].sort_values("stop_sequence")
    return seg["stop_id"].astype(str).tolist()


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------


def _attach_pop_total(equity: pd.DataFrame, acs_path: Path) -> pd.DataFrame:
    """Fallback: pull pop_total from the conventional ACS path (read-only).

    Returns ``equity`` unchanged when ``acs_path`` is missing or lacks a
    ``pop_total`` column.
    """
    if not Path(acs_path).exists():
        return equity
    acs = pd.read_parquet(acs_path)
    if "pop_total" not in acs.columns:
        return equity
    eq = equity.copy()
    acs_map = acs[["geoid", "pop_total"]].copy()
    acs_map["geoid"] = acs_map["geoid"].astype(str)
    eq["geoid"] = eq["geoid"].astype(str)
    eq = eq.merge(acs_map, on="geoid", how="left")
    return eq


def _select_candidate_mask(eq: pd.DataFrame) -> pd.Series:
    """Deterministic candidate block-group selection (bool Series).

    Primary rule (task brief): ``need_index >= 0.6`` and ``gap <= -0.15``.
    On the prepared 2026 King County data, no block group satisfies this
    (the ACS composite need index peaks around 0.63 and zero block groups
    combine ``need_index >= 0.6`` with a negative gap). When the primary rule
    yields fewer than :data:`MIN_CANDIDATES` candidate block groups, we relax
    deterministically to distribution-anchored thresholds — ``need_index`` at
    or above its 90th percentile AND ``gap < 0`` (still *high-need and
    underserved* relative to the region). Percentiles are computed over block
    groups with finite need/gap/geometry, so the selection is stable.
    """
    base = (
        eq["need_index"].notna()
        & eq["gap"].notna()
        & eq["geometry"].notna()
    )
    primary = (
        base
        & (eq["need_index"] >= NEED_THRESHOLD)
        & (eq["gap"] <= GAP_THRESHOLD)
    )
    if int(primary.sum()) >= MIN_CANDIDATES:
        return primary
    nd = eq.loc[base, "need_index"]
    return (
        base
        & (eq["need_index"] >= nd.quantile(0.90))
        & (eq["gap"] < 0.0)
    )


def _corridor_label(route_id: str | None, short_names: dict) -> str:
    if route_id is None:
        return "Unserved area (coverage gap)"
    label = short_names.get(route_id)
    if label is not None and str(label) != "nan":
        return f"Route {label}"
    return f"Route {route_id}"


def recommend(
    equity: pd.DataFrame,
    bg_gdf: gpd.GeoDataFrame,
    net,
    gtfs_dir: Path,
    acs_path: Path | None = None,
) -> list[dict]:
    """Produce deterministic, route-grounded service recommendations.

    Parameters
    ----------
    equity:
        ``compute_equity`` output, optionally augmented with ``pop_total``
        (used for ``affected_pop``; when absent it is attempted from the
        conventional ACS path, else ``ValueError``).
    bg_gdf:
        Block-group GeoDataFrame with ``geoid`` and polygon geometry.
    net:
        The ``datanova.network.Network``.
    gtfs_dir:
        Prepared GTFS directory (``data/prepared/gtfs``); used for route and
        stop-time data plus the trip→route map (raw-zip fallback).
    acs_path:
        Optional explicit path to the ACS demographics parquet used to attach
        ``pop_total`` when ``equity`` lacks it. Defaults to the conventional
        project path (``data/prepared/census/acs_demographics.parquet``) via
        :func:`_default_acs_path`.

    Returns
    -------
    list[dict]
        One dict per recommendation, each with at least ``route_id`` (str or
        ``None`` for coverage gaps), ``corridor``, ``action``,
        ``affected_pop`` and ``geoids`` (list of block-group geoids), plus
        extra attributes used by ``run_analysis.py`` (``n_block_groups``,
        ``mean_gap``, ``mean_need``, ``mean_access_overall``,
        ``am_peak_trips``, ``headway_min_current``, ``wait_saving_min``).
        Sorted by ``affected_pop`` descending (ties by route id).
    """
    gtfs_dir = Path(gtfs_dir)
    eq = equity.copy()
    eq["geoid"] = eq["geoid"].astype(str)

    if "pop_total" not in eq.columns:
        target = acs_path if acs_path is not None else _default_acs_path(gtfs_dir)
        eq = _attach_pop_total(eq, target)
    if "pop_total" not in eq.columns:
        raise ValueError(
            "equity must include a 'pop_total' column (or acs_demographics.parquet "
            "must be available) to estimate affected population"
        )
    eq["pop_total"] = pd.to_numeric(eq["pop_total"], errors="coerce").fillna(0.0)

    # Geometry for centroids (already attached by callers such as
    # run_analysis.py when a previous merge added it; merge only if absent).
    if "geometry" not in eq.columns:
        bg = bg_gdf[["geoid", "geometry"]].copy()
        bg["geoid"] = bg["geoid"].astype(str)
        eq = eq.merge(bg, on="geoid", how="left")

    cand = eq[_select_candidate_mask(eq)].copy()
    if cand.empty:
        return []

    routes = _load_routes(gtfs_dir)
    short_names = dict(zip(routes["route_id"], routes["route_short_name"]))

    stop_times = _load_stop_times(gtfs_dir)
    trips_map = _load_trips_map(gtfs_dir)
    weekday_service_ids = _weekday_service_ids(_load_calendar(gtfs_dir))
    route_freq = _route_am_peak_trips(stop_times, trips_map, weekday_service_ids)
    stop_routes = _build_stop_routes(stop_times, trips_map)

    radius = float(getattr(net, "max_walk_m", STOP_ATTRIBUTION_RADIUS_M)) or STOP_ATTRIBUTION_RADIUS_M

    # Aggregate candidate block groups into route corridors.
    buckets: dict[tuple[str | None, str], dict] = {}
    for _, row in cand.iterrows():
        xy = (float(row["geometry"].centroid.y), float(row["geometry"].centroid.x))
        near = get_closest_stops(net, xy, radius)
        route_id: str | None = None
        if not near.empty:
            for stop_row in near.itertuples(index=False):
                stop_id = str(stop_row.stop_id)
                serving = stop_routes.get(stop_id)
                if not serving:
                    continue
                # Dominant route = highest AM-peak frequency; tie-break by id.
                route_id = max(serving, key=lambda r: (route_freq.get(r, 0), r))
                break

        corridor = _corridor_label(route_id, short_names)
        key = (route_id, corridor)
        bucket = buckets.get(key)
        if bucket is None:
            buckets[key] = {
                "route_id": route_id,
                "corridor": corridor,
                "geoids": [],
                "affected_pop": 0.0,
                "gaps": [],
                "needs": [],
                "access": [],
            }
        bucket = buckets[key]
        bucket["geoids"].append(row["geoid"])
        bucket["affected_pop"] += float(row["pop_total"])
        bucket["gaps"].append(float(row["gap"]))
        bucket["needs"].append(float(row["need_index"]))
        bucket["access"].append(float(row["access_overall"]))

    recs: list[dict] = []
    for (route_id, corridor), bucket in buckets.items():
        geoids = sorted(set(bucket["geoids"]))
        affected_pop = int(round(bucket["affected_pop"]))
        freq = route_freq.get(route_id, 0) if route_id else 0
        headway = (AM_PEAK_END_MIN - AM_PEAK_START_MIN) / max(1, freq) if route_id else None
        wait_saving = min(headway / 4.0, 3.5) if headway is not None else 0.0

        if route_id is None:
            action = (
                f"Add transit service or a new stop to serve this high-need, "
                f"low-access area (no stop within ~{radius:.0f} m of block-group "
                f"centroids)"
            )
        elif freq < LOW_FREQ_TRIPS:
            action = (
                f"Increase weekday AM-peak frequency on {corridor} "
                f"(currently ~{freq} peak trips / 3 h ≈ {headway:.0f}-min headway)"
            )
        else:
            action = (
                f"Increase weekday AM-peak frequency on {corridor} "
                f"(currently ~{freq} peak trips / 3 h)"
            )

        recs.append(
            {
                "route_id": route_id,
                "corridor": corridor,
                "action": action,
                "affected_pop": affected_pop,
                "geoids": geoids,
                "n_block_groups": len(geoids),
                "mean_gap": float(np.mean(bucket["gaps"])),
                "mean_need": float(np.mean(bucket["needs"])),
                "mean_access_overall": float(np.mean(bucket["access"])),
                "am_peak_trips": freq,
                "headway_min_current": headway,
                "wait_saving_min": wait_saving,
            }
        )

    recs.sort(key=lambda r: (-r["affected_pop"], r["route_id"] or ""))
    return recs


# ---------------------------------------------------------------------------
# What-if sensitivity (documented approximation)
# ---------------------------------------------------------------------------


def _gain_per_bg(rec: dict, equity: pd.DataFrame) -> dict[str, float]:
    """Per-geoid estimated access gain (see :func:`estimate_access_gain`)."""
    geoids = set(rec.get("geoids", []))
    saving = float(rec.get("wait_saving_min", 0.0) or 0.0)
    if not geoids or saving <= 0:
        return {g: 0.0 for g in geoids}
    sub = equity[equity["geoid"].astype(str).isin(geoids)]
    weights = np.array([ACCESS_WEIGHTS[c] for c in CATEGORY_ORDER], dtype=float)
    out: dict[str, float] = {}
    for _, row in sub.iterrows():
        num = den = 0.0
        for c, w in zip(CATEGORY_ORDER, weights):
            acc = row.get(f"{c}_access")
            if acc is None or pd.isna(acc):
                continue
            thr = float(ACCESS_THRESHOLDS_MIN[c])
            frac = min(saving / thr, 1.0)
            gain = max(0.0, 1.0 - float(acc)) * frac
            num += w * gain
            den += w
        out[str(row["geoid"])] = float(num / den) if den > 0 else 0.0
    return out


def estimate_access_gain(rec: dict, equity: pd.DataFrame) -> float:
    """Estimated overall-access gain from doubling frequency on a corridor.

    Approximation (documented in the task report): doubling frequency halves
    the expected wait. With the static network model (fixed 7-min wait per
    journey), the saving is ``min(headway_current / 4, 3.5)`` minutes. For each
    affected block group we assume opportunities are roughly uniformly
    distributed in time up to their category threshold (jobs 45, healthcare 30,
    schools 30, food 20 min), so a wait saving ``s`` makes roughly
    ``s / threshold`` of the currently-unreachable share reachable::

        gain_b = sum_c w_c * (1 - access_c,b) * min(s / threshold_c, 1)
                 / sum_c w_c        (over non-NaN categories)

    Returns the population-unweighted mean gain over the block groups in
    ``rec["geoids"]`` (0.0 when no saving applies).
    """
    gains = list(_gain_per_bg(rec, equity).values())
    return float(np.mean(gains)) if gains else 0.0


# ---------------------------------------------------------------------------
# Geo output for the recommendations layer
# ---------------------------------------------------------------------------


def recommendations_geodataframe(
    recs: list[dict],
    net,
    equity: pd.DataFrame | None = None,
    stop_times: pd.DataFrame | None = None,
    trips_map: pd.DataFrame | None = None,
    weekday_service_ids: set[str] | None = None,
) -> gpd.GeoDataFrame:
    """Points (coverage gaps) / corridor lines (routes) for the map layer.

    Corridor lines follow a route's real stop sequence (representative weekday
    trip); coverage gaps become points at the population-weighted centroid of
    the affected block groups (from ``equity`` geometry when provided).
    """
    stop_coords = {
        str(stop_id): (float(lat), float(lon))
        for stop_id, lat, lon in zip(
            net.stops["stop_id"], net.stops["stop_lat"], net.stops["stop_lon"]
        )
    }

    # Pop-weighted centroid source if equity carries geometry + pop_total.
    centroid_of: dict[str, np.ndarray] = {}
    pop_of: dict[str, float] = {}
    if equity is not None and "geometry" in equity.columns:
        e = equity[["geoid", "geometry"]].copy()
        e["geoid"] = e["geoid"].astype(str)
        if "pop_total" in equity.columns:
            pop_of = dict(
                zip(
                    equity["geoid"].astype(str),
                    pd.to_numeric(equity["pop_total"], errors="coerce"),
                )
            )
        for _, row in e.iterrows():
            if row["geometry"] is None or pd.isna(row["geometry"]):
                continue
            centroid_of[row["geoid"]] = np.array(
                [row["geometry"].centroid.y, row["geometry"].centroid.x], dtype=float
            )
    for rec in recs:
        geoids = rec.get("geoids", [])
        pts = [centroid_of[g] for g in geoids if g in centroid_of]
        if pts:
            pts = np.asarray(pts, dtype=float)
            w = np.array(
                [float(pop_of.get(geoids[i], 1.0)) for i in range(len(pts))],
                dtype=float,
            )
            if w.sum() > 0:
                rec["centroid_lat"], rec["centroid_lon"] = (
                    float(np.average(pts[:, 0], weights=w)),
                    float(np.average(pts[:, 1], weights=w)),
                )
            else:
                rec["centroid_lat"], rec["centroid_lon"] = (
                    float(np.mean(pts[:, 0])),
                    float(np.mean(pts[:, 1])),
                )

    rows = []
    for rec in recs:
        props = {k: rec[k] for k in rec if k != "geoids"}
        props["geoids"] = rec["geoids"]
        route_id = rec["route_id"]
        geom = None
        if route_id is not None and stop_times is not None and trips_map is not None:
            order = _representative_stop_order(
                route_id, stop_times, trips_map, weekday_service_ids
            )
            coords = [stop_coords[s] for s in order if s in stop_coords]
            if len(coords) >= 2:
                geom = LineString([(lon, lat) for lat, lon in coords])
        if geom is None:
            lat = rec.get("centroid_lat")
            lon = rec.get("centroid_lon")
            if lat is not None and lon is not None:
                geom = Point(lon, lat)
        rows.append((geom, props))

    return gpd.GeoDataFrame(
        [p for _, p in rows],
        geometry=[g for g, _ in rows],
        crs="EPSG:4326",
    )
