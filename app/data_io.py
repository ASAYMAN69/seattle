"""Central data loader for the Seattle Transit Equity Index app.

All prepared inputs are loaded through :func:`load_prepared`, which returns a
single typed dict keyed by logical name. If any file is missing or has
wrong/missing columns, a :class:`PreparedDataError` is raised with a precise
message naming the file and the problem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

# Single source of truth for all prepared-data paths.
PREPARED_DIR = Path(__file__).resolve().parents[1] / "data" / "prepared"

BOUNDARY_PATH = PREPARED_DIR / "seattle_boundary.geojson"
BLOCK_GROUPS_PATH = PREPARED_DIR / "census" / "block_groups.geojson"
EQUITY_SCORES_PATH = PREPARED_DIR / "equity" / "equity_scores.geojson"
REPORT_CARDS_PATH = PREPARED_DIR / "equity" / "report_cards.json"
RECOMMENDATIONS_PATH = PREPARED_DIR / "equity" / "recommendations.geojson"
SENSITIVITY_PATH = PREPARED_DIR / "equity" / "sensitivity.parquet"

# Minimum required columns for each file (extra columns are allowed).
_BOUNDARY_MIN_COLS: tuple[str, ...] = ("geometry",)
_BLOCK_GROUPS_MIN_COLS: tuple[str, ...] = ("geoid", "geometry")
_EQUITY_MIN_COLS: tuple[str, ...] = (
    "geoid",
    "jobs_access",
    "healthcare_access",
    "schools_access",
    "food_access",
    "access_overall",
    "need_index",
    "gap",
    "grade",
)
_RECOMMENDATIONS_MIN_COLS: tuple[str, ...] = (
    "route_id",
    "corridor",
    "action",
    "geometry",
)
_SENSITIVITY_MIN_COLS: tuple[str, ...] = (
    "route_id",
    "corridor",
    "action",
    "affected_pop",
    "est_access_gain_mean",
    "est_access_gain_popweighted",
)
_REPORT_CARDS_REQUIRED_KEYS: tuple[str, ...] = ("generated_at", "summary", "report_cards")


class PreparedDataError(Exception):
    """Raised when a prepared input is missing or malformed."""


def _read_geojson(
    path: Path, required_cols: tuple[str, ...], label: str
) -> gpd.GeoDataFrame:
    """Read a GeoJSON/GeoDataFrame and validate presence of required columns."""
    if not path.exists():
        raise PreparedDataError(f"{label} missing: {path}")
    try:
        gdf = gpd.read_file(path)
    except Exception as exc:  # noqa: BLE001 - report any read failure precisely
        raise PreparedDataError(f"{label} could not be read ({path}): {exc}") from exc
    if gdf.empty:
        raise PreparedDataError(f"{label} contains no features ({path})")
    missing = [col for col in required_cols if col not in gdf.columns]
    if missing:
        raise PreparedDataError(
            f"{label} missing required column(s): {', '.join(missing)} ({path})"
        )
    return gdf


def _read_report_cards(path: Path) -> dict[str, Any]:
    """Load the report-card JSON and validate its top-level structure."""
    if not path.exists():
        raise PreparedDataError(f"report cards missing: {path}")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        raise PreparedDataError(f"report cards could not be parsed ({path}): {exc}") from exc
    missing = [key for key in _REPORT_CARDS_REQUIRED_KEYS if key not in data]
    if missing:
        raise PreparedDataError(
            f"report cards missing required key(s): {', '.join(missing)} ({path})"
        )
    return data


def _read_sensitivity(path: Path) -> pd.DataFrame:
    """Load the sensitivity parquet and validate required columns."""
    if not path.exists():
        raise PreparedDataError(f"sensitivity missing: {path}")
    try:
        df = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001
        raise PreparedDataError(f"sensitivity could not be read ({path}): {exc}") from exc
    missing = [col for col in _SENSITIVITY_MIN_COLS if col not in df.columns]
    if missing:
        raise PreparedDataError(
            f"sensitivity missing required column(s): {', '.join(missing)} ({path})"
        )
    return df


def load_prepared() -> dict[str, Any]:
    """Load every prepared input into typed structures.

    Returns a dict keyed by logical name:

    - ``boundary``: ``geopandas.GeoDataFrame`` (Seattle boundary)
    - ``block_groups``: ``geopandas.GeoDataFrame`` (Census block groups)
    - ``equity_scores``: ``geopandas.GeoDataFrame`` (per-block-group scores/grades)
    - ``report_cards``: ``dict`` (report_cards.json root object)
    - ``recommendations``: ``geopandas.GeoDataFrame`` (corridor recommendations)
    - ``sensitivity``: ``pandas.DataFrame`` (what-if gain estimates)

    Raises:
        PreparedDataError: if any input is missing or malformed.
    """
    boundary = _read_geojson(BOUNDARY_PATH, _BOUNDARY_MIN_COLS, "Seattle boundary")
    block_groups = _read_geojson(
        BLOCK_GROUPS_PATH, _BLOCK_GROUPS_MIN_COLS, "Block groups"
    )
    equity_scores = _read_geojson(
        EQUITY_SCORES_PATH, _EQUITY_MIN_COLS, "Equity scores"
    )
    recommendations = _read_geojson(
        RECOMMENDATIONS_PATH, _RECOMMENDATIONS_MIN_COLS, "Recommendations"
    )
    sensitivity = _read_sensitivity(SENSITIVITY_PATH)
    report_cards = _read_report_cards(REPORT_CARDS_PATH)

    return {
        "boundary": boundary,
        "block_groups": block_groups,
        "equity_scores": equity_scores,
        "report_cards": report_cards,
        "recommendations": recommendations,
        "sensitivity": sensitivity,
    }
