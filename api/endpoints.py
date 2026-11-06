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
from fastapi import APIRouter, HTTPException, Query

from api import serialization as ser
from api.data import PREPARED

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


def build_top_underserved(prepared: dict[str, Any], n: int) -> pd.DataFrame:
    """Top ``n`` underserved block groups (plain DataFrame, no geometry).

    Ranked by ``need_index`` descending, then ``gap`` ascending, then letter
    grade F-first — identical semantics to ``app.views.export.build_top_underserved_table``.
    """
    equity = prepared["equity_scores"]
    df = equity[list(SNAPSHOT_COLUMNS)].copy()
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
def equity() -> dict[str, Any]:
    """Equity scores (with ACS demographics joined) as GeoJSON."""
    return ser.gdf_to_featurecollection(PREPARED["equity_scores"])


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
) -> list[dict[str, Any]]:
    """Top-N underserved block groups (plain records, no geometry)."""
    return ser.frame_to_records(build_top_underserved(PREPARED, n))


@router.get("/block-group/{geoid}")
def block_group(geoid: str) -> dict[str, Any]:
    """One block group's full equity row (with ACS stats) as a GeoJSON feature."""
    row = lookup_block_group(geoid, PREPARED)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Block group {geoid!r} not found in equity data.",
        )
    equity = PREPARED["equity_scores"]
    props = {
        col: ser.clean_value(row[col])
        for col in equity.columns
        if col != "geometry"
    }
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
    }
