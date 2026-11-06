"""API endpoints for the Seattle Transit Equity Index service.

All endpoints are read-only over the prepared data loaded once in ``api.data``.
Response shapes follow the contract in
``agents/wizard/tasks/fastapi-service-001.md``.

The top-underserved ranking and block-group lookup mirror the logic of
``app/views/export.py`` / ``app/views/report_card.py`` but are implemented
locally here so the API does not depend on the retiring Streamlit app.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import geopandas as gpd
from fastapi import APIRouter, HTTPException, Query

from typing import Literal

from api import scenarios as scen
from api import serialization as ser
from api.data import PREPARED

TimeOfDay = Literal["am_peak", "off_peak"]

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Top-underserved ranking (mirrors app/views/export.py, kept local)
# ---------------------------------------------------------------------------

SNAPSHOT_COLUMNS: tuple[str, ...] = (
    "geoid",
    "grade",
    "jobs_grade",
    "healthcare_grade",
    "schools_grade",
    "food_grade",
    "jobs_access",
    "healthcare_access",
    "schools_access",
    "food_access",
    "access_overall",
    "need_index",
    "gap",
    "pop_total",
    "poverty_pct",
    "zero_car_pct",
    "median_income",
)

# Letter-grade rank used to break ties (F first).
GRADE_RANK: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}


def build_top_underserved(
    prepared: dict[str, Any], n: int, time_of_day: str = "am_peak"
) -> pd.DataFrame:
    """Top ``n`` underserved block groups (plain DataFrame, no geometry).

    Ranked by ``need_index`` descending, then ``gap`` ascending, then letter
    grade F-first — identical semantics to ``app.views.export.build_top_underserved_table``.
    For ``off_peak`` the adjusted equity frame is used and an
    ``approximation_note`` column is added.
    """
    equity = scen.adjusted_equity_frame(prepared, time_of_day)
    df = equity[list(SNAPSHOT_COLUMNS)].copy()
    if scen.is_off_peak(time_of_day):
        df["approximation_note"] = scen.OFF_PEAK_NOTE
    df["_grade_rank"] = df["grade"].map(GRADE_RANK).fillna(len(GRADE_RANK))
    ranked = df.sort_values(
        ["need_index", "gap", "_grade_rank"],
        ascending=[False, True, False],
    )
    return ranked.drop(columns=["_grade_rank"]).reset_index(drop=True).head(n)


def lookup_block_group(geoid: str, prepared: dict[str, Any]) -> pd.Series | None:
    """Return the equity_scores row for ``geoid`` (or None if unknown)."""
    equity = prepared["equity_scores"]
    key = str(geoid).strip()
    matches = equity.loc[equity["geoid"].astype(str) == key]
    if matches.empty:
        return None
    return matches.iloc[0]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/boundary")
def boundary() -> dict[str, Any]:
    """Seattle boundary as a GeoJSON FeatureCollection."""
    return ser.gdf_to_featurecollection(PREPARED["boundary"])


@router.get("/equity")
def equity(
    time_of_day: TimeOfDay = Query("am_peak", description="am_peak (default) or off_peak"),
) -> dict[str, Any]:
    """Equity scores (with ACS demographics joined) as GeoJSON."""
    try:
        scen.validate_time_of_day(time_of_day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if scen.is_off_peak(time_of_day):
        df = scen.adjusted_equity_frame(PREPARED, time_of_day)
        gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=PREPARED["equity_scores"].crs)
        gdf["time_of_day"] = time_of_day
        gdf["scenario_id"] = time_of_day
        gdf["approximation_applied"] = True
        gdf["methodology_note"] = scen.equity_methodology_note(time_of_day)
        return ser.gdf_to_featurecollection(gdf)
    fc = ser.gdf_to_featurecollection(PREPARED["equity_scores"])
    return fc


@router.get("/recommendations")
def recommendations() -> dict[str, Any]:
    """Corridor recommendations as a GeoJSON FeatureCollection."""
    return ser.gdf_to_featurecollection(PREPARED["recommendations"])


@router.get("/sensitivity")
def sensitivity() -> list[dict[str, Any]]:
    """Sensitivity (what-if gain) table as plain JSON records."""
    return ser.frame_to_records(PREPARED["sensitivity"])


@router.get("/report-cards")
def report_cards() -> dict[str, Any]:
    """The report_cards.json root object (generated_at, summary, per-BG cards)."""
    return PREPARED["report_cards"]


@router.get("/top-underserved")
def top_underserved(
    n: int = Query(
        25, ge=1, le=5000, description="Number of block groups to return."
    ),
    time_of_day: TimeOfDay = Query("am_peak", description="am_peak (default) or off_peak"),
) -> list[dict[str, Any]]:
    """Top-N underserved block groups (plain records, no geometry)."""
    try:
        scen.validate_time_of_day(time_of_day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ser.frame_to_records(build_top_underserved(PREPARED, n, time_of_day))


@router.get("/block-group/{geoid}")
def block_group(
    geoid: str,
    time_of_day: TimeOfDay = Query("am_peak", description="am_peak (default) or off_peak"),
) -> dict[str, Any]:
    """One block group's full equity row (with ACS stats) as a GeoJSON feature."""
    try:
        scen.validate_time_of_day(time_of_day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    equity = scen.adjusted_equity_frame(PREPARED, time_of_day)
    key = str(geoid).strip()
    matches = equity.loc[equity["geoid"].astype(str) == key]
    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Block group {geoid!r} not found in equity data.",
        )
    row = matches.iloc[0]
    props = {
        col: ser.clean_value(row[col])
        for col in equity.columns
        if col != "geometry"
    }
    if scen.is_off_peak(time_of_day):
        props["time_of_day"] = time_of_day
        props["scenario_id"] = time_of_day
        props["approximation_applied"] = True
        props["methodology_note"] = scen.equity_methodology_note(time_of_day)
    return {
        "type": "Feature",
        "geometry": ser.geometry_to_geojson(row.geometry),
        "properties": props,
    }


@router.get("/metadata")
def metadata() -> dict[str, Any]:
    """Small metadata object for footers: generated_at, summary, data counts."""
    rc = PREPARED["report_cards"]
    return {
        "app": "Seattle Transit Equity Index",
        "generated_at": rc.get("generated_at"),
        "summary": rc.get("summary", {}),
        "data_counts": {
            "n_block_groups": len(PREPARED["equity_scores"]),
            "n_recommendations": len(PREPARED["recommendations"]),
            "n_sensitivity_rows": len(PREPARED["sensitivity"]),
        },
        "methodology_note": (
            "Equity scores, letter grades, and ACS statistics are from the "
            "prepared DataNova 2026 transit-equity analysis. The equity gap = "
            "access − need (positive = better served). No live routing or API keys."
        ),
        "scenarios": {s["id"]: s for s in scen.SCENARIOS},
    }


@router.get("/scenarios")
def scenarios() -> list[dict[str, Any]]:
    """Both scenario descriptors (id, label, is_full_compute, basis, notes)."""
    return list(scen.SCENARIOS)
