"""Tests for Task 2.1: transit network builder + router (datanova/network.py).

Run: `.venv/bin/python -m pytest tests/test_network.py -q`

Integration tests use the real Phase‑1 prepared GTFS data
(``data/prepared/gtfs/``); micro‑fixture tests cover pure algorithm logic with
a tiny synthetic network.
"""

import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from datanova.network import (  # noqa: E402
    EDGE_KIND_TRANSIT,
    EDGE_KIND_WALK,
    Network,
    build_network,
    get_closest_stops,
    haversine_m,
    travel_time,
)

GTFS_DIR = PROJECT_ROOT / "data" / "prepared" / "gtfs"

# Real stops used by the integration tests (Seattle downtown):
#   stop 431  -> "3rd Ave & Pike St"      (47.609791, -122.337959)
#   stop 1619 -> "Westlake And 7th"       (47.614864, -122.337860)
#   stop 501  -> "Pioneer Square" (ST)    (47.602139, -122.331055)
STOP_431_XY = (47.609791, -122.337959)
STOP_1619_XY = (47.614864, -122.337860)
STOP_501_XY = (47.602139, -122.331055)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def real_network() -> Network:
    """Build the real network once per test session (takes a few seconds)."""
    return build_network(GTFS_DIR)


@pytest.fixture()
def micro_network() -> Network:
    """4-stop transit chain A->B->C->D plus an isolated stop E.

    Stop spacing is ~1.1 km so no walking edges are generated; the graph is
    purely the transit chain (A, B, C, D connected; E isolated).
    """
    stops = pd.DataFrame(
        {
            "stop_id": pd.array(["A", "B", "C", "D", "E"], dtype="string"),
            "stop_name": ["A", "B", "C", "D", "E"],
            "stop_lat": [47.610, 47.620, 47.630, 47.640, 47.650],
            "stop_lon": [-122.340] * 5,
            "source": ["fixture"] * 5,
        }
    )
    edges = pd.DataFrame(
        {
            "from_stop": ["A", "B", "C"],
            "to_stop": ["B", "C", "D"],
            "weight_min": [5.0, 3.0, 4.0],
            "kind": [EDGE_KIND_TRANSIT] * 3,
        }
    )
    return Network(stops=stops, edges=edges)


# ---------------------------------------------------------------------------
# Real-data integration: network shape and schema
# ---------------------------------------------------------------------------


def test_build_network_real_scale(real_network: Network) -> None:
    net = real_network
    assert len(net.stops) > 5000
    assert len(net.edges) > 0
    kinds = set(net.edges["kind"])
    assert EDGE_KIND_TRANSIT in kinds
    assert EDGE_KIND_WALK in kinds
    assert (net.edges["weight_min"] >= 0).all()
    # Every edge endpoint is a node.
    stop_ids = set(net.stops["stop_id"])
    endpoints = set(net.edges["from_stop"]) | set(net.edges["to_stop"])
    assert endpoints <= stop_ids
    # All stops are nodes even if they have no edges.
    assert net.graph().number_of_nodes() == len(net.stops)


def test_real_network_edge_counts_reasonable(real_network: Network) -> None:
    counts = real_network.edges["kind"].value_counts()
    assert counts.get(EDGE_KIND_TRANSIT, 0) > 1000
    assert counts.get(EDGE_KIND_WALK, 0) > 10_000


def test_real_network_connects_downtown(real_network: Network) -> None:
    """Pioneer Square (ST) and Westlake are connected by in-vehicle edges."""
    assert nx.has_path(real_network.graph(), "501", "1619")


# ---------------------------------------------------------------------------
# Real-data integration: travel time and closest stops
# ---------------------------------------------------------------------------


def test_travel_time_known_pair_finite(real_network: Network) -> None:
    t = travel_time(real_network, STOP_431_XY, STOP_1619_XY)
    assert t is not None
    assert 0 < t < 90


def test_travel_time_downtown_pair_finite(real_network: Network) -> None:
    t = travel_time(real_network, STOP_501_XY, STOP_1619_XY)
    assert t is not None
    assert 0 < t < 90


def test_travel_time_identical_points_is_walk_only(real_network: Network) -> None:
    t = travel_time(real_network, STOP_431_XY, STOP_431_XY)
    assert t is not None
    assert t < 1.0


def test_travel_time_no_catchment_returns_none(real_network: Network) -> None:
    # A point in eastern Washington is far outside any stop catchment.
    t = travel_time(real_network, (47.0, -122.0), STOP_431_XY)
    assert t is None


def test_get_closest_stops_real(real_network: Network) -> None:
    df = get_closest_stops(real_network, STOP_431_XY, 800.0)
    assert list(df.columns) == ["stop_id", "dist_m"]
    assert not df.empty
    assert df.iloc[0]["stop_id"] == "431"
    assert df.iloc[0]["dist_m"] == pytest.approx(0.0, abs=1.0)
    distances = df["dist_m"].to_numpy()
    assert (distances[1:] >= distances[:-1]).all()


# ---------------------------------------------------------------------------
# Micro-fixture: pure algorithm logic
# ---------------------------------------------------------------------------


def test_micro_shortest_path_exact(micro_network: Network) -> None:
    a_xy = (47.610, -122.340)
    d_xy = (47.640, -122.340)
    # 5 + 3 + 4 = 12 transit minutes + 7 min waiting = 19.
    assert travel_time(micro_network, a_xy, d_xy) == pytest.approx(19.0)


def test_micro_unreachable_returns_none(micro_network: Network) -> None:
    a_xy = (47.610, -122.340)
    e_xy = (47.650, -122.340)  # isolated stop, no in/out edges
    assert travel_time(micro_network, a_xy, e_xy) is None


def test_micro_origin_outside_catchment_returns_none(
    micro_network: Network,
) -> None:
    far_origin = (47.700, -122.340)  # > 5 km from every stop
    d_xy = (47.640, -122.340)
    assert travel_time(micro_network, far_origin, d_xy) is None


def test_micro_direct_walk_fallback(micro_network: Network) -> None:
    near = (47.6101, -122.340)  # ~11 m from stop A
    t = travel_time(micro_network, (47.610, -122.340), near)
    assert t is not None
    # ~11 m at 5 km/h ≈ 0.13 min (direct walk beats the transit itinerary).
    assert t == pytest.approx(0.133, abs=0.02)


def test_micro_closest_stops_clamping(micro_network: Network) -> None:
    a_xy = (47.610, -122.340)
    df = get_closest_stops(micro_network, a_xy, 1500.0)
    assert list(df["stop_id"]) == ["A", "B"]
    assert df.iloc[0]["dist_m"] == pytest.approx(0.0)
    assert df.iloc[1]["dist_m"] == pytest.approx(1111.95, rel=1e-3)
    # Radius too small around a distant point -> empty.
    far_xy = (47.67, -122.340)  # ~2.2 km from the nearest stop
    assert get_closest_stops(micro_network, far_xy, 500.0).empty


def test_validate_rejects_negative_weight(micro_network: Network) -> None:
    bad = Network(stops=micro_network.stops.copy(), edges=micro_network.edges.copy())
    bad.edges.loc[0, "weight_min"] = -1.0
    with pytest.raises(ValueError, match="negative"):
        bad.validate()


def test_validate_rejects_unknown_stop(micro_network: Network) -> None:
    edges = micro_network.edges.copy()
    edges.loc[0, "to_stop"] = "ZZZ"
    bad = Network(stops=micro_network.stops.copy(), edges=edges)
    with pytest.raises(ValueError, match="unknown"):
        bad.validate()


def test_graph_walk_edges_are_undirected(micro_network: Network) -> None:
    stops = micro_network.stops.copy()
    edges = pd.concat(
        [
            micro_network.edges,
            pd.DataFrame(
                {
                    "from_stop": ["A"],
                    "to_stop": ["E"],
                    "weight_min": [10.0],
                    "kind": [EDGE_KIND_WALK],
                }
            ),
        ],
        ignore_index=True,
    )
    net = Network(stops=stops, edges=edges)
    g = net.graph()
    assert g.has_edge("A", "E")
    assert g.has_edge("E", "A")


def test_haversine_basics() -> None:
    assert haversine_m(47.61, -122.33, 47.61, -122.33) == pytest.approx(0.0)
    d = haversine_m(47.61, -122.33, 47.62, -122.33)
    # 0.01 deg latitude ~= 1.11 km.
    assert d == pytest.approx(1111.95, rel=1e-3)
    assert haversine_m(47.61, -122.33, 47.62, -122.33) == pytest.approx(
        haversine_m(47.62, -122.33, 47.61, -122.33)
    )
