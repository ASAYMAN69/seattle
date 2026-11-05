"""Tests for the map view skeleton."""

from pathlib import Path

import pytest

from app.views.map_view import BOUNDARY_PATH, load_boundary

PREPARED_DIR = Path(__file__).resolve().parents[1] / "data" / "prepared"


def test_boundary_path_points_at_prepared_dir() -> None:
    assert BOUNDARY_PATH.parent == PREPARED_DIR


def test_boundary_exists_and_is_valid_geojson() -> None:
    if not BOUNDARY_PATH.exists():
        pytest.skip("boundary not prepared yet — run scripts/fetch_geometry.py")
    gdf = load_boundary()
    assert not gdf.empty
    assert gdf.crs is not None
    assert gdf.geometry.is_valid.all()


def test_load_boundary_raises_when_missing(tmp_path, monkeypatch) -> None:
    missing = tmp_path / "missing.geojson"
    monkeypatch.setattr("app.views.map_view.BOUNDARY_PATH", missing)
    with pytest.raises(FileNotFoundError):
        load_boundary()
