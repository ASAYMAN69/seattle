"""Tests for Task 1.3 opportunity POI outputs (real data).

Validates the four GeoJSON files under ``data/prepared/opportunities/``:
jobs, healthcare, schools, food.

Notes on spatial bounds:
- ``jobs.geojson`` covers all of King County (per the task brief: LODES WAC
  filtered to FIPS 53033), so it is checked against a King County envelope.
- ``healthcare/schools/food.geojson`` are OSM POIs inside the Seattle boundary
  bbox expanded by ~0.03°, so those are checked against that expanded bbox.
"""

from pathlib import Path

import geopandas as gpd
import pytest

ROOT = Path(__file__).resolve().parents[1]
OPP = ROOT / "data" / "prepared" / "opportunities"

FILES = ["jobs.geojson", "healthcare.geojson", "schools.geojson", "food.geojson"]

# Expanded Seattle boundary bbox: (minx, miny, maxx, maxy) = city bounds ±0.03°.
# Computed from the boundary file exactly as the fetch script does, with a
# small tolerance for floating-point edge effects.
_PAD = 0.03
_TOL = 1e-4
_boundary = gpd.read_file(ROOT / "data" / "prepared" / "seattle_boundary.geojson")
_minx, _miny, _maxx, _maxy = _boundary.total_bounds
SEATTLE_BBOX = (
    _minx - _PAD - _TOL,
    _miny - _PAD - _TOL,
    _maxx + _PAD + _TOL,
    _maxy + _PAD + _TOL,
)

# King County envelope (jobs are county-wide per the task brief)
KING_COUNTY_BBOX = (-122.7, 47.05, -120.9, 47.85)


def load(name: str) -> gpd.GeoDataFrame:
    path = OPP / name
    assert path.exists(), f"missing expected output {path}"
    gdf = gpd.read_file(path)
    assert len(gdf) > 0, f"{name} is empty"
    return gdf


def all_within_bbox(gdf: gpd.GeoDataFrame, bbox: tuple) -> bool:
    minx, miny, maxx, maxy = bbox
    return bool(
        (
            (gdf.geometry.x >= minx)
            & (gdf.geometry.x <= maxx)
            & (gdf.geometry.y >= miny)
            & (gdf.geometry.y <= maxy)
        ).all()
    )


def test_files_exist_and_nonempty():
    for name in FILES:
        gdf = load(name)
        assert gdf.crs is not None and gdf.crs.to_epsg() == 4326
        assert "geometry" in gdf.columns
        assert "name" in gdf.columns
        assert "category" in gdf.columns


def test_categories_correct():
    expected = {
        "jobs.geojson": {"jobs"},
        "healthcare.geojson": {"healthcare"},
        "schools.geojson": {"schools"},
        "food.geojson": {"food"},
    }
    for name, cats in expected.items():
        assert set(load(name)["category"]) == cats


def test_jobs_within_king_county():
    gdf = load("jobs.geojson")
    assert all_within_bbox(gdf, KING_COUNTY_BBOX)


@pytest.mark.parametrize(
    "name", ["healthcare.geojson", "schools.geojson", "food.geojson"]
)
def test_osm_within_seattle_bbox(name):
    gdf = load(name)
    assert all_within_bbox(gdf, SEATTLE_BBOX)


def test_jobs_weight_sane():
    gdf = load("jobs.geojson")
    total = float(gdf["weight"].sum())
    assert total > 0, "jobs weight sum must be > 0"
    # Census LEHD/LODES 2022 reports ~1.46M King County jobs; cap at a
    # plausible ceiling (well above the observed value, far below nonsense).
    assert total <= 2_000_000, f"jobs weight sum {total:,.0f} implausibly high"
    assert (gdf["weight"] >= 0).all()


@pytest.mark.parametrize(
    "name,min_features",
    [
        ("healthcare.geojson", 10),
        ("schools.geojson", 10),
        ("food.geojson", 10),
    ],
)
def test_osm_feature_counts(name, min_features):
    gdf = load(name)
    assert len(gdf) >= min_features, f"{name} has only {len(gdf)} features"
