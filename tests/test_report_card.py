"""Tests for the neighborhood Equity Report Card (Task 3.2).

These run against the real prepared data (``app.data_io.load_prepared``), so
they verify that the report-card helpers return correct grades/stats for a
known geoid and degrade gracefully for an unknown one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.data_io import load_prepared
from app.views import report_card as rc

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "prepared"
ACS_PARQUET = DATA_DIR / "census" / "acs_demographics.parquet"

_DATA: dict[str, Any] | None = None


def get_data() -> dict[str, Any]:
    """Load real prepared data once per test session (it is heavy)."""
    global _DATA
    if _DATA is None:
        _DATA = load_prepared()
    return _DATA


class Recorder:
    """Minimal stand-in for the streamlit module, capturing calls."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def markdown(self, body: str, **_: Any) -> None:
        self.calls.append(("markdown", body))

    def caption(self, body: str, **_: Any) -> None:
        self.calls.append(("caption", body))

    def info(self, body: str, **_: Any) -> None:
        self.calls.append(("info", body))

    def warning(self, body: str, **_: Any) -> None:
        self.calls.append(("warning", body))

    @property
    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


def _known_geoid_with_recommendation(data: dict[str, Any]) -> str:
    recommendation = data["recommendations"]
    return str(recommendation.iloc[0]["geoids"][0])


def _source_row(data: dict[str, Any], geoid: str) -> pd.Series:
    equity = data["equity_scores"]
    return equity.loc[equity["geoid"].astype(str) == geoid].iloc[0]


# ---------------------------------------------------------------------------
# Known geoid: stats + grades come from the real data
# ---------------------------------------------------------------------------
def test_get_neighborhood_summary_known_geoid_matches_acs() -> None:
    data = get_data()
    geoid = str(data["equity_scores"].iloc[0]["geoid"])

    summary = rc.get_neighborhood_summary(geoid, data)
    assert summary is not None
    assert summary["geoid"] == geoid

    row = _source_row(data, geoid)
    assert summary["pop_total"] == int(row["pop_total"])
    assert summary["poverty_pct"] == pytest.approx(float(row["poverty_pct"]))
    assert summary["zero_car_pct"] == pytest.approx(float(row["zero_car_pct"]))
    assert summary["median_income"] == pytest.approx(float(row["median_income"]))

    # Cross-check against the raw ACS source file.
    acs = pd.read_parquet(ACS_PARQUET)
    acs_row = acs.loc[acs["geoid"].astype(str) == geoid].iloc[0]
    assert summary["pop_total"] == int(acs_row["pop_total"])
    assert summary["poverty_pct"] == pytest.approx(float(acs_row["poverty_pct"]))
    assert summary["zero_car_pct"] == pytest.approx(float(acs_row["zero_car_pct"]))
    assert summary["median_income"] == pytest.approx(float(acs_row["median_income"]))


def test_get_grades_known_geoid() -> None:
    data = get_data()
    geoid = str(data["equity_scores"].iloc[0]["geoid"])

    grades = rc.get_grades(geoid, data)
    assert grades is not None
    assert [g["dimension"] for g in grades] == [
        dim for dim, _ in rc.GRADE_DIMENSIONS
    ]

    row = _source_row(data, geoid)
    for item in grades:
        assert item["grade"] == str(row[item["column"]]).strip().upper()


def test_get_top_recommendations_known_geoid() -> None:
    data = get_data()
    geoid = _known_geoid_with_recommendation(data)

    recommendations = rc.get_top_recommendations(geoid, data)
    assert recommendations
    assert len(recommendations) <= 3
    for item in recommendations:
        assert item["corridor"]
        assert item["action"]
        assert item["affected_pop"] is not None

    populations = [item["affected_pop"] for item in recommendations]
    assert populations == sorted(populations, reverse=True)


def test_get_top_recommendations_limited_to_k() -> None:
    data = get_data()
    geoid = _known_geoid_with_recommendation(data)

    top1 = rc.get_top_recommendations(geoid, data, k=1)
    assert len(top1) == 1
    all_recs = rc.get_top_recommendations(geoid, data)
    assert top1[0]["affected_pop"] == max(
        item["affected_pop"] for item in all_recs
    )


def test_get_top_recommendations_for_geoid_without_recs() -> None:
    data = get_data()
    # Find a block group that no corridor recommendation serves.
    served: set[str] = set()
    for geoids in data["recommendations"]["geoids"]:
        served.update(str(g) for g in geoids)
    unserved = next(
        str(g)
        for g in data["equity_scores"]["geoid"].astype(str)
        if str(g) not in served
    )
    assert rc.get_top_recommendations(unserved, data) == []


# ---------------------------------------------------------------------------
# Missing / unknown geoid: handled gracefully
# ---------------------------------------------------------------------------
UNKNOWN_GEOID = "535353535353"


def test_lookup_unknown_geoid_returns_none() -> None:
    data = get_data()
    assert rc.lookup_block_group(UNKNOWN_GEOID, data) is None
    assert rc.get_neighborhood_summary(UNKNOWN_GEOID, data) is None
    assert rc.get_grades(UNKNOWN_GEOID, data) is None
    assert rc.get_top_recommendations(UNKNOWN_GEOID, data) == []


def test_render_unknown_geoid_shows_warning(monkeypatch) -> None:
    data = get_data()
    recorder = Recorder()
    monkeypatch.setattr(rc, "st", recorder)
    rc.render_report_card(UNKNOWN_GEOID, data)
    assert "warning" in recorder.names
    assert "markdown" not in recorder.names


def test_render_no_selection_shows_info(monkeypatch) -> None:
    data = get_data()
    recorder = Recorder()
    monkeypatch.setattr(rc, "st", recorder)
    rc.render_report_card(None, data)
    assert "info" in recorder.names


# ---------------------------------------------------------------------------
# Render: known geoid produces stats, grade chips, and recommendations
# ---------------------------------------------------------------------------
def test_render_known_geoid_outputs_statsgrades_and_recommendations(
    monkeypatch,
) -> None:
    data = get_data()
    geoid = _known_geoid_with_recommendation(data)

    recorder = Recorder()
    monkeypatch.setattr(rc, "st", recorder)
    rc.render_report_card(geoid, data)

    markdown = "".join(body for name, body in recorder.calls if name == "markdown")

    # Identity + ACS stats (formatted).
    assert "Block Group" in markdown
    assert "Population" in markdown
    assert "Poverty rate" in markdown
    assert "Zero-car households" in markdown
    assert "Median income" in markdown
    assert "%" in markdown
    assert "$" in markdown

    # Grade chips for every dimension.
    for dimension, _col in rc.GRADE_DIMENSIONS:
        assert dimension in markdown

    # Recommendations (corridor text should appear in the rendered output).
    expected_corridors = {
        item["corridor"] for item in rc.get_top_recommendations(geoid, data)
    }
    for corridor in expected_corridors:
        assert corridor in markdown
