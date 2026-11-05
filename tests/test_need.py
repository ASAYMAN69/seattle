"""Tests for Task 2.3 Need Index (datanova/need.py).

Real-data integration tests over the prepared ACS parquet plus small synthetic
micro-fixtures for pure logic (direction, missing data, income suppression).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from datanova.need import compute_need_index

ROOT = Path(__file__).resolve().parents[1]
ACS_PATH = ROOT / "data" / "prepared" / "census" / "acs_demographics.parquet"

NEED_COLS = ["geoid", "need_index"]
PCT_INDICATORS = ["poverty_pct", "zero_car_pct", "minority_pct", "elderly_pct"]


@pytest.fixture(scope="module")
def acs() -> pd.DataFrame:
    if not ACS_PATH.exists():
        pytest.skip("acs_demographics.parquet not prepared yet — run scripts/fetch_census.py")
    return pd.read_parquet(ACS_PATH)


# ---------------------------------------------------------------------------
# Real-data integration tests
# ---------------------------------------------------------------------------


def test_output_columns(acs) -> None:
    out = compute_need_index(acs)
    assert list(out.columns) == NEED_COLS
    assert pd.api.types.is_string_dtype(out["geoid"])


def test_real_data_same_geoids(acs) -> None:
    out = compute_need_index(acs)
    assert set(out["geoid"]) == set(acs["geoid"].astype(str))
    assert len(out) == len(acs)


def test_real_data_need_index_in_unit_interval_or_nan(acs) -> None:
    out = compute_need_index(acs)
    vals = out["need_index"].dropna()
    assert ((vals >= 0) & (vals <= 1)).all()


def test_real_data_no_missing_need_index(acs) -> None:
    out = compute_need_index(acs)
    n_na = int(out["need_index"].isna().sum())
    # The current prepared ACS has no missing indicator shares (only suppressed
    # incomes, which are skipped rather than propagated), so every block group
    # has >= 4 available components -> no NaNs in practice.
    assert n_na == 0, f"{n_na} block groups got a NaN need index"


def test_deterministic(acs) -> None:
    a = compute_need_index(acs)
    b = compute_need_index(acs)
    pd.testing.assert_frame_equal(a, b)


def test_order_independent(acs) -> None:
    out = compute_need_index(acs)
    shuffled = acs.sample(frac=1.0, random_state=0).reset_index(drop=True)
    out_shuffled = compute_need_index(shuffled)
    pd.testing.assert_frame_equal(out, out_shuffled)


# ---------------------------------------------------------------------------
# Synthetic micro-fixtures (pure logic)
# ---------------------------------------------------------------------------


def test_high_need_row_outranks_low_need_row() -> None:
    fixture = pd.DataFrame(
        {
            "geoid": ["high", "low"],
            "median_income": [40_000, 150_000],
            "poverty_pct": [0.50, 0.05],
            "zero_car_pct": [0.50, 0.05],
            "minority_pct": [0.50, 0.05],
            "elderly_pct": [0.50, 0.05],
        }
    )
    out = compute_need_index(fixture).set_index("geoid")
    assert out.loc["high", "need_index"] > out.loc["low", "need_index"]


def test_higher_poverty_increases_need() -> None:
    fixture = pd.DataFrame(
        {
            "geoid": ["a", "b"],
            "median_income": [100_000, 100_000],
            "poverty_pct": [0.40, 0.10],
            "zero_car_pct": [0.20, 0.20],
            "minority_pct": [0.20, 0.20],
            "elderly_pct": [0.20, 0.20],
        }
    )
    out = compute_need_index(fixture).set_index("geoid")
    assert out.loc["a", "need_index"] > out.loc["b", "need_index"]


def test_all_missing_row_gives_nan() -> None:
    fixture = pd.DataFrame(
        {
            "geoid": ["ok", "allnan"],
            "median_income": [90_000, np.nan],
            "poverty_pct": [0.20, np.nan],
            "zero_car_pct": [0.20, np.nan],
            "minority_pct": [0.20, np.nan],
            "elderly_pct": [0.20, np.nan],
        }
    )
    out = compute_need_index(fixture).set_index("geoid")
    assert pd.isna(out.loc["allnan", "need_index"])
    assert not pd.isna(out.loc["ok", "need_index"])


def test_suppressed_income_component_is_skipped() -> None:
    # Row 'suppressed' carries the ACS income suppression code; its need index
    # must equal the plain mean of its four percentage indicators (income is
    # not counted, and must not distort the income min-max scale).
    fixture = pd.DataFrame(
        {
            "geoid": ["a", "b", "suppressed"],
            "median_income": [50_000, 200_000, -666_666_666],
            "poverty_pct": [0.30, 0.30, 0.24],
            "zero_car_pct": [0.30, 0.30, 0.24],
            "minority_pct": [0.30, 0.30, 0.24],
            "elderly_pct": [0.30, 0.30, 0.24],
        }
    )
    out = compute_need_index(fixture).set_index("geoid")
    expected = pytest.approx(float(np.mean([0.24, 0.24, 0.24, 0.24])))
    assert out.loc["suppressed", "need_index"] == expected


def test_pct_clipping_is_defensive() -> None:
    fixture = pd.DataFrame(
        {
            "geoid": ["a", "b"],
            "median_income": [100_000, 100_000],
            "poverty_pct": [1.50, -0.20],
            "zero_car_pct": [0.10, 0.10],
            "minority_pct": [0.10, 0.10],
            "elderly_pct": [0.10, 0.10],
        }
    )
    out = compute_need_index(fixture).set_index("geoid")
    assert out.loc["a", "need_index"] <= 1.0
    assert out.loc["a", "need_index"] > out.loc["b", "need_index"]
