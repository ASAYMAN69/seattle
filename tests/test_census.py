"""Tests for Task 1.2 census assets (real data).

Covers:
  - block_groups.geojson: >1000 King County block groups, valid geometry,
    a handful inside the Seattle city boundary.
  - acs_demographics.parquet: required columns, plausible King County
    population total, and all derived percentages within [0, 1] or NaN.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PREPARED_DIR = ROOT / "data" / "prepared"
BG_PATH = PREPARED_DIR / "census" / "block_groups.geojson"
ACS_PATH = PREPARED_DIR / "census" / "acs_demographics.parquet"
SEATTLE_PATH = PREPARED_DIR / "seattle_boundary.geojson"

KING_COUNTY_POP_REF = 2_269_000  # ACS 5-yr 2022 King County population

REQUIRED_ACS_COLUMNS = [
    "geoid",
    "median_income",
    "poverty_pct",
    "zero_car_pct",
    "minority_pct",
    "elderly_pct",
    "pop_total",
]
PCT_COLUMNS = ["poverty_pct", "zero_car_pct", "minority_pct", "elderly_pct"]


@pytest.fixture(scope="module")
def block_groups() -> gpd.GeoDataFrame:
    if not BG_PATH.exists():
        pytest.skip("block_groups.geojson not prepared yet — run scripts/fetch_census.py")
    return gpd.read_file(BG_PATH)


@pytest.fixture(scope="module")
def acs() -> pd.DataFrame:
    if not ACS_PATH.exists():
        pytest.skip("acs_demographics.parquet not prepared yet — run scripts/fetch_census.py")
    return pd.read_parquet(ACS_PATH)


def test_block_group_count(block_groups) -> None:
    assert len(block_groups) > 1000


def test_block_groups_all_in_king_county(block_groups) -> None:
    assert (block_groups["COUNTYFP"] == "033").all()
    assert block_groups["geoid"].astype(str).str.startswith("53033").all()


def test_block_group_geometry_valid(block_groups) -> None:
    assert block_groups.crs is not None
    assert block_groups.geometry.is_valid.all()


def test_some_block_groups_within_seattle_boundary(block_groups) -> None:
    if not SEATTLE_PATH.exists():
        pytest.skip("seattle_boundary.geojson not present yet")
    seattle = gpd.read_file(SEATTLE_PATH)
    inter = gpd.overlay(block_groups, seattle, how="intersection", keep_geom_type=False)
    assert len(inter) >= 1


def test_acs_required_columns(acs) -> None:
    assert set(REQUIRED_ACS_COLUMNS).issubset(acs.columns)


def test_acs_geoid_joins_geometry(block_groups, acs) -> None:
    geom_geoids = set(block_groups["geoid"].astype(str))
    acs_geoids = set(acs["geoid"].astype(str))
    overlap = len(geom_geoids & acs_geoids) / max(len(geom_geoids), 1)
    assert overlap >= 0.9


def test_pop_total_plausible(acs) -> None:
    total = float(acs["pop_total"].sum())
    assert abs(total - KING_COUNTY_POP_REF) / KING_COUNTY_POP_REF < 0.15


def test_pct_columns_in_unit_interval_or_nan(acs) -> None:
    for col in PCT_COLUMNS:
        vals = acs[col].dropna()
        assert ((vals >= 0) & (vals <= 1)).all()
