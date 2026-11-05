"""Accessibility scores per block group (Task 2.2, Seattle Transit Equity Index).

Computes, for every King County block group, a transit-access score per
opportunity category (jobs, healthcare, schools, food):

    access = sum(weight of sampled opportunities reachable within threshold)
             / sum(weight of all sampled opportunities)

Method
------
- Origins are block-group centroids (``(lat, lon)``).
- Per category, each origin samples the ``MAX_SAMPLE_PER_CATEGORY`` (25)
  nearest opportunities by straight-line (haversine) distance; categories with
  fewer opportunities than the cap are evaluated in full (exact). This bounds
  the expensive jobs category (14,991 POIs) at 25 routed opportunities per
  origin while leaving the small OSM categories exact.
- Door-to-door travel times come from the same network semantics as
  ``datanova.network.travel_time`` (walking catchments of ``max_walk_m``,
  transit Dijkstra, direct-walk fallback, fixed 7-minute waiting penalty).
  Instead of running one Dijkstra per destination (``travel_time`` is ~1.3 s
  per call on the real network), we run **one single-source Dijkstra per
  origin** and evaluate every sampled opportunity against it, and we
  precompute each opportunity's walking catchment once. This is numerically
  identical to ``travel_time`` (verified in ``tests/test_accessibility.py``)
  and makes the full 1,545-block-group run feasible (~45 s measured).
- The Dijkstra cutoff is ``max(thresholds) - waiting`` (38 min). Any stop
  farther than that cannot contribute to a reachable-within-threshold transit
  journey. When every destination stop lies beyond the cutoff, the
  direct-walk answer is still scored exactly like ``travel_time`` (which
  returns the direct walk whenever *any* transit path exists, even beyond the
  800 m catchment); a lazy reachability check distinguishes that case from a
  genuinely unreachable destination.

Coordinate convention: every ``xy`` / lat/lon array is ``(latitude,
longitude)``, matching ``network.py``.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import networkx as nx
import numpy as np
import pandas as pd

from datanova.network import (
    DEFAULT_WAITING_MIN,
    Network,
    get_closest_stops,
    haversine_m,
)

ACCESS_THRESHOLDS_MIN: dict[str, int] = {
    "jobs": 45,
    "healthcare": 30,
    "schools": 30,
    "food": 20,
}

CATEGORY_ORDER = ("jobs", "healthcare", "schools", "food")

# Cap on the number of opportunities sampled per origin per category (nearest
# by straight-line distance). Documented in the task report.
MAX_SAMPLE_PER_CATEGORY = 25

_VIRTUAL_ORIGIN = "__accessibility_virtual_origin__"

_CATCHMENT_CHUNK = 512


# ---------------------------------------------------------------------------
# Internal routing helpers (batch equivalents of network.travel_time)
# ---------------------------------------------------------------------------


def _centroid_xy(gdf) -> tuple[np.ndarray, np.ndarray]:
    """(lat, lon) arrays of a GeoDataFrame's centroid points."""
    c = gdf.geometry.centroid
    return np.asarray(c.y, dtype=float), np.asarray(c.x, dtype=float)


def _build_catchments(
    net: Network, lat: np.ndarray, lon: np.ndarray
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Precompute each opportunity's walking catchment.

    For every point (lat, lon) returns:
      - ``pos``: integer positions (row indices into ``net.stops``) of the
        stops within ``net.max_walk_m``;
      - ``walk``: walking minutes from each of those stops to the point.
    """
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    n = len(lat)
    stop_ids = net.stops["stop_id"].to_numpy()
    pos_of = {s: i for i, s in enumerate(stop_ids)}
    s_lat = net.stops["stop_lat"].to_numpy(dtype=float)
    s_lon = net.stops["stop_lon"].to_numpy(dtype=float)
    max_walk = float(net.max_walk_m)
    speed = float(net.walk_speed_kmh)

    pos_list: list[np.ndarray] = [np.empty(0, dtype=np.int64)] * n
    walk_list: list[np.ndarray] = [np.empty(0, dtype=float)] * n

    for start in range(0, n, _CATCHMENT_CHUNK):
        end = min(start + _CATCHMENT_CHUNK, n)
        d = haversine_m(
            lat[start:end, None],
            lon[start:end, None],
            s_lat[None, :],
            s_lon[None, :],
        )
        mask = d <= max_walk
        for r in range(end - start):
            m = mask[r]
            if not m.any():
                continue
            sel_ids = stop_ids[m]
            pos_list[start + r] = np.fromiter(
                (pos_of[s] for s in sel_ids),
                dtype=np.int64,
                count=int(m.sum()),
            )
            walk_list[start + r] = d[r, m] / 1000.0 / speed * 60.0

    return pos_list, walk_list


def _origin_distances(
    net: Network,
    origin_xy: tuple[float, float],
    cutoff: float | None = None,
    stop_pos_of: dict | None = None,
    return_orig: bool = False,
) -> np.ndarray | None | tuple[np.ndarray | None, pd.DataFrame]:
    """Single-source Dijkstra from an origin to every stop.

    Replicates the origin side of ``travel_time``: a transient virtual origin
    node connects to every stop within ``net.max_walk_m`` with a walking-time
    edge; a single Dijkstra then yields the door-to-stop minutes for all
    stops. Returns ``None`` when the origin has no stop in its catchment
    (everything is unreachable by transit). ``cutoff`` prunes stops beyond a
    given minute budget (exact for reachability decisions — see module doc).
    With ``return_orig=True`` a tuple ``(arr, orig_df)`` is returned where
    ``orig_df`` is the origin catchment DataFrame (used for reachability).
    """
    orig = get_closest_stops(net, origin_xy, net.max_walk_m)
    if orig.empty:
        if return_orig:
            return None, orig
        return None
    g = net.graph()
    g.add_node(_VIRTUAL_ORIGIN)
    try:
        for row in orig.itertuples(index=False):
            g.add_edge(
                _VIRTUAL_ORIGIN,
                row.stop_id,
                weight=row.dist_m / 1000.0 / net.walk_speed_kmh * 60.0,
            )
        dist = nx.single_source_dijkstra_path_length(
            g, _VIRTUAL_ORIGIN, weight="weight", cutoff=cutoff
        )
    finally:
        g.remove_node(_VIRTUAL_ORIGIN)

    arr = np.full(len(net.stops), np.inf)
    if stop_pos_of is None:
        stop_pos_of = {s: i for i, s in enumerate(net.stops["stop_id"].to_numpy())}
    for s, val in dist.items():
        j = stop_pos_of.get(s)
        if j is not None:
            arr[j] = val
    if return_orig:
        return arr, orig
    return arr


def _reachable_any(
    orig_df: pd.DataFrame,
    pos: np.ndarray,
    reach_cache: dict,
    net: Network,
    stop_pos_of: dict,
) -> bool:
    """Whether any stop in ``pos`` is reachable (any path) from the origin.

    Used only to resolve the pruned-cutoff ambiguity: when every destination
    catchment stop lies beyond the Dijkstra cutoff, ``travel_time`` still
    returns the direct walk (unconditionally) as long as *some* transit path
    exists — even one slower than the cutoff. ``reach_cache`` memoizes the
    reachable-stop mask per origin catchment (a frozenset of stop ids).
    """
    if orig_df.empty:
        return False
    key = tuple(sorted(map(str, orig_df["stop_id"].tolist())))
    mask = reach_cache.get(key)
    if mask is None:
        g = net.graph()
        g.add_node(_VIRTUAL_ORIGIN)
        try:
            for row in orig_df.itertuples(index=False):
                g.add_edge(_VIRTUAL_ORIGIN, row.stop_id, weight=1.0)
            reach = nx.descendants(g, _VIRTUAL_ORIGIN)
        finally:
            g.remove_node(_VIRTUAL_ORIGIN)
        mask = np.zeros(len(net.stops), dtype=bool)
        for s in reach:
            j = stop_pos_of.get(s)
            if j is not None:
                mask[j] = True
        reach_cache[key] = mask
    return bool(mask[pos].any())


def _pair_minutes(
    net: Network,
    origin_xy: tuple[float, float],
    dest_xy: tuple[float, float],
    d_arr: np.ndarray | None = None,
    stop_pos_of: dict | None = None,
    waiting_min: float = DEFAULT_WAITING_MIN,
    pruned: bool = False,
    get_reachable: Callable[[], np.ndarray] | None = None,
) -> float | None:
    """Door-to-door minutes for one pair — batch equivalent of ``travel_time``.

    If ``d_arr`` is given (from ``_origin_distances``) it is reused; otherwise
    it is computed here with no cutoff (full-graph parity with
    ``travel_time``). ``pruned=True`` signals that ``d_arr`` came from a
    cutoff-limited search, so an all-``inf`` destination is ambiguous: its
    stops may lie beyond the cutoff rather than be unreachable. In that case
    ``get_reachable`` must supply a boolean mask over stop positions of stops
    reachable from the origin, so the direct-walk-competes case resolves
    exactly like ``travel_time`` (which returns ``direct_walk`` whenever any
    transit path exists, even beyond the 800 m catchment).
    """
    ox, oy = float(origin_xy[0]), float(origin_xy[1])
    dx, dy = float(dest_xy[0]), float(dest_xy[1])
    direct_m = float(haversine_m(ox, oy, dx, dy))
    direct_walk = direct_m / 1000.0 / net.walk_speed_kmh * 60.0

    if d_arr is None:
        d_arr = _origin_distances(net, origin_xy, cutoff=None, stop_pos_of=stop_pos_of)
        pruned = False
        if d_arr is None:
            # Origin has no stop in its catchment -> travel_time returns None.
            return None

    dest = get_closest_stops(net, dest_xy, net.max_walk_m)
    if dest.empty:
        # Destination has no stop in its catchment -> travel_time returns None.
        return None
    if stop_pos_of is None:
        stop_pos_of = {s: i for i, s in enumerate(net.stops["stop_id"].to_numpy())}
    pos = np.array([stop_pos_of[s] for s in dest["stop_id"]], dtype=np.int64)
    if pos.size == 0:
        return None

    wlk = (
        dest["dist_m"].to_numpy(dtype=float)
        / 1000.0
        / net.walk_speed_kmh
        * 60.0
    )
    best = float((d_arr[pos] + wlk).min())

    if math.isinf(best):
        if direct_m <= net.max_walk_m:
            # Both branches of travel_time agree here: the direct walk is the
            # answer (it beats the slow/missing transit).
            return direct_walk
        if pruned:
            # Transit may exist but lie beyond the cutoff. travel_time returns
            # min(best + waiting, direct_walk) unconditionally whenever a
            # transit path exists, so a direct walk longer than max_walk_m can
            # still win (it beats the slow pruned transit). Confirm that some
            # transit path actually exists before returning it.
            reach = get_reachable() if get_reachable is not None else None
            if reach is not None and reach[pos].any():
                return direct_walk
            return None
        # Full (unpruned) search: best == inf means genuinely no transit path.
        return None
    return min(best + waiting_min, direct_walk)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_access_scores(
    bg_gdf,
    opps: dict[str, object],
    net: Network,
    sample_per_category: int | None = None,
) -> pd.DataFrame:
    """Compute per-block-group accessibility scores.

    Parameters
    ----------
    bg_gdf:
        GeoDataFrame of block groups with ``geoid`` and polygon geometry
        (centroids are the origins).
    opps:
        Mapping ``category -> GeoDataFrame`` of opportunity POIs with
        ``geometry`` (points) and, optionally, a ``weight`` column. Categories
        with no data produce NaN scores. Only the four ``CATEGORY_ORDER``
        categories are scored (extra keys are ignored).
    net:
        The routable transit :class:`Network` (Task 2.1).
    sample_per_category:
        Maximum opportunities sampled per origin per category (default:
        ``MAX_SAMPLE_PER_CATEGORY`` = 25; smaller categories are exact).

    Returns
    -------
    pd.DataFrame
        Columns ``geoid`` + one score per category (``jobs_access``,
        ``healthcare_access``, ``schools_access``, ``food_access``), each in
        [0, 1] or NaN. Rows match ``bg_gdf`` order.
    """
    if sample_per_category is None:
        sample_per_category = MAX_SAMPLE_PER_CATEGORY
    sample_per_category = int(sample_per_category)
    if sample_per_category < 1:
        raise ValueError("sample_per_category must be >= 1")

    lat_o, lon_o = _centroid_xy(bg_gdf)
    n_orig = len(lat_o)
    stop_pos_of = {s: i for i, s in enumerate(net.stops["stop_id"].to_numpy())}

    # --- per-category preparation ---------------------------------------
    cats: dict[str, dict | None] = {}
    for cat in CATEGORY_ORDER:
        gdf = opps.get(cat)
        if gdf is None or len(gdf) == 0:
            cats[cat] = None
            continue

        lat_c, lon_c = _centroid_xy(gdf)
        if "weight" in gdf.columns:
            w = gdf["weight"].astype(float).to_numpy()
            w = np.where(np.isfinite(w) & (w > 0), w, 0.0)
        else:
            w = np.ones(len(gdf), dtype=float)
        pos, walk = _build_catchments(net, lat_c, lon_c)

        k = min(sample_per_category, len(gdf))
        samples: list[np.ndarray] = []
        for i in range(n_orig):
            d = haversine_m(lat_o[i], lon_o[i], lat_c, lon_c)
            if k == len(gdf):
                idx = np.arange(k, dtype=np.int64)
            else:
                part = np.argpartition(d, k - 1)[:k]
                part = part[np.argsort(d[part], kind="stable")]
                idx = part.astype(np.int64)
            samples.append(idx)

        cats[cat] = {
            "lat": lat_c,
            "lon": lon_c,
            "weight": w,
            "pos": pos,
            "walk": walk,
            "samples": samples,
        }

    # Exact pruning cutoff for the reachability decision: a journey is
    # reachable within threshold T only if some catchment stop is within
    # T - waiting minutes (the remaining walk is non-negative).
    cutoff = float(max(ACCESS_THRESHOLDS_MIN.values()) - DEFAULT_WAITING_MIN)
    scores = {cat: np.full(n_orig, np.nan) for cat in CATEGORY_ORDER}

    # --- per-origin routing (one Dijkstra serves all categories) ----------
    reach_cache: dict[tuple, np.ndarray] = {}
    for i in range(n_orig):
        origin_xy = (float(lat_o[i]), float(lon_o[i]))
        d_arr, orig_df = _origin_distances(
            net, origin_xy, cutoff=cutoff, stop_pos_of=stop_pos_of, return_orig=True
        )

        for cat in CATEGORY_ORDER:
            info = cats[cat]
            if info is None:
                continue
            thr = float(ACCESS_THRESHOLDS_MIN[cat])
            lat_c, lon_c, w = info["lat"], info["lon"], info["weight"]
            pos_l, walk_l = info["pos"], info["walk"]

            den = 0.0
            num = 0.0
            for j in info["samples"][i]:
                wj = w[j]
                den += wj
                direct_m = float(haversine_m(lat_o[i], lon_o[i], lat_c[j], lon_c[j]))
                direct_walk = direct_m / 1000.0 / net.walk_speed_kmh * 60.0

                pj = pos_l[j]
                if d_arr is None or pj.size == 0:
                    # Origin or destination has no stop in its catchment ->
                    # travel_time returns None (unreachable).
                    continue

                best = float((d_arr[pj] + walk_l[j]).min())
                if math.isinf(best):
                    if direct_m <= net.max_walk_m:
                        # Direct walk wins and is within the permitted catchment.
                        val = direct_walk
                    elif direct_walk <= thr:
                        # Direct walk beats a transit itinerary that was pruned
                        # by the cutoff. travel_time returns direct_walk here
                        # whenever ANY transit path exists (even beyond 800 m),
                        # so confirm reachability before scoring.
                        if _reachable_any(
                            orig_df, pj, reach_cache, net, stop_pos_of
                        ):
                            val = direct_walk
                        else:
                            continue
                    else:
                        continue
                else:
                    val = min(best + DEFAULT_WAITING_MIN, direct_walk)

                if val <= thr:
                    num += wj

            scores[cat][i] = num / den if den > 0 else np.nan

    out = pd.DataFrame({"geoid": bg_gdf["geoid"].to_numpy()})
    for cat in CATEGORY_ORDER:
        out[f"{cat}_access"] = scores[cat]
    return out
