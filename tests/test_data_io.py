"""Tests for ``app.data_io.load_prepared`` (Task 3.1)."""

from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from app.data_io import (
    BLOCK_GROUPS_PATH,
    BOUNDARY_PATH,
    EQUITY_SCORES_PATH,
    PreparedDataError,
    RECOMMENDATIONS_PATH,
    REPORT_CARDS_PATH,
    SENSITIVITY_PATH,
    load_prepared,
)

PREPARED_DIR = Path(__file__).resolve().parents[1] / "data" / "prepared"

# Every prepared input path, keyed by its module-level attribute name so the
# missing-file test can monkeypatch each one independently.
ALL_PATHS = {
    "BOUNDARY_PATH": BOUNDARY_PATH,
    "BLOCK_GROUPS_PATH": BLOCK_GROUPS_PATH,
    "EQUITY_SCORES_PATH": EQUITY_SCORES_PATH,
    "REPORT_CARDS_PATH": REPORT_CARDS_PATH,
    "RECOMMENDATIONS_PATH": RECOMMENDATIONS_PATH,
    "SENSITIVITY_PATH": SENSITIVITY_PATH,
}

EXPECTED_KEYS = {
    "boundary",
    "block_groups",
    "equity_scores",
    "report_cards",
    "recommendations",
    "sensitivity",
}

REQUIRED_EQUITY_COLS = {
    "geoid",
    "jobs_access",
    "healthcare_access",
    "schools_access",
    "food_access",
    "access_overall",
    "need_index",
    "gap",
    "grade",
}

REQUIRED_RECOMMENDATIONS_COLS = {"route_id", "corridor", "action"}


def test_load_prepared_returns_all_real_inputs() -> None:
    """load_prepared() works on the real prepared files."""
    data = load_prepared()
    assert set(data) == EXPECTED_KEYS

    assert not data["boundary"].empty
    assert not data["block_groups"].empty
    assert "geoid" in data["block_groups"].columns

    equity = data["equity_scores"]
    assert len(equity) == 1545
    assert REQUIRED_EQUITY_COLS <= set(equity.columns)
    assert equity.crs is not None

    assert isinstance(data["report_cards"], dict)
    assert "report_cards" in data["report_cards"]
    assert "summary" in data["report_cards"]

    assert not data["recommendations"].empty
    assert REQUIRED_RECOMMENDATIONS_COLS <= set(data["recommendations"].columns)

    assert not data["sensitivity"].empty
    assert "est_access_gain_mean" in data["sensitivity"].columns
    assert "est_access_gain_popweighted" in data["sensitivity"].columns


@pytest.mark.parametrize("attr", sorted(ALL_PATHS))
def test_load_prepared_raises_when_file_missing(tmp_path, monkeypatch, attr: str) -> None:
    """A missing prepared file raises PreparedDataError with a clear message."""
    missing = tmp_path / "missing-file"
    monkeypatch.setattr(f"app.data_io.{attr}", missing)
    with pytest.raises(PreparedDataError, match="missing"):
        load_prepared()


def test_load_prepared_raises_on_missing_equity_column(tmp_path, monkeypatch) -> None:
    """A file with wrong/missing columns raises PreparedDataError naming them."""
    bad = gpd.GeoDataFrame(
        {"geoid": ["1"], "geometry": [Point(0, 0)]}, crs="EPSG:4326"
    )
    path = tmp_path / "equity_bad.geojson"
    bad.to_file(path, driver="GeoJSON")
    monkeypatch.setattr("app.data_io.EQUITY_SCORES_PATH", path)
    with pytest.raises(PreparedDataError, match="jobs_access"):
        load_prepared()


def test_report_cards_missing_key_raises(tmp_path, monkeypatch) -> None:
    """A report_cards.json missing required top-level keys raises."""
    import json as _json

    path = tmp_path / "report_cards.json"
    path.write_text(_json.dumps({"generated_at": "now"}), encoding="utf-8")
    monkeypatch.setattr("app.data_io.REPORT_CARDS_PATH", path)
    with pytest.raises(PreparedDataError, match="summary|report_cards"):
        load_prepared()
