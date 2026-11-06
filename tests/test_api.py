"""Tests for the FastAPI service (Task 001).

These run against the real prepared data via FastAPI's TestClient. Assertions
target shapes and ordering (feature counts, required keys, monotonic ranking),
not fabricated values — mirroring the project's existing real-data test style.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.data import PREPARED, WEB_DIST
from api.main import app

client = TestClient(app)

REQUIRED_EQUITY_PROPS = {
    "geoid",
    "grade",
    "need_index",
    "gap",
    "access_overall",
    "jobs_access",
    "healthcare_access",
    "schools_access",
    "food_access",
    "pop_total",
    "poverty_pct",
    "zero_car_pct",
    "median_income",
}

# Sanity envelope for Seattle-area EPSG:4326 coordinates (catches swapped
# axes or non-degree units like UTM meters, without being tautological).
SEATTLE_BBOX = {"min_lon": -123.0, "max_lon": -120.0, "min_lat": 47.0, "max_lat": 48.0}

FIRST_GEOID = str(PREPARED["equity_scores"].iloc[0]["geoid"])


def _assert_feature_collection(payload: dict[str, Any]) -> None:
    assert payload["type"] == "FeatureCollection"
    assert isinstance(payload["features"], list)
    assert payload["features"]
    for feature in payload["features"]:
        assert feature["type"] == "Feature"
        assert isinstance(feature["properties"], dict)


def _assert_no_nonfinite_floats(value: Any) -> None:
    """Recursively ensure no NaN/Inf leaks into a decoded JSON payload."""
    if isinstance(value, float):
        assert math.isfinite(value), f"non-finite float in payload: {value!r}"
    elif isinstance(value, dict):
        for v in value.values():
            _assert_no_nonfinite_floats(v)
    elif isinstance(value, list):
        for v in value:
            _assert_no_nonfinite_floats(v)


# ---------------------------------------------------------------------------
# Health / basic
# ---------------------------------------------------------------------------


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_unknown_api_path_returns_404_json() -> None:
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.json()["detail"]


# ---------------------------------------------------------------------------
# GeoJSON endpoints
# ---------------------------------------------------------------------------


def test_boundary_feature_collection() -> None:
    resp = client.get("/api/boundary")
    assert resp.status_code == 200
    payload = resp.json()
    _assert_feature_collection(payload)
    assert len(payload["features"]) == len(PREPARED["boundary"])
    assert payload["features"][0]["properties"]["NAME"] == "Seattle"


def test_equity_feature_collection_shape() -> None:
    resp = client.get("/api/equity")
    assert resp.status_code == 200
    payload = resp.json()
    _assert_feature_collection(payload)
    assert len(payload["features"]) == len(PREPARED["equity_scores"])
    for feature in payload["features"]:
        assert REQUIRED_EQUITY_PROPS <= set(feature["properties"])
        assert feature["geometry"] is not None
    _assert_no_nonfinite_floats(payload)


def test_equity_coordinates_are_lonlat_4326() -> None:
    resp = client.get("/api/equity")
    payload = resp.json()
    for feature in payload["features"][:50]:
        # Polygon rings: (lon, lat) pairs.
        lon, lat = feature["geometry"]["coordinates"][0][0]
        assert SEATTLE_BBOX["min_lon"] <= lon <= SEATTLE_BBOX["max_lon"]
        assert SEATTLE_BBOX["min_lat"] <= lat <= SEATTLE_BBOX["max_lat"]


def test_recommendations_feature_collection() -> None:
    resp = client.get("/api/recommendations")
    assert resp.status_code == 200
    payload = resp.json()
    _assert_feature_collection(payload)
    assert len(payload["features"]) == len(PREPARED["recommendations"])
    for feature in payload["features"]:
        props = feature["properties"]
        assert {"route_id", "corridor", "action", "affected_pop"} <= set(props)
        assert feature["geometry"] is not None
    _assert_no_nonfinite_floats(payload)


# ---------------------------------------------------------------------------
# Tabular endpoints
# ---------------------------------------------------------------------------


def test_sensitivity_records() -> None:
    resp = client.get("/api/sensitivity")
    assert resp.status_code == 200
    records = resp.json()
    assert isinstance(records, list)
    assert len(records) == len(PREPARED["sensitivity"])
    required = {
        "route_id",
        "corridor",
        "action",
        "affected_pop",
        "est_access_gain_mean",
        "est_access_gain_popweighted",
    }
    for record in records:
        assert required <= set(record)
        assert "geometry" not in record
    _assert_no_nonfinite_floats(records)


def test_report_cards_root_object() -> None:
    resp = client.get("/api/report-cards")
    assert resp.status_code == 200
    payload = resp.json()
    assert {"generated_at", "summary", "report_cards"} <= set(payload)
    assert isinstance(payload["report_cards"], dict)


# ---------------------------------------------------------------------------
# Top-N underserved
# ---------------------------------------------------------------------------


def test_top_underserved_default_shape_and_ordering() -> None:
    resp = client.get("/api/top-underserved")
    assert resp.status_code == 200
    top = resp.json()
    assert len(top) == 25
    assert "geometry" not in top[0]
    # Monotonic need_index (descending).
    need = [r["need_index"] for r in top]
    assert all(need[i] >= need[i + 1] for i in range(len(need) - 1))
    # Within a need tie: gap ascending.
    for i in range(len(top) - 1):
        if need[i] == need[i + 1]:
            assert top[i]["gap"] <= top[i + 1]["gap"]
    # Within a need/gap tie: grade F-first (rank descending).
    rank = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
    for i in range(len(top) - 1):
        if need[i] == need[i + 1] and top[i]["gap"] == top[i + 1]["gap"]:
            assert rank[top[i]["grade"]] >= rank[top[i + 1]["grade"]]
    _assert_no_nonfinite_floats(top)


def test_top_underserved_n_param() -> None:
    assert len(client.get("/api/top-underserved?n=5").json()) == 5
    assert len(client.get("/api/top-underserved?n=1").json()) == 1
    assert client.get("/api/top-underserved?n=0").status_code == 422
    assert client.get("/api/top-underserved?n=-3").status_code == 422


def test_top_underserved_first_row_is_max_need() -> None:
    top = client.get("/api/top-underserved").json()
    max_need = PREPARED["equity_scores"]["need_index"].max()
    assert top[0]["need_index"] == max_need


# ---------------------------------------------------------------------------
# Block group detail
# ---------------------------------------------------------------------------


def test_block_group_known_geoid() -> None:
    resp = client.get(f"/api/block-group/{FIRST_GEOID}")
    assert resp.status_code == 200
    feature = resp.json()
    assert feature["type"] == "Feature"
    assert feature["geometry"] is not None
    props = feature["properties"]
    assert REQUIRED_EQUITY_PROPS <= set(props)
    assert str(props["geoid"]) == FIRST_GEOID
    source = PREPARED["equity_scores"].loc[
        PREPARED["equity_scores"]["geoid"].astype(str) == FIRST_GEOID
    ].iloc[0]
    assert props["need_index"] == source["need_index"]
    assert props["grade"] == source["grade"]
    _assert_no_nonfinite_floats(feature)


def test_block_group_suppressed_income_is_null() -> None:
    equity = PREPARED["equity_scores"]
    suppressed = equity.loc[equity["median_income"] == -666666666]
    if suppressed.empty:
        pytest.skip("no suppressed-income row in prepared data")
    geoid = str(suppressed.iloc[0]["geoid"])
    resp = client.get(f"/api/block-group/{geoid}")
    assert resp.status_code == 200
    assert resp.json()["properties"]["median_income"] is None


def test_block_group_unknown_geoid_404() -> None:
    resp = client.get("/api/block-group/535353535353")
    assert resp.status_code == 404
    assert resp.json()["detail"]


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_metadata_shape() -> None:
    resp = client.get("/api/metadata")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["app"] == "Seattle Transit Equity Index"
    assert payload["generated_at"] == PREPARED["report_cards"]["generated_at"]
    assert "n_block_groups" in payload["data_counts"]
    assert payload["data_counts"]["n_block_groups"] == len(PREPARED["equity_scores"])
    assert "methodology_note" in payload


# ---------------------------------------------------------------------------
# Static serving / CORS
# ---------------------------------------------------------------------------


def test_cors_preflight_allows_vite_origin() -> None:
    resp = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert (
        resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    )


def test_static_fallback_when_no_build() -> None:
    if WEB_DIST.is_dir():
        pytest.skip("web/dist present; fallback path not exercised")
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "API is live" in resp.text

    # Any non-API path returns the same fallback page (not a 404).
    resp = client.get("/some/spa/route")
    assert resp.status_code == 200
    assert "API is live" in resp.text


def test_static_serves_spa_when_build_present() -> None:
    if not WEB_DIST.is_dir():
        pytest.skip("web/dist absent; SPA serving not exercised")
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_static_spa_serving_with_temp_dist(tmp_path, monkeypatch) -> None:
    """Deterministically exercise the web/dist-serving branch (build a temp dist).

    Guarded against Picasso's parallel progress: works whether or not the real
    ``web/dist`` exists yet, and never touches ``web/``.
    """
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        "<!doctype html><html><body>SPA INDEX</body></html>", encoding="utf-8"
    )
    (dist / "assets" / "app.js").write_text(
        "console.log('app')", encoding="utf-8"
    )

    import api.data as data_mod
    import api.main as main_mod

    monkeypatch.setattr(data_mod, "WEB_DIST", dist)
    monkeypatch.setattr(main_mod, "WEB_DIST", dist)
    from api.main import create_app

    spa_client = TestClient(create_app())

    # Directory index.
    resp = spa_client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "SPA INDEX" in resp.text

    # Client-side route falls back to index.html (SPA routing).
    resp = spa_client.get("/some/spa/route")
    assert resp.status_code == 200
    assert "SPA INDEX" in resp.text

    # Real static asset is served as-is.
    resp = spa_client.get("/assets/app.js")
    assert resp.status_code == 200
    assert "console.log('app')" in resp.text

    # API still reachable underneath the "/" mount.
    resp = spa_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
