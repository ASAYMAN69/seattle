"""Tests for Task 2.4: equity scores, grades, recommendations, run_analysis.

Run: `.venv/bin/python -m pytest tests/test_equity.py -q`

- Real-data integration runs the full ``scripts/run_analysis.py`` pipeline on
  the real prepared inputs (network + accessibility + need + equity +
  recommendations) and asserts the prepared outputs are written, readable, and
  internally consistent.
- Micro-fixture tests cover equity grade-band boundaries, NaN-safe overall
  access, and recommendation determinism on a tiny synthetic GTFS/network.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from datanova.accessibility import CATEGORY_ORDER  # noqa: E402
from datanova.equity import (  # noqa: E402
    ACCESS_WEIGHTS,
    GRADE_BANDS,
    compute_equity,
    grade_bands,
    grade_for_gap,
)
from datanova.network import (  # noqa: E402
    EDGE_KIND_TRANSIT,
    Network,
    build_network,
    get_closest_stops,
)
from datanova.recommend import recommend  # noqa: E402

GTFS_DIR = PROJECT_ROOT / "data" / "prepared" / "gtfs"
BG_PATH = PROJECT_ROOT / "data" / "prepared" / "census" / "block_groups.geojson"
ACS_PATH = PROJECT_ROOT / "data" / "prepared" / "census" / "acs_demographics.parquet"
EQUITY_DIR = PROJECT_ROOT / "data" / "prepared" / "equity"
RUN_ANALYSIS = PROJECT_ROOT / "scripts" / "run_analysis.py"

GRADES = ("A", "B", "C", "D", "F")


# ---------------------------------------------------------------------------
# Real-data integration (full pipeline)
# ---------------------------------------------------------------------------


def _load_real_bg() -> gpd.GeoDataFrame:
    return gpd.read_file(BG_PATH)


@pytest.fixture(scope="session")
def pipeline_outputs() -> dict:
    """Run the real end-to-end pipeline once via the actual script."""
    if not (GTFS_DIR / "stops.parquet").exists():
        pytest.skip("prepared GTFS missing — run scripts/fetch_gtfs.py + parse_gtfs.py")
    if not BG_PATH.exists():
        pytest.skip("prepared census missing — run scripts/fetch_census.py")
    if not (PROJECT_ROOT / "data" / "prepared" / "opportunities" / "jobs.geojson").exists():
        pytest.skip("prepared opportunities missing — run scripts/fetch_opportunities.py")

    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, str(RUN_ANALYSIS)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=900,
    )
    elapsed = time.time() - t0
    assert proc.returncode == 0, (
        f"run_analysis.py failed\nSTDOUT:\n{proc.stdout[-4000:]}\n"
        f"STDERR:\n{proc.stderr[-4000:]}"
    )
    return {
        "elapsed": elapsed,
        "stdout": proc.stdout,
        "summary": proc.stdout[-4000:],
    }


def test_pipeline_writes_outputs(pipeline_outputs) -> None:
    for name in (
        "equity_scores.geojson",
        "equity_scores.parquet",
        "report_cards.json",
        "recommendations.geojson",
        "sensitivity.parquet",
    ):
        p = EQUITY_DIR / name
        assert p.exists(), f"missing output {name}"
        assert p.stat().st_size > 0, f"empty output {name}"


def test_equity_scores_geojson(pipeline_outputs) -> None:
    bg = _load_real_bg()
    gdf = gpd.read_file(EQUITY_DIR / "equity_scores.geojson")
    assert len(gdf) == len(bg)
    assert gdf.crs is not None and gdf.crs.to_epsg() == 4326
    for col in (
        "geoid",
        "jobs_access",
        "healthcare_access",
        "schools_access",
        "food_access",
        "access_overall",
        "need_index",
        "gap",
        "grade",
        "jobs_grade",
        "healthcare_grade",
        "schools_grade",
        "food_grade",
    ):
        assert col in gdf.columns, f"missing column {col} in equity_scores"
    grades = set(gdf["grade"].dropna().astype(str))
    assert grades <= set(GRADES), grades
    vals = gdf["gap"].dropna()
    assert ((vals >= -1.0) & (vals <= 1.0)).all()
    acc = gdf["access_overall"].dropna()
    assert ((acc >= 0.0) & (acc <= 1.0)).all()


def test_report_cards_json(pipeline_outputs) -> None:
    with open(EQUITY_DIR / "report_cards.json", encoding="utf-8") as fh:
        report = json.load(fh)
    assert report["summary"]["n_block_groups"] > 0
    cards = report["report_cards"]
    assert len(cards) == report["summary"]["n_block_groups"]
    grades = {v["grade"] for v in cards.values() if v.get("grade") is not None}
    assert grades <= set(GRADES)
    # A card must carry overall + per-dimension grades.
    sample = next(iter(cards.values()))
    for key in (
        "grade",
        "jobs_grade",
        "healthcare_grade",
        "schools_grade",
        "food_grade",
    ):
        assert key in sample


def test_recommendations_geojson(pipeline_outputs) -> None:
    gdf = gpd.read_file(EQUITY_DIR / "recommendations.geojson")
    assert len(gdf) > 0, "recommendations must be non-empty"
    for _, row in gdf.iterrows():
        assert row["affected_pop"] > 0
        # pyogrio decodes the GeoJSON array as a numpy array, not a list.
        geoids = row["geoids"]
        assert geoids is not None and len(geoids) > 0
        assert all(isinstance(g, str) for g in geoids)
        assert "action" in row and "corridor" in row
        assert "route_id" in row
        assert row.geometry is not None


def test_sensitivity_parquet(pipeline_outputs) -> None:
    sens = pd.read_parquet(EQUITY_DIR / "sensitivity.parquet")
    assert len(sens) > 0
    for col in (
        "route_id",
        "corridor",
        "affected_pop",
        "n_block_groups",
        "geoids",
        "am_peak_trips",
        "headway_min_current",
        "wait_saving_min",
        "est_access_gain_mean",
        "est_access_gain_popweighted",
    ):
        assert col in sens.columns
    rec = gpd.read_file(EQUITY_DIR / "recommendations.geojson")
    assert len(sens) == len(rec)
    # Both sides convert missing coverage-gap route_id (None) to "None".
    assert set(sens["route_id"].astype(str)) == set(rec["route_id"].astype(str))


def test_affected_pop_reconciles_with_census(pipeline_outputs) -> None:
    """Sum of recommendation affected populations vs census pop (within 5%)."""
    acs = pd.read_parquet(ACS_PATH)
    pop_by_geoid = dict(zip(acs["geoid"].astype(str), acs["pop_total"].astype(float)))
    # 1) per-recommendation reported affected_pop == sum of its geoids' pop.
    rec = gpd.read_file(EQUITY_DIR / "recommendations.geojson")
    for _, row in rec.iterrows():
        expected = sum(pop_by_geoid.get(g, 0.0) for g in row["geoids"])
        assert row["affected_pop"] == pytest.approx(expected, rel=1e-6, abs=1.0)
    # 2) union of recommended geoids reconciles with census totals within 5%.
    union_geoids = set()
    for geoids in rec["geoids"]:
        union_geoids.update(geoids)
    census_pop = sum(pop_by_geoid.get(g, 0.0) for g in union_geoids)
    rec_pop = int(rec["affected_pop"].sum())
    assert census_pop > 0
    assert rec_pop == pytest.approx(census_pop, rel=0.05)


# ---------------------------------------------------------------------------
# Micro-fixture: equity bands, NaN-safe overall, schema
# ---------------------------------------------------------------------------


def _access_frame(rows) -> pd.DataFrame:
    """rows: list of dicts with geoid + category access values."""
    cols = ["geoid"] + [f"{c}_access" for c in CATEGORY_ORDER]
    return pd.DataFrame(rows, columns=cols)


def test_grade_bands_contract() -> None:
    bands = grade_bands()
    assert set(bands) == set(GRADES)
    assert bands["A"][0] == pytest.approx(0.25)
    assert bands["B"] == (0.10, 0.25)
    assert bands["C"] == (-0.05, 0.10)
    assert bands["D"] == (-0.20, -0.05)
    # F is unbounded below: lower bound is -inf, upper (exclusive) is -0.20.
    assert bands["F"] == (float("-inf"), -0.20)
    # Mirrors the module constant.
    assert bands == GRADE_BANDS


def test_grade_band_boundaries() -> None:
    assert grade_for_gap(0.25) == "A"
    assert grade_for_gap(0.25 - 1e-9) == "B"
    assert grade_for_gap(0.10) == "B"
    assert grade_for_gap(0.10 - 1e-9) == "C"
    assert grade_for_gap(-0.05) == "C"
    assert grade_for_gap(-0.05 - 1e-9) == "D"
    assert grade_for_gap(-0.20) == "D"
    assert grade_for_gap(-0.20 - 1e-9) == "F"
    assert grade_for_gap(1.0) == "A"
    assert grade_for_gap(-1.0) == "F"


def test_compute_equity_schema_and_gap() -> None:
    access = _access_frame(
        [
            {
                "geoid": "g1",
                "jobs_access": 0.8,
                "healthcare_access": 0.6,
                "schools_access": 0.4,
                "food_access": 0.5,
            }
        ]
    )
    need = pd.DataFrame({"geoid": ["g1"], "need_index": [0.7]})
    out = compute_equity(access, need)
    assert list(out.columns) == [
        "geoid",
        "jobs_access",
        "healthcare_access",
        "schools_access",
        "food_access",
        "access_overall",
        "need_index",
        "gap",
        "grade",
        "jobs_grade",
        "healthcare_grade",
        "schools_grade",
        "food_grade",
    ]
    expected_overall = (
        0.4 * 0.8 + 0.25 * 0.6 + 0.15 * 0.4 + 0.2 * 0.5
    )  # 0.63
    assert out["access_overall"].iloc[0] == pytest.approx(expected_overall)
    assert out["gap"].iloc[0] == pytest.approx(expected_overall - 0.7)
    # gap = 0.63 - 0.7 = -0.07 -> D (C starts at -0.05).
    assert out["grade"].iloc[0] == "D"
    assert out["jobs_grade"].iloc[0] == grade_for_gap(0.8 - 0.7)  # 0.10 -> B
    assert out["food_grade"].iloc[0] == grade_for_gap(0.5 - 0.7)  # -0.20 -> D


def test_nan_safe_overall_access() -> None:
    need = pd.DataFrame({"geoid": ["g1", "g2", "g3"], "need_index": [0.5, 0.5, 0.5]})
    access = _access_frame(
        [
            {
                "geoid": "g1",
                "jobs_access": 0.8,
                "healthcare_access": 0.6,
                "schools_access": 0.4,
                "food_access": 0.5,
            },
            {
                "geoid": "g2",
                "jobs_access": np.nan,  # dropped -> weights renormalized
                "healthcare_access": 0.6,
                "schools_access": 0.4,
                "food_access": 0.5,
            },
            {
                "geoid": "g3",
                "jobs_access": np.nan,
                "healthcare_access": np.nan,
                "schools_access": np.nan,
                "food_access": np.nan,
            },
        ]
    )
    out = compute_equity(access, need).set_index("geoid")
    # g1: weighted mean of all four.
    assert out.loc["g1", "access_overall"] == pytest.approx(
        0.4 * 0.8 + 0.25 * 0.6 + 0.15 * 0.4 + 0.2 * 0.5
    )
    # g2: only healthcare/schools/food, weights renormalized over 0.60.
    assert out.loc["g2", "access_overall"] == pytest.approx(
        (0.25 * 0.6 + 0.15 * 0.4 + 0.2 * 0.5) / 0.60
    )
    # g3: all NaN -> overall NaN -> gap NaN -> grade NaN.
    assert pd.isna(out.loc["g3", "access_overall"])
    assert pd.isna(out.loc["g3", "gap"])
    assert pd.isna(out.loc["g3", "grade"])
    # Per-dimension grade for a NaN category is also NaN.
    assert pd.isna(out.loc["g2", "jobs_grade"])


def test_compute_equity_missing_need_geoid_is_nan() -> None:
    access = _access_frame(
        [{"geoid": "g1", "jobs_access": 0.5, "healthcare_access": 0.5,
          "schools_access": 0.5, "food_access": 0.5}]
    )
    need = pd.DataFrame({"geoid": ["other"], "need_index": [0.5]})
    out = compute_equity(access, need)
    assert pd.isna(out.loc[0, "need_index"])
    assert pd.isna(out.loc[0, "gap"])
    assert pd.isna(out.loc[0, "grade"])


# ---------------------------------------------------------------------------
# Micro-fixture: recommendation determinism + attribution
# ---------------------------------------------------------------------------


@pytest.fixture()
def micro_gtfs(tmp_path) -> Path:
    """Minimal prepared-style GTFS dir: routes/stop_times/trips/calendar."""
    routes = pd.DataFrame(
        {
            "route_id": ["R1", "R2"],
            "route_short_name": ["1", "2"],
            "route_long_name": ["Route One", "Route Two"],
            "route_type": [3, 3],
            "agency_id": ["a", "a"],
        }
    )
    # Two R1 trips and one R2 trip, all departing in the AM peak window.
    stop_times = pd.DataFrame(
        {
            "trip_id": ["t1", "t1", "t2", "t2", "t3", "t3"],
            "stop_id": ["A", "B", "A", "B", "A", "B"],
            "stop_sequence": [1, 2, 1, 2, 1, 2],
            "arrival_time": ["07:00:00", "07:10:00", "07:30:00", "07:40:00",
                             "08:00:00", "08:10:00"],
            "departure_time": ["07:00:00", "07:10:00", "07:30:00", "07:40:00",
                               "08:00:00", "08:10:00"],
        }
    )
    trips = pd.DataFrame(
        {
            "trip_id": ["t1", "t2", "t3"],
            "route_id": ["R1", "R1", "R2"],
            "service_id": ["s1", "s1", "s1"],
        }
    )
    calendar = pd.DataFrame(
        {
            "service_id": ["s1"],
            "monday": [1], "tuesday": [1], "wednesday": [1],
            "thursday": [1], "friday": [1],
            "saturday": [0], "sunday": [0],
            "start_date": ["20260101"], "end_date": ["20261231"],
        }
    )
    routes.to_parquet(tmp_path / "routes.parquet", index=False)
    stop_times.to_parquet(tmp_path / "stop_times.parquet", index=False)
    trips.to_parquet(tmp_path / "trips.parquet", index=False)
    calendar.to_parquet(tmp_path / "calendar.parquet", index=False)
    return tmp_path


@pytest.fixture()
def micro_network() -> Network:
    stops = pd.DataFrame(
        {
            "stop_id": pd.array(["A", "B"], dtype="string"),
            "stop_name": ["A", "B"],
            "stop_lat": [47.6100, 47.6200],
            "stop_lon": [-122.3400, -122.3400],
        }
    )
    edges = pd.DataFrame(
        {
            "from_stop": ["A"],
            "to_stop": ["B"],
            "weight_min": [10.0],
            "kind": [EDGE_KIND_TRANSIT],
        }
    )
    net = Network(stops=stops, edges=edges)
    net.max_walk_m = 800.0
    return net


def _micro_equity() -> pd.DataFrame:
    """Two candidates near stop A (attributed to R1) + one coverage-gap BG."""
    return pd.DataFrame(
        {
            "geoid": ["g1", "g2", "g_far"],
            "jobs_access": [0.2, 0.3, 0.1],
            "healthcare_access": [0.2, 0.3, 0.1],
            "schools_access": [0.2, 0.3, 0.1],
            "food_access": [0.2, 0.3, 0.1],
            "access_overall": [0.2, 0.3, 0.1],
            "need_index": [0.8, 0.7, 0.9],
            "gap": [-0.6, -0.4, -0.8],
            "grade": ["F", "F", "F"],
            "pop_total": [1000, 2000, 500],
        }
    )


def _micro_bg() -> gpd.GeoDataFrame:
    # g1/g2 sit at stop A; g_far is > 800 m from every stop (coverage gap).
    return gpd.GeoDataFrame(
        {
            "geoid": ["g1", "g2", "g_far"],
        },
        geometry=[
            Point(-122.34, 47.61),
            Point(-122.34, 47.61),
            Point(-122.0, 48.0),
        ],
        crs="EPSG:4326",
    )


def test_recommend_micro_deterministic(micro_gtfs, micro_network) -> None:
    eq = _micro_equity()
    bg = _micro_bg()
    a = recommend(eq, bg, micro_network, micro_gtfs)
    b = recommend(eq, bg, micro_network, micro_gtfs)
    assert a == b
    assert len(a) >= 1


def test_recommend_micro_attribution_and_shape(micro_gtfs, micro_network) -> None:
    recs = recommend(_micro_equity(), _micro_bg(), micro_network, micro_gtfs)
    assert len(recs) >= 2  # R1 corridor + coverage gap

    by_route = {r["route_id"]: r for r in recs}
    r1 = by_route["R1"]
    assert r1["corridor"] == "Route 1"
    assert set(r1["geoids"]) == {"g1", "g2"}
    assert r1["affected_pop"] == 3000
    assert r1["am_peak_trips"] == 2
    assert r1["headway_min_current"] == pytest.approx(90.0)  # 180 / 2
    assert r1["wait_saving_min"] == pytest.approx(min(90.0 / 4, 3.5))
    assert "Increase weekday AM-peak frequency" in r1["action"]

    cov = by_route[None]
    assert "Add transit" in cov["action"]
    assert cov["geoids"] == ["g_far"]
    assert cov["affected_pop"] == 500


def test_recommend_requires_pop_total(micro_gtfs, micro_network) -> None:
    eq = _micro_equity().drop(columns=["pop_total"])
    with pytest.raises(ValueError, match="pop_total"):
        recommend(eq, _micro_bg(), micro_network, micro_gtfs)


def test_default_acs_path_resolves_to_conventional_location() -> None:
    """Regression: the ACS fallback must not duplicate the 'data' segment."""
    from datanova.recommend import _default_acs_path

    expected = (
        PROJECT_ROOT / "data" / "prepared" / "census" / "acs_demographics.parquet"
    )
    assert _default_acs_path(GTFS_DIR) == expected
    assert _default_acs_path(GTFS_DIR).exists()


def test_recommend_fallback_attaches_pop_total(
    micro_gtfs, micro_network, tmp_path
) -> None:
    """Equity without pop_total must load ACS via acs_path and succeed."""
    eq = _micro_equity().drop(columns=["pop_total"])
    acs = pd.DataFrame(
        {"geoid": ["g1", "g2", "g_far"], "pop_total": [1000, 2000, 500]}
    )
    acs_path = tmp_path / "acs_demographics.parquet"
    acs.to_parquet(acs_path, index=False)

    recs = recommend(eq, _micro_bg(), micro_network, micro_gtfs, acs_path=acs_path)
    by_route = {r["route_id"]: r for r in recs}
    assert by_route["R1"]["affected_pop"] == 3000
    assert by_route[None]["affected_pop"] == 500


def test_recommend_real_fallback_attaches_pop_total(pipeline_outputs) -> None:
    """Real equity without pop_total must resolve the conventional ACS path.

    Regression for the duplicated-``data``-segment bug: before the fix this
    raised ValueError because the fallback looked under <root>/data/data/...
    """
    gdf = gpd.read_file(EQUITY_DIR / "equity_scores.geojson")
    assert "pop_total" in gdf.columns
    eq = gdf.drop(columns=["pop_total"])

    net = build_network(GTFS_DIR)
    recs = recommend(eq, gdf, net, GTFS_DIR)  # default ACS path resolution
    assert len(recs) > 0

    acs = pd.read_parquet(ACS_PATH)
    pop_by = dict(zip(acs["geoid"].astype(str), acs["pop_total"].astype(float)))
    r0 = recs[0]
    expected = sum(pop_by.get(g, 0.0) for g in r0["geoids"])
    assert r0["affected_pop"] == pytest.approx(expected, rel=1e-6, abs=1.0)


def test_micro_nearest_stop_used(micro_gtfs, micro_network) -> None:
    """g near stop B (R1/R2 both serve B) picks the higher-frequency route."""
    stops = micro_network.stops.copy()
    edges = micro_network.edges.copy()
    net = Network(stops=stops, edges=edges)
    bg = gpd.GeoDataFrame(
        {"geoid": ["gB"]},
        geometry=[Point(-122.34, 47.62)],
        crs="EPSG:4326",
    )
    eq = _micro_equity().iloc[[0]].copy()
    eq["geoid"] = ["gB"]
    eq["pop_total"] = [900]
    recs = recommend(eq, bg, net, micro_gtfs)
    assert recs[0]["route_id"] == "R1"
    assert recs[0]["affected_pop"] == 900
