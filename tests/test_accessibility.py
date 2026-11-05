"""Tests for Task 2.2: accessibility scores per block group.

Run: `.venv/bin/python -m pytest tests/test_accessibility.py -q`

- Integration tests use the real prepared inputs (block groups, opportunities,
  GTFS network) and assert score shape/range plus a non-zero jobs mean.
- Micro-fixture tests use a synthetic 2-origin x 3-opportunity setup to assert
  threshold behavior, weighting, zero-opportunity -> NaN and all-unreachable
  -> 0, and exact parity with ``network.travel_time``.
"""

import sys
import time
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from datanova.accessibility import (  # noqa: E402
    ACCESS_THRESHOLDS_MIN,
    CATEGORY_ORDER,
    MAX_SAMPLE_PER_CATEGORY,
    compute_access_scores,
    _origin_distances,
    _pair_minutes,
)
from datanova.network import (  # noqa: E402
    EDGE_KIND_TRANSIT,
    Network,
    build_network,
    get_closest_stops,
    haversine_m,
    travel_time,
)

GTFS_DIR = PROJECT_ROOT / "data" / "prepared" / "gtfs"
BG_PATH = PROJECT_ROOT / "data" / "prepared" / "census" / "block_groups.geojson"
OPP_DIR = PROJECT_ROOT / "data" / "prepared" / "opportunities"


# ---------------------------------------------------------------------------
# Micro fixture: 2 origins x 3 opportunities
# ---------------------------------------------------------------------------

# Stops ~5 km apart along latitude 47.61 -> 47.745; transit chain A->B->C,
# E isolated. No walking edges. So each destination's catchment is exactly its
# own stop, and direct walks are far outside the 800 m catchment (except the
# identical-point case).
_A = (47.610, -122.340)
_B = (47.655, -122.340)
_C = (47.700, -122.340)
_E = (47.745, -122.340)


@pytest.fixture()
def micro_network() -> Network:
    stops = pd.DataFrame(
        {
            "stop_id": pd.array(["A", "B", "C", "E"], dtype="string"),
            "stop_name": ["A", "B", "C", "E"],
            "stop_lat": [a[0] for a in (_A, _B, _C, _E)],
            "stop_lon": [a[1] for a in (_A, _B, _C, _E)],
        }
    )
    edges = pd.DataFrame(
        {
            "from_stop": ["A", "B"],
            "to_stop": ["B", "C"],
            "weight_min": [25.0, 25.0],
            "kind": [EDGE_KIND_TRANSIT, EDGE_KIND_TRANSIT],
        }
    )
    return Network(stops=stops, edges=edges)


@pytest.fixture()
def micro_bg() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"geoid": ["g1", "g2"]},
        geometry=[Point(_A[1], _A[0]), Point(_B[1], _B[0])],
        crs="EPSG:4326",
    )


def _opp(points, weights, category) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "name": [f"{category}{i}" for i in range(len(points))],
            "weight": list(weights),
            "category": [category] * len(points),
        },
        geometry=[Point(p[1], p[0]) for p in points],
        crs="EPSG:4326",
    )


@pytest.fixture()
def micro_jobs() -> gpd.GeoDataFrame:
    # Points at A, B, E with weights 10, 20, 40.
    return _opp([_A, _B, _E], [10.0, 20.0, 40.0], "jobs")


# Stops for the pruned-cutoff / direct-walk-competes cases. A->B is a 40-min
# transit leg (40 > cutoff 38), B is 3.0 km from A (direct walk 36 min), and F
# is an isolated stop 6 km away. No walking edges exist.
_PRUNE_B = (47.63698, -122.340)  # ~3.0 km north of A, transit 40 min from A
_PRUNE_F = (47.66396, -122.340)  # ~6.0 km north of A, isolated stop


@pytest.fixture()
def pruned_network() -> Network:
    stops = pd.DataFrame(
        {
            "stop_id": pd.array(["A", "B", "F"], dtype="string"),
            "stop_name": ["A", "B", "F"],
            "stop_lat": [_A[0], _PRUNE_B[0], _PRUNE_F[0]],
            "stop_lon": [_A[1], _PRUNE_B[1], _PRUNE_F[1]],
        }
    )
    edges = pd.DataFrame(
        {
            "from_stop": ["A"],
            "to_stop": ["B"],
            "weight_min": [40.0],
            "kind": [EDGE_KIND_TRANSIT],
        }
    )
    return Network(stops=stops, edges=edges)


# No-transit fallback within the 800 m catchment: origin at X has stop O within
# 800 m; destination at Y (723 m from X) has only stop S in its catchment; O
# and S are not connected, so travel_time falls back to the direct walk.
_FB_X = (47.610, -122.340)
_FB_O = (47.6040, -122.340)  # stop, 667 m south of X
_FB_Y = (47.6165, -122.340)  # destination, 723 m north of X
_FB_S = (47.6235, -122.340)  # stop, 778 m north of Y


@pytest.fixture()
def fallback_network() -> Network:
    stops = pd.DataFrame(
        {
            "stop_id": pd.array(["O", "S"], dtype="string"),
            "stop_name": ["O", "S"],
            "stop_lat": [_FB_O[0], _FB_S[0]],
            "stop_lon": [_FB_O[1], _FB_S[1]],
        }
    )
    edges = pd.DataFrame(
        columns=["from_stop", "to_stop", "weight_min", "kind"]
    )
    return Network(stops=stops, edges=edges)


def _reach_mask(net: Network, origin_xy) -> np.ndarray:
    """Boolean mask over stop positions reachable from origin (any path)."""
    g = net.graph()
    virt = "__reach_virtual__"
    g.add_node(virt)
    try:
        for row in get_closest_stops(net, origin_xy, net.max_walk_m).itertuples(
            index=False
        ):
            g.add_edge(virt, row.stop_id, weight=1.0)
        desc = nx.descendants(g, virt)
    finally:
        g.remove_node(virt)
    pos_of = {s: i for i, s in enumerate(net.stops["stop_id"].to_numpy())}
    mask = np.zeros(len(net.stops), dtype=bool)
    for s in desc:
        j = pos_of.get(s)
        if j is not None:
            mask[j] = True
    return mask


# ---------------------------------------------------------------------------
# Micro-fixture: threshold behavior, weighting, edge cases
# ---------------------------------------------------------------------------


def test_micro_travel_times_as_designed(micro_network: Network) -> None:
    """Sanity-check the fixture's expected door-to-door times."""
    assert travel_time(micro_network, _A, _A) == pytest.approx(0.0)
    assert travel_time(micro_network, _A, _B) == pytest.approx(32.0)  # 25 + 7
    assert travel_time(micro_network, _A, _C) == pytest.approx(57.0)  # 50 + 7
    assert travel_time(micro_network, _A, _E) is None
    assert travel_time(micro_network, _B, _C) == pytest.approx(32.0)
    assert travel_time(micro_network, _B, _A) is None  # directed chain: no B->A


def test_micro_schema_and_geoids(
    micro_network: Network, micro_bg, micro_jobs
) -> None:
    res = compute_access_scores(micro_bg, {"jobs": micro_jobs}, micro_network)
    assert list(res.columns) == ["geoid", "jobs_access", "healthcare_access",
                                 "schools_access", "food_access"]
    assert list(res["geoid"]) == ["g1", "g2"]
    # Missing categories -> NaN.
    assert res["healthcare_access"].isna().all()
    assert res["schools_access"].isna().all()
    assert res["food_access"].isna().all()


def test_micro_threshold_and_weighting(micro_network, micro_bg, micro_jobs):
    # jobs threshold 45: g1 reaches A (0 min) and B (32 min); E unreachable.
    # Weighted share = (10 + 20) / 70.
    res = compute_access_scores(micro_bg, {"jobs": micro_jobs}, micro_network)
    assert res["jobs_access"].iloc[0] == pytest.approx(30.0 / 70.0)
    # g2 (origin at B) reaches B only: A has no reverse transit path, E is
    # unreachable -> (20) / 70.
    assert res["jobs_access"].iloc[1] == pytest.approx(20.0 / 70.0)
    # Weighting is actually applied: unweighted count share would be 2/3.
    assert res["jobs_access"].iloc[0] != pytest.approx(2.0 / 3.0)


def test_micro_per_category_thresholds(micro_network, micro_bg, micro_jobs):
    # healthcare/schools threshold 30: B (32 min) becomes unreachable for g1,
    # so only A counts -> 10 / 70. food threshold 20: same as healthcare here.
    opps = {c: micro_jobs for c in CATEGORY_ORDER}
    res = compute_access_scores(micro_bg, opps, micro_network)
    for col in ("healthcare_access", "schools_access", "food_access"):
        assert res[col].iloc[0] == pytest.approx(10.0 / 70.0)
    assert res["jobs_access"].iloc[0] == pytest.approx(30.0 / 70.0)


def test_micro_zero_opportunity_nan(micro_network, micro_bg):
    empty = gpd.GeoDataFrame(
        {
            "name": pd.Series(dtype=str),
            "weight": pd.Series(dtype=float),
            "category": pd.Series(dtype=str),
        },
        geometry=[],
        crs="EPSG:4326",
    )
    opps = {"jobs": empty, "healthcare": empty, "schools": empty, "food": empty}
    res = compute_access_scores(micro_bg, opps, micro_network)
    for col in ("jobs_access", "healthcare_access", "schools_access", "food_access"):
        assert res[col].isna().all()


def test_micro_all_unreachable_zero(micro_network, micro_bg):
    # All opportunities at the isolated stop E -> every origin gets 0.0.
    unreachable = _opp([_E, _E, _E], [5.0, 5.0, 5.0], "jobs")
    res = compute_access_scores(micro_bg, {"jobs": unreachable}, micro_network)
    assert (res["jobs_access"] == 0.0).all()


def test_micro_pair_parity_with_travel_time(micro_network: Network) -> None:
    """Batch routing helper must match travel_time on every micro pair."""
    pairs = [
        (_A, _A), (_A, _B), (_A, _C), (_A, _E),
        (_B, _B), (_B, _C), (_B, _A), (_B, _E),
    ]
    for origin, dest in pairs:
        expected = travel_time(micro_network, origin, dest)
        got = _pair_minutes(micro_network, origin, dest)
        if expected is None:
            assert got is None, (origin, dest)
        else:
            assert got is not None, (origin, dest)
            assert got == pytest.approx(expected, rel=1e-9, abs=1e-6)


def test_micro_pruned_direct_walk_beats_pruned_transit(
    pruned_network: Network,
) -> None:
    """Direct walk (3.0 km, 36 min) beats pruned 40-min transit leg.

    travel_time returns min(40 + 7, 36) = 36, so the pair is reachable for
    jobs/45 but NOT healthcare/schools/30 even though the transit leg is beyond
    the internal 38-min cutoff. The scorer must reproduce this exactly.
    """
    net = pruned_network
    direct_walk_ab = (
        float(haversine_m(_A[0], _A[1], _PRUNE_B[0], _PRUNE_B[1]))
        / 1000.0
        / net.walk_speed_kmh
        * 60.0
    )
    assert travel_time(net, _A, _PRUNE_B) == pytest.approx(direct_walk_ab)

    bg = gpd.GeoDataFrame(
        {"geoid": ["g1"]},
        geometry=[Point(_A[1], _A[0])],
        crs="EPSG:4326",
    )
    opp = _opp([_PRUNE_B], [1.0], "jobs")
    res = compute_access_scores(bg, {c: opp for c in CATEGORY_ORDER}, net)
    assert res["jobs_access"].iloc[0] == pytest.approx(1.0)
    assert res["healthcare_access"].iloc[0] == pytest.approx(0.0)
    assert res["schools_access"].iloc[0] == pytest.approx(0.0)
    assert res["food_access"].iloc[0] == pytest.approx(0.0)

    # Lower-level pruned-path parity with travel_time.
    stop_pos_of = {s: i for i, s in enumerate(net.stops["stop_id"].to_numpy())}
    d_arr = _origin_distances(net, _A, cutoff=38.0, stop_pos_of=stop_pos_of)
    reach = _reach_mask(net, _A)
    got = _pair_minutes(
        net,
        _A,
        _PRUNE_B,
        d_arr=d_arr,
        stop_pos_of=stop_pos_of,
        pruned=True,
        get_reachable=lambda: reach,
    )
    assert got == pytest.approx(direct_walk_ab)
    # Without the pruning-aware fallback (pruned=False) the pruned all-inf
    # result would be mistaken for "no path" -> None (the old bug).
    assert (
        _pair_minutes(
            net, _A, _PRUNE_B, d_arr=d_arr, stop_pos_of=stop_pos_of
        )
        is None
    )


def test_micro_pruned_no_transit_beyond_catchment(
    pruned_network: Network,
) -> None:
    """Isolated stop beyond the catchment stays unreachable (no overcount)."""
    net = pruned_network
    assert travel_time(net, _A, _PRUNE_F) is None

    bg = gpd.GeoDataFrame(
        {"geoid": ["g1"]},
        geometry=[Point(_A[1], _A[0])],
        crs="EPSG:4326",
    )
    opp = _opp([_PRUNE_F], [1.0], "jobs")
    res = compute_access_scores(bg, {"jobs": opp}, net)
    assert res["jobs_access"].iloc[0] == 0.0

    stop_pos_of = {s: i for i, s in enumerate(net.stops["stop_id"].to_numpy())}
    d_arr = _origin_distances(net, _A, cutoff=38.0, stop_pos_of=stop_pos_of)
    reach = _reach_mask(net, _A)
    assert (
        _pair_minutes(
            net,
            _A,
            _PRUNE_F,
            d_arr=d_arr,
            stop_pos_of=stop_pos_of,
            pruned=True,
            get_reachable=lambda: reach,
        )
        is None
    )


def test_micro_no_transit_direct_within_catchment_fallback(
    fallback_network: Network,
) -> None:
    """No transit path but direct walk within 800 m -> reachable by fallback."""
    net = fallback_network
    direct_walk = (
        float(haversine_m(_FB_X[0], _FB_X[1], _FB_Y[0], _FB_Y[1]))
        / 1000.0
        / net.walk_speed_kmh
        * 60.0
    )  # ~8.67 min
    assert travel_time(net, _FB_X, _FB_Y) == pytest.approx(direct_walk)

    bg = gpd.GeoDataFrame(
        {"geoid": ["g1"]},
        geometry=[Point(_FB_X[1], _FB_X[0])],
        crs="EPSG:4326",
    )
    opp = _opp([_FB_Y], [1.0], "jobs")
    res = compute_access_scores(bg, {c: opp for c in CATEGORY_ORDER}, net)
    for col in ("jobs_access", "healthcare_access", "schools_access", "food_access"):
        assert res[col].iloc[0] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Real-data integration
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def real_network() -> Network:
    return build_network(GTFS_DIR)


def _load_real_inputs():
    bg = gpd.read_file(BG_PATH)
    opps = {c: gpd.read_file(OPP_DIR / f"{c}.geojson") for c in CATEGORY_ORDER}
    return bg, opps


def test_real_access_scores(real_network: Network) -> None:
    bg, opps = _load_real_inputs()
    n_bg = len(bg)

    t0 = time.time()
    res = compute_access_scores(bg, opps, real_network)
    elapsed = time.time() - t0

    # Shape / schema.
    assert len(res) == n_bg
    assert list(res.columns) == ["geoid", "jobs_access", "healthcare_access",
                                 "schools_access", "food_access"]
    pd.testing.assert_series_equal(
        res["geoid"], bg["geoid"].reset_index(drop=True), check_names=False
    )

    # Ranges: every non-NaN score in [0, 1].
    stats = {}
    for col in ("jobs_access", "healthcare_access", "schools_access", "food_access"):
        s = res[col]
        finite = s.dropna()
        assert ((finite >= 0.0) & (finite <= 1.0)).all(), col
        stats[col] = {
            "n": int(s.notna().sum()),
            "n_nan": int(s.isna().sum()),
            "mean": float(finite.mean()) if len(finite) else float("nan"),
            "min": float(finite.min()) if len(finite) else float("nan"),
            "max": float(finite.max()) if len(finite) else float("nan"),
        }

    # jobs_access must be meaningfully non-zero (transit-reachable jobs exist).
    assert res["jobs_access"].notna().any()
    assert res["jobs_access"].mean() > 0.0

    print(f"\n[real] compute_access_scores runtime: {elapsed:.1f}s " f"({n_bg} block groups)")
    for col, st in stats.items():
        print(
            f"[real] {col}: n={st['n']} n_nan={st['n_nan']} "
            f"mean={st['mean']:.4f} min={st['min']:.4f} max={st['max']:.4f}"
        )


def test_real_batch_parity_with_travel_time(real_network: Network) -> None:
    """Spot-check the batched router against travel_time on real data."""
    rng = np.random.default_rng(42)
    bg, opps = _load_real_inputs()
    lat = bg.geometry.centroid.y.to_numpy()
    lon = bg.geometry.centroid.x.to_numpy()

    jobs = opps["jobs"]
    jlat = jobs.geometry.centroid.y.to_numpy()
    jlon = jobs.geometry.centroid.x.to_numpy()

    idx_o = rng.choice(len(bg), size=4, replace=False)
    idx_d = rng.choice(len(jobs), size=4, replace=False)
    for io, id_ in zip(idx_o, idx_d):
        origin = (float(lat[io]), float(lon[io]))
        dest = (float(jlat[id_]), float(jlon[id_]))
        expected = travel_time(real_network, origin, dest)
        got = _pair_minutes(real_network, origin, dest)
        if expected is None:
            assert got is None, (origin, dest)
        else:
            assert got is not None, (origin, dest)
            assert got == pytest.approx(expected, rel=1e-9, abs=1e-6)
