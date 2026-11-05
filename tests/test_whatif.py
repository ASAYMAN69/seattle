"""Tests for the What-if frequency explorer (Task 3.3).

These run against the real prepared data (``app.data_io.load_prepared``), so
they verify that route-id lookups, the interpolation/extrapolation projection,
and graceful missing-row handling behave correctly on the actual sensitivity
table (.``app.views.whatif``).
"""

from __future__ import annotations

from typing import Any

import math
import numpy as np
import pytest

from app.data_io import load_prepared
from app.views import whatif as wi

_DATA: dict[str, Any] | None = None


def get_data() -> dict[str, Any]:
    """Load real prepared data once per test session (it is heavy)."""
    global _DATA
    if _DATA is None:
        _DATA = load_prepared()
    return _DATA


def _route_row(data: dict[str, Any], route_id: Any) -> Any:
    df = data["sensitivity"]
    target = wi.route_key(route_id)
    keys = [wi.route_key(v) for v in df["route_id"]]
    return df.iloc[keys.index(target)]


# ---------------------------------------------------------------------------
# Lookups keyed by route_id
# ---------------------------------------------------------------------------
def test_lookup_sensitivity_by_route_id() -> None:
    data = get_data()
    row = wi.lookup_sensitivity_row("100512", data)
    assert row is not None
    assert row["corridor"] == "Route A Line"
    assert int(row["affected_pop"]) == 8871
    assert row["est_access_gain_mean"] > 0

    row183 = wi.lookup_sensitivity_row("100074", data)
    assert row183 is not None
    assert row183["corridor"] == "Route 183"


def test_lookup_sensitivity_coverage_row_by_none() -> None:
    data = get_data()
    row = wi.lookup_sensitivity_row(None, data)
    assert row is not None
    assert "Unserved area" in row["corridor"]
    assert int(row["affected_pop"]) == 1500
    assert float(row["est_access_gain_mean"]) == 0.0

    # Lookup by NaN/np.nan must hit the same coverage row.
    row_nan = wi.lookup_sensitivity_row(np.nan, data)
    assert row_nan is not None
    assert row_nan["corridor"] == row["corridor"]


def test_lookup_unknown_route_returns_none() -> None:
    data = get_data()
    assert wi.lookup_sensitivity_row("999999", data) is None
    assert wi.what_if_projection("999999", 2.0, data) is None


def test_route_key_blank_normalizes_to_coverage() -> None:
    # A blank/NaN route id is the coverage-gap sentinel (mapped to None), so a
    # blank lookup hits the coverage row by design — documented behavior.
    data = get_data()
    assert wi.route_key("") is None
    assert wi.route_key(np.nan) is None
    row = wi.lookup_sensitivity_row("", data)
    assert row is not None
    assert "Unserved area" in row["corridor"]


# ---------------------------------------------------------------------------
# Reference multiplier (2.0×) reproduces the precomputed sensitivity table
# ---------------------------------------------------------------------------
def test_projection_at_reference_multiplier_matches_table() -> None:
    data = get_data()
    for _, row in data["sensitivity"].iterrows():
        rid = wi.route_key(row["route_id"])
        if rid is None:  # coverage row handled separately
            continue
        proj = wi.what_if_projection(rid, 2.0, data)
        assert proj is not None
        assert proj["gain_mean"] == pytest.approx(float(row["est_access_gain_mean"]), rel=1e-4)
        assert proj["gain_popweighted"] == pytest.approx(
            float(row["est_access_gain_popweighted"]), rel=1e-4
        )
        assert proj["wait_saving_min"] == pytest.approx(
            float(row["wait_saving_min"]), abs=1e-4
        )
        # At the reference scenario the whole catchment is benefiting.
        assert abs(proj["benefited_pop"] - int(row["affected_pop"])) <= 1
        assert proj["affected_pop"] == int(row["affected_pop"])


# ---------------------------------------------------------------------------
# Slider bounds produce sensible outputs
# ---------------------------------------------------------------------------
def test_projection_at_multiplier_one_is_zero() -> None:
    data = get_data()
    proj = wi.what_if_projection("100512", 1.0, data)
    assert proj is not None
    assert proj["wait_saving_min"] == 0.0
    assert proj["gain_mean"] == 0.0
    assert proj["gain_popweighted"] == 0.0
    assert proj["benefited_pop"] == 0


def test_projection_monotonic_in_multiplier() -> None:
    data = get_data()
    mults = [1.0, 1.5, 2.0, 2.5, 3.0]
    wait = [wi.what_if_projection("100512", m, data)["wait_saving_min"] for m in mults]
    gains = [wi.what_if_projection("100512", m, data)["gain_mean"] for m in mults]
    assert wait == sorted(wait)
    assert gains == sorted(gains)
    # Route A Line has a small headway, so the wait saving is below the 3.5-min
    # cap and the gain grows strictly with the multiplier.
    assert wait[-1] > wait[0]
    assert gains[-1] > gains[0]
    # Extrapolation beyond the 2.0× reference stays finite and non-decreasing.
    assert wi.what_if_projection("100512", 3.0, data)["gain_mean"] > (
        wi.what_if_projection("100512", 2.0, data)["gain_mean"]
    )


def test_projection_clamps_out_of_range_multipliers() -> None:
    data = get_data()
    # Below the slider minimum is treated as 1.0× → no change, no gain.
    low = wi.what_if_projection("100512", 0.5, data)
    floor = wi.what_if_projection("100512", 1.0, data)
    assert low == floor
    assert low["gain_mean"] == 0.0
    # Above the slider maximum is treated as 3.0×.
    high = wi.what_if_projection("100512", 5.0, data)
    cap = wi.what_if_projection("100512", 3.0, data)
    assert high == cap
    assert math.isfinite(high["gain_mean"])
    assert high["gain_mean"] >= wi.what_if_projection("100512", 2.0, data)["gain_mean"]


def test_projection_all_real_corridors_finite() -> None:
    data = get_data()
    for _, row in data["sensitivity"].iterrows():
        rid = wi.route_key(row["route_id"])
        for m in (1.0, 1.5, 2.0, 2.5, 3.0):
            proj = wi.what_if_projection(rid, m, data)
            assert proj is not None
            assert math.isfinite(proj["gain_mean"])
            assert math.isfinite(proj["gain_popweighted"])
            assert math.isfinite(proj["wait_saving_min"])
            assert proj["gain_mean"] >= 0.0
            assert proj["affected_pop"] >= 0


# ---------------------------------------------------------------------------
# Missing sensitivity row handled gracefully (coverage-gap row)
# ---------------------------------------------------------------------------
def test_projection_coverage_row_has_no_gain() -> None:
    data = get_data()
    for m in (1.0, 2.0, 3.0):
        proj = wi.what_if_projection(None, m, data)
        assert proj is not None
        assert proj["affected_pop"] == 1500
        assert proj["gain_mean"] == 0.0
        assert proj["gain_popweighted"] == 0.0
        assert proj["wait_saving_min"] == 0.0
        assert proj["benefited_pop"] == 0
        assert "Add transit service" in proj["action"]


# ---------------------------------------------------------------------------
# Corridor list + geoid serving helpers
# ---------------------------------------------------------------------------
def test_sensitivity_corridors_sorted_and_complete() -> None:
    data = get_data()
    corridors = wi.sensitivity_corridors(data)
    assert len(corridors) == len(data["sensitivity"])  # 14, incl. coverage
    pops = [c["affected_pop"] for c in corridors]
    assert pops == sorted(pops, reverse=True)
    assert corridors[0]["corridor"] == "Route A Line"
    assert corridors[0]["affected_pop"] == 8871
    assert any(c["route_id"] is None for c in corridors)  # coverage row present


def test_route_ids_serving_geoid() -> None:
    data = get_data()
    rec = data["recommendations"].iloc[0]
    geoid = str(rec["geoids"][0])
    serving = wi.route_ids_serving_geoid(geoid, data)
    assert wi.route_key(rec["route_id"]) in serving
    assert wi.route_ids_serving_geoid("000000000000", data) == []


# ---------------------------------------------------------------------------
# Render smoke test (Streamlit replaced by a recording stub)
# ---------------------------------------------------------------------------
class Recorder:
    """Minimal stand-in for the streamlit module, capturing calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.session_state = type("SS", (), {"get": lambda self, k, d=None: d})()

    def _record(self, name: str, args: tuple, kwargs: dict) -> Any:
        self.calls.append((name, args, kwargs))
        if name == "selectbox":
            return ("100512", "Route A Line", 8871)
        if name == "slider":
            return 2.0
        return None

    def selectbox(self, *a, **k) -> Any:
        return self._record("selectbox", a, k)

    def slider(self, *a, **k) -> Any:
        return self._record("slider", a, k)

    def columns(self, *a, **k) -> list["RecorderMetric"]:
        return [RecorderMetric(self) for _ in range(int(a[0]) if a else 4)]

    def iframe(self, *a, **k) -> None:
        self._record("iframe", a, k)

    def markdown(self, *a, **k) -> None:
        self._record("markdown", a, k)

    def caption(self, *a, **k) -> None:
        self._record("caption", a, k)

    def info(self, *a, **k) -> None:
        self._record("info", a, k)

    def warning(self, *a, **k) -> None:
        self._record("warning", a, k)

    def metric(self, *a, **k) -> None:
        self._record("metric", a, k)

    @property
    def names(self) -> list[str]:
        return [name for name, _, _ in self.calls]


class RecorderMetric:
    def __init__(self, recorder: Recorder) -> None:
        self._recorder = recorder

    def metric(self, *a, **k) -> None:
        self._recorder.metric(*a, **k)


def test_render_whatif_produces_ui(monkeypatch) -> None:
    data = get_data()
    recorder = Recorder()
    monkeypatch.setattr(wi, "st", recorder)
    wi.render_whatif(data)
    names = recorder.names
    assert "selectbox" in names
    assert "slider" in names
    assert "metric" in names
    assert "markdown" in names or "caption" in names
    # The real Route A Line action text is rendered.
    action = _route_row(data, "100512")["action"]
    assert any(action in str(a) for name, a, _ in recorder.calls if name == "markdown")
