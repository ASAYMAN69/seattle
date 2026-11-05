"""Tests for the Export & summary view (Task 3.4).

These run against the real prepared data (``app.data_io.load_prepared``), so
they verify that the CSV builders return correct columns/rows/ordering for
known data and that the renderer degrades gracefully for an empty (or unknown)
selection.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from app.data_io import load_prepared
from app.views import export as ex

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

    def subheader(self, body: str, **_: Any) -> None:
        self.calls.append(("subheader", body))

    def caption(self, body: str, **_: Any) -> None:
        self.calls.append(("caption", body))

    def markdown(self, body: str, **_: Any) -> None:
        self.calls.append(("markdown", body))

    def dataframe(self, frame: pd.DataFrame, **_: Any) -> None:
        self.calls.append(("dataframe", frame))

    def download_button(
        self, label: str, data: str, file_name: str | None = None,
        mime: str | None = None, **_: Any,
    ) -> None:
        self.calls.append(("download_button", label, data, file_name, mime))

    def info(self, body: str, **_: Any) -> None:
        self.calls.append(("info", body))

    def warning(self, body: str, **_: Any) -> None:
        self.calls.append(("warning", body))

    @property
    def names(self) -> list[str]:
        return [call[0] for call in self.calls]

    def downloads(self) -> list[tuple[str, str, str | None, str | None]]:
        return [
            call[1:] for call in self.calls if call[0] == "download_button"
        ]


def _known_geoid(data: dict[str, Any]) -> str:
    return str(data["equity_scores"].iloc[0]["geoid"])


def _source_row(data: dict[str, Any], geoid: str) -> pd.Series:
    equity = data["equity_scores"]
    return equity.loc[equity["geoid"].astype(str) == geoid].iloc[0]


# ---------------------------------------------------------------------------
# City-wide top-N underserved table
# ---------------------------------------------------------------------------
def test_top_underserved_default_shape_and_columns() -> None:
    data = get_data()
    top = ex.build_top_underserved_table(data)
    assert len(top) == ex.TOP_N_DEFAULT == 25
    assert list(top.columns) == list(ex.SNAPSHOT_COLUMNS)
    assert "geometry" not in top.columns
    assert "_grade_rank" not in top.columns
    assert top["geoid"].astype(str).is_unique


def test_top_underserved_ordering_by_need_then_gap_then_grade() -> None:
    data = get_data()
    top = ex.build_top_underserved_table(data)

    need = top["need_index"].to_numpy()
    assert (need[1:] <= need[:-1]).all()

    gap = top["gap"].to_numpy()
    need_np = top["need_index"].to_numpy()
    for i in range(len(top) - 1):
        if need_np[i] == need_np[i + 1]:
            assert gap[i] <= gap[i + 1]

    # Within a need/gap tie, F must rank before A.
    rank = top["grade"].map(ex.GRADE_RANK)
    for i in range(len(top) - 1):
        if (need_np[i] == need_np[i + 1]) and (gap[i] == gap[i + 1]):
            assert rank.iloc[i] >= rank.iloc[i + 1]


def test_top_underserved_n_param() -> None:
    data = get_data()
    assert len(ex.build_top_underserved_table(data, n=5)) == 5
    assert len(ex.build_top_underserved_table(data, n=1)) == 1


def test_top_underserved_first_row_is_max_need() -> None:
    data = get_data()
    top = ex.build_top_underserved_table(data)
    equity = data["equity_scores"]
    assert top.iloc[0]["need_index"] == equity["need_index"].max()


# ---------------------------------------------------------------------------
# Report-card snapshot
# ---------------------------------------------------------------------------
def test_report_card_snapshot_known_geoid_matches_source() -> None:
    data = get_data()
    geoid = _known_geoid(data)
    snap = ex.build_report_card_snapshot(geoid, data)
    assert snap is not None
    assert list(snap.columns) == list(ex.SNAPSHOT_COLUMNS)
    assert len(snap) == 1
    assert str(snap.iloc[0]["geoid"]) == geoid

    row = _source_row(data, geoid)
    for col in ex.SNAPSHOT_COLUMNS:
        assert snap.iloc[0][col] == row[col]


def test_report_card_snapshot_unknown_geoid_returns_none() -> None:
    data = get_data()
    assert ex.build_report_card_snapshot("535353535353", data) is None
    assert ex.build_report_card_snapshot(None, data) is None


# ---------------------------------------------------------------------------
# CSV serialization
# ---------------------------------------------------------------------------
def test_to_csv_header_and_rows() -> None:
    data = get_data()
    top = ex.build_top_underserved_table(data, n=5)
    csv = ex.to_csv(top)
    lines = csv.strip().splitlines()
    assert lines[0] == ",".join(ex.SNAPSHOT_COLUMNS)
    assert len(lines) == 6  # header + 5 rows
    assert str(top.iloc[0]["geoid"]) in csv


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def test_render_export_empty_selection(monkeypatch) -> None:
    data = get_data()
    recorder = Recorder()
    monkeypatch.setattr(ex, "st", recorder)

    ex.render_export(data)  # no selection (no session state in bare run)

    assert "subheader" in recorder.names
    assert "caption" in recorder.names
    assert "info" in recorder.names
    downloads = recorder.downloads()
    assert len(downloads) == 1
    label, payload, file_name, mime = downloads[0]
    assert "city-wide" in label.lower()
    assert "seattle_top_underserved.csv" in (file_name or "")
    assert mime == "text/csv"
    assert payload.strip().splitlines()[0] == ",".join(ex.SNAPSHOT_COLUMNS)


def test_render_export_with_selection(monkeypatch) -> None:
    data = get_data()
    geoid = _known_geoid(data)
    recorder = Recorder()
    monkeypatch.setattr(ex, "st", recorder)

    ex.render_export(data, selected_geoid=geoid)

    assert "info" not in recorder.names
    downloads = recorder.downloads()
    assert len(downloads) == 2

    # Report-card snapshot download carries the geoid.
    snapshot_dl = next(
        d for d in downloads if "report card" in d[0].lower()
    )
    _label, payload, file_name, mime = snapshot_dl
    assert geoid in payload
    assert file_name == f"seattle_report_card_{geoid}.csv"
    assert mime == "text/csv"

    city_dl = next(d for d in downloads if "city-wide" in d[0].lower())
    city_lines = city_dl[1].strip().splitlines()
    assert len(city_lines) == 1 + ex.TOP_N_DEFAULT


def test_render_export_unknown_geoid_warns(monkeypatch) -> None:
    data = get_data()
    recorder = Recorder()
    monkeypatch.setattr(ex, "st", recorder)

    ex.render_export(data, selected_geoid="535353535353")

    assert "warning" in recorder.names
    assert len(recorder.downloads()) == 1  # city-wide still offered
