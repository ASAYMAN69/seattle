"""Serialization helpers for the FastAPI service.

Geometric datasets are served as GeoJSON FeatureCollections; tabular datasets
as plain JSON record arrays. Values are cleaned for JSON output:

- numpy scalars are converted to native Python types;
- NaN/inf and pandas missing scalars (pd.NA, pd.NaT, ...) become ``null``;
- the ACS suppressed-income sentinel (-666,666,666) is treated as missing
  (context/decisions.md: "treated as missing (component skipped)"), so it is
  never surfaced to the frontend as a literal number.

This module must stay free of Streamlit imports so the API can outlive the
retiring Streamlit app.
"""

from __future__ import annotations

import json
import math
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import to_geojson
from shapely.geometry.base import BaseGeometry

# ACS Summary File suppression sentinel (value means "missing").
ACS_SUPPRESSED_SENTINEL = -666_666_666


def clean_value(value: Any) -> Any:
    """Return a JSON-safe conversion of ``value`` (NaN/sentinel -> None)."""
    if isinstance(value, np.ndarray):
        return [clean_value(v) for v in value.tolist()]
    if isinstance(value, np.integer):
        v = int(value)
        return None if v == ACS_SUPPRESSED_SENTINEL else v
    if isinstance(value, (np.floating, float)):
        v = float(value)
        if not math.isfinite(v):
            return None
        return None if v == ACS_SUPPRESSED_SENTINEL else v
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (int, float)) and value == ACS_SUPPRESSED_SENTINEL:
        return None
    return value


def geometry_to_geojson(geom: BaseGeometry | None) -> dict[str, Any] | None:
    """Convert a shapely geometry to a GeoJSON geometry dict (None if empty)."""
    if geom is None or geom.is_empty:
        return None
    return json.loads(to_geojson(geom))


def gdf_to_featurecollection(gdf: gpd.GeoDataFrame) -> dict[str, Any]:
    """Serialize a GeoDataFrame as a GeoJSON FeatureCollection dict."""
    features: list[dict[str, Any]] = []
    for _, row in gdf.iterrows():
        features.append(
            {
                "type": "Feature",
                "geometry": geometry_to_geojson(row.geometry),
                "properties": {
                    col: clean_value(row[col])
                    for col in gdf.columns
                    if col != "geometry"
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def frame_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Serialize a DataFrame as a list of plain JSON records."""
    return [
        {str(col): clean_value(row[col]) for col in df.columns}
        for _, row in df.iterrows()
    ]
