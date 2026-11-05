"""Transit network builder + router (Task 2.1, Seattle Transit Equity Index).

Reads the Phase‑1 prepared GTFS parquet files (real King County Metro + Sound
Transit data, ``data/prepared/gtfs/``) and builds a routable graph:

* **Nodes** = stops (all stops from ``stops.parquet``, including stops with no
  transit service — they remain nodes and may still connect via walking edges).
* **In‑vehicle edges** between consecutive stops of the same trip. The travel
  time of a stop pair is the *median* over the whole merged schedule, which is
  a representative value for the weekday network (segment travel times are
  essentially day‑invariant; see the report for the exact rationale).
* **Walking edges** between stops within ``max_walk_m`` (haversine distance),
  timed at ``walk_speed_kmh``.

Door‑to‑door travel times are computed with Dijkstra (networkx) from a virtual
origin node to each destination stop, adding walking catchments at both ends
and a fixed waiting penalty, falling back to direct pedestrian travel when it
is the fastest option.

Coordinate convention: every ``xy`` tuple is ``(latitude, longitude)``.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants / defaults
# ---------------------------------------------------------------------------

EARTH_RADIUS_M = 6_371_008.8
DEFAULT_WALK_SPEED_KMH = 5.0
DEFAULT_MAX_WALK_M = 800.0
DEFAULT_WAITING_MIN = 7.0  # fixed waiting penalty per journey (see module docs)

EDGE_KIND_TRANSIT = "transit"
EDGE_KIND_WALK = "walk"

EDGE_COLUMNS = ["from_stop", "to_stop", "weight_min", "kind"]
EDGE_KINDS = (EDGE_KIND_TRANSIT, EDGE_KIND_WALK)

# Virtual Dijkstra terminal nodes (cannot collide with real stop ids: stop ids
# are numeric strings / GTFS codes, never these reserved labels).
_VIRTUAL_ORIGIN = "__virtual_origin__"


def haversine_m(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Vectorized haversine great‑circle distance in meters."""
    lat1 = np.asarray(lat1, dtype=float)
    lon1 = np.asarray(lon1, dtype=float)
    lat2 = np.asarray(lat2, dtype=float)
    lon2 = np.asarray(lon2, dtype=float)
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = phi2 - phi1
    dlambda = np.radians(lon2 - lon1)
    a = (
        np.sin(dphi / 2.0) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def _clock_to_minutes(value: str) -> float:
    """Convert ``'HH:MM:SS'`` -> minutes since midnight (hours may exceed 23,
    as GTFS allows > 24:00 for service crossing midnight)."""
    parts = str(value).split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    s = int(parts[2]) if len(parts) > 2 else 0
    return h * 60 + m + s / 60.0


def _walk_minutes(dist_m: float, walk_speed_kmh: float) -> float:
    """Walking time in minutes for a distance in meters."""
    return dist_m / 1000.0 / walk_speed_kmh * 60.0


# ---------------------------------------------------------------------------
# Network dataclass
# ---------------------------------------------------------------------------


@dataclass
class Network:
    """A routable transit network.

    Attributes
    ----------
    stops:
        DataFrame with at least ``stop_id, stop_name, stop_lat, stop_lon``
        (one row per node; a stop with no edges is still a node).
    edges:
        DataFrame with columns ``from_stop, to_stop, weight_min, kind``.
        ``kind`` is ``"transit"`` (directed, in‑vehicle) or ``"walk"``
        (undirected, pedestrian transfer).
    walk_speed_kmh:
        Walking speed used to time walking edges (default 5.0).
    max_walk_m:
        Maximum walking distance for transfer/catchment edges (default 800.0).
    """

    stops: pd.DataFrame
    edges: pd.DataFrame
    walk_speed_kmh: float = DEFAULT_WALK_SPEED_KMH
    max_walk_m: float = DEFAULT_MAX_WALK_M

    # Lazy cache of the networkx graph; built by ``graph()``.
    _graph: nx.DiGraph | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.stops = self.stops.reset_index(drop=True)
        self.edges = self.edges.reset_index(drop=True)

    # -- validation --------------------------------------------------------

    def validate(self) -> None:
        """Check structural invariants; raise ``ValueError`` on violation."""
        required = {"from_stop", "to_stop", "weight_min", "kind"}
        missing = required - set(self.edges.columns)
        if missing:
            raise ValueError(f"edges missing required columns: {sorted(missing)}")
        if "stop_id" not in self.stops.columns:
            raise ValueError("stops missing required column 'stop_id'")
        if self.edges.empty:
            raise ValueError("network has no edges")
        bad_kinds = set(self.edges["kind"]) - set(EDGE_KINDS)
        if bad_kinds:
            raise ValueError(f"unknown edge kind(s): {sorted(bad_kinds)}")
        if pd.isna(self.edges["weight_min"]).any():
            raise ValueError("edges contain NaN weight_min")
        if (self.edges["weight_min"] < 0).any():
            raise ValueError("edges contain negative weight_min")
        stop_ids = set(self.stops["stop_id"])
        endpoints = set(self.edges["from_stop"]) | set(self.edges["to_stop"])
        unknown = endpoints - stop_ids
        if unknown:
            sample = sorted(map(str, unknown))[:5]
            raise ValueError(f"edges reference unknown stops: {sample}")

    # -- graph --------------------------------------------------------------

    def graph(self) -> nx.DiGraph:
        """Return the directed graph (built once, cached).

        Note: walking edge weights are taken from ``self.edges`` verbatim, so
        construct the Network (e.g. via :func:`build_network`) with the desired
        ``walk_speed_kmh`` / ``max_walk_m`` before first use.
        """
        if self._graph is None:
            self._graph = _build_graph(self)
        return self._graph


def _build_graph(net: Network) -> nx.DiGraph:
    g = nx.DiGraph()
    for stop_id in net.stops["stop_id"]:
        g.add_node(stop_id)
    for row in net.edges.itertuples(index=False):
        frm, to, weight, kind = row.from_stop, row.to_stop, row.weight_min, row.kind
        g.add_edge(frm, to, weight=float(weight))
        if kind == EDGE_KIND_WALK:
            g.add_edge(to, frm, weight=float(weight))
    return g


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _transit_edges(stop_times: pd.DataFrame) -> pd.DataFrame:
    """Median in‑vehicle travel time per directed consecutive-stop pair."""
    st = stop_times.copy()
    st["arr_min"] = st["arrival_time"].map(_clock_to_minutes)
    st["dep_min"] = st["departure_time"].map(_clock_to_minutes)
    st = st.sort_values(["trip_id", "stop_sequence"], kind="mergesort")

    prev_stop = st.groupby("trip_id", sort=False)["stop_id"].shift(1)
    prev_dep = st.groupby("trip_id", sort=False)["dep_min"].shift(1)

    seg = pd.DataFrame(
        {
            "from_stop": prev_stop,
            "to_stop": st["stop_id"],
            "weight_min": st["arr_min"] - prev_dep,
        }
    )
    seg = seg.dropna(subset=["from_stop", "to_stop", "weight_min"])
    # Skip zero/negative segments (non-monotonic times, same-stop entries).
    seg = seg[seg["weight_min"] > 0]

    med = (
        seg.groupby(["from_stop", "to_stop"], sort=False)["weight_min"]
        .median()
        .reset_index()
    )
    med["kind"] = EDGE_KIND_TRANSIT
    return med[EDGE_COLUMNS]


def _walk_edges(stops: pd.DataFrame, max_walk_m: float, speed_kmh: float) -> pd.DataFrame:
    """Undirected walking edges between stops within ``max_walk_m``.

    Uses a uniform spatial grid (cell size >= ``max_walk_m``) so that any two
    stops within range are guaranteed to fall in the same or an adjacent cell;
    candidate pairs are then filtered with exact haversine distances.
    """
    lat = stops["stop_lat"].to_numpy(dtype=float)
    lon = stops["stop_lon"].to_numpy(dtype=float)
    stop_ids = stops["stop_id"].to_numpy()
    n = len(stops)
    if n == 0 or max_walk_m <= 0:
        return pd.DataFrame(columns=EDGE_COLUMNS)

    # Local planar projection (equirectangular around the mean latitude).
    mean_lat_rad = float(np.radians(lat).mean())
    x = EARTH_RADIUS_M * np.radians(lon) * np.cos(mean_lat_rad)
    y = EARTH_RADIUS_M * np.radians(lat)

    cell = max(1, int(math.ceil(max_walk_m)))
    cell_ix = np.floor(x / cell).astype(np.int64)
    cell_iy = np.floor(y / cell).astype(np.int64)

    by_cell: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i in range(n):
        by_cell[(int(cell_ix[i]), int(cell_iy[i]))].append(i)

    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)
    cos_lat = np.cos(lat_rad)

    pairs: dict[tuple[int, int], float] = {}
    for (cx, cy) in sorted(by_cell):
        neighbor_idx: list[int] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor_idx.extend(by_cell.get((cx + dx, cy + dy), ()))
        nb = np.asarray(neighbor_idx, dtype=np.int64)
        la = lat_rad[nb]
        lo = lon_rad[nb]
        for s in sorted(by_cell[(cx, cy)]):
            dphi = la - lat_rad[s]
            dlambda = lo - lon_rad[s]
            a = (
                np.sin(dphi / 2.0) ** 2
                + cos_lat[s] * np.cos(la) * np.sin(dlambda / 2.0) ** 2
            )
            dist = 2.0 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))
            hit = np.nonzero((dist <= max_walk_m) & (nb != s))[0]
            for j in hit:
                t = int(nb[j])
                key = (s, t) if s < t else (t, s)
                pairs[key] = float(dist[j])

    rows = [
        (stop_ids[a], stop_ids[b], _walk_minutes(d, speed_kmh), EDGE_KIND_WALK)
        for (a, b), d in pairs.items()
    ]
    walk = pd.DataFrame(rows, columns=EDGE_COLUMNS)
    walk["from_stop"] = walk["from_stop"].astype(stops["stop_id"].dtype)
    walk["to_stop"] = walk["to_stop"].astype(stops["stop_id"].dtype)
    return walk


def build_network(gtfs_dir: Path) -> Network:
    """Build a :class:`Network` from the Phase‑1 prepared GTFS parquet files.

    Parameters
    ----------
    gtfs_dir:
        Directory containing ``stops.parquet`` and ``stop_times.parquet``
        (route/calendar files are not needed to build travel-time edges).
    """
    gtfs_dir = Path(gtfs_dir)
    stops = pd.read_parquet(gtfs_dir / "stops.parquet")
    stop_times = pd.read_parquet(gtfs_dir / "stop_times.parquet")

    for col in ["stop_id", "stop_name", "stop_lat", "stop_lon"]:
        if col not in stops.columns:
            raise ValueError(f"stops.parquet missing column {col!r}")
    for col in ["trip_id", "stop_id", "stop_sequence", "arrival_time", "departure_time"]:
        if col not in stop_times.columns:
            raise ValueError(f"stop_times.parquet missing column {col!r}")

    transit = _transit_edges(stop_times)
    walk = _walk_edges(stops, DEFAULT_MAX_WALK_M, DEFAULT_WALK_SPEED_KMH)
    edges = pd.concat([transit, walk], ignore_index=True).sort_values(
        ["kind", "from_stop", "to_stop"]
    )

    net = Network(stops=stops, edges=edges)
    net.validate()
    return net


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def get_closest_stops(net: Network, xy: tuple[float, float], radius_m: float) -> pd.DataFrame:
    """Stops within ``radius_m`` of ``xy`` = ``(lat, lon)``.

    Returns a DataFrame with columns ``stop_id, dist_m`` sorted by distance.
    """
    lat0, lon0 = float(xy[0]), float(xy[1])
    dist = haversine_m(lat0, lon0, net.stops["stop_lat"], net.stops["stop_lon"])
    mask = dist <= radius_m
    out = pd.DataFrame(
        {
            "stop_id": net.stops.loc[mask, "stop_id"].to_numpy(),
            "dist_m": dist[mask],
        }
    )
    return out.sort_values("dist_m").reset_index(drop=True)


def travel_time(
    net: Network,
    origin_xy: tuple[float, float],
    dest_xy: tuple[float, float],
    depart_min: int = 480,
    waiting_min: float = DEFAULT_WAITING_MIN,
) -> float | None:
    """Door‑to‑door travel time in minutes between two points.

    Parameters
    ----------
    net:
        The network to route on.
    origin_xy, dest_xy:
        ``(latitude, longitude)`` tuples.
    depart_min:
        Departure time (minutes since midnight). The network is static
        (time‑independent), so this is accepted for interface compatibility and
        reserved for future frequency‑based modeling; it does not affect the
        result.
    waiting_min:
        Fixed waiting penalty in minutes, added once per completed journey.
        A single per‑journey value is used instead of a per‑boarding penalty
        because route/line membership is not present in the prepared dataset
        (no ``trips.txt``), so boardings cannot be counted.

    Returns
    -------
    float | None
        Total minutes (walk + transit + walk + waiting), or ``None`` when the
        origin or destination has no stop within ``net.max_walk_m`` and no
        direct walking fallback is available, or when no path exists.
    """
    orig = get_closest_stops(net, origin_xy, net.max_walk_m)
    dest = get_closest_stops(net, dest_xy, net.max_walk_m)
    if orig.empty or dest.empty:
        return None

    # Direct pedestrian fallback (e.g. identical points -> ~0 min).
    direct_m = float(haversine_m(origin_xy[0], origin_xy[1], dest_xy[0], dest_xy[1]))
    direct_walk = _walk_minutes(direct_m, net.walk_speed_kmh)

    g = net.graph()
    g.add_node(_VIRTUAL_ORIGIN)
    try:
        for row in orig.itertuples(index=False):
            g.add_edge(_VIRTUAL_ORIGIN, row.stop_id, weight=row.dist_m / 1000.0 / net.walk_speed_kmh * 60.0)
        best = float("inf")
        for row in dest.itertuples(index=False):
            try:
                tt = nx.dijkstra_path_length(g, _VIRTUAL_ORIGIN, row.stop_id, weight="weight")
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            dest_walk = row.dist_m / 1000.0 / net.walk_speed_kmh * 60.0
            best = min(best, tt + dest_walk)
    finally:
        g.remove_node(_VIRTUAL_ORIGIN)

    if math.isinf(best):
        # No transit path: fall back to walking only if the direct hop is
        # within the walking catchment radius.
        return direct_walk if direct_m <= net.max_walk_m else None
    return min(best + waiting_min, direct_walk)
