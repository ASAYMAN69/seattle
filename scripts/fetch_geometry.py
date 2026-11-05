"""Fetch the real Seattle city boundary from Census TIGER/Line and write it to
data/prepared/seattle_boundary.geojson.

Source: U.S. Census Bureau TIGER/Line 2023 Places (state 53 = Washington).
"""

import io
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2023/PLACE/tl_2023_53_place.zip"
PLACE_NAME = "Seattle"
OUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "prepared"
    / "seattle_boundary.geojson"
)


def fetch_tiger_place_zip(url: str = TIGER_URL) -> bytes:
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.content


def extract_and_read_place_shapefile(zip_bytes: bytes, extract_dir: Path) -> gpd.GeoDataFrame:
    """Extract the TIGER shapefile zip to disk and read the .shp."""
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(extract_dir)
    shp_path = next(extract_dir.glob("*.shp"))
    return gpd.read_file(shp_path)


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = OUT_PATH.parents[1] / "raw" / "tiger_place_wa"
    gdf = extract_and_read_place_shapefile(
        fetch_tiger_place_zip(), extract_dir=raw_dir
    )
    seattle = gdf[gdf["NAME"] == PLACE_NAME].copy()
    if seattle.empty:
        raise ValueError(f"Place '{PLACE_NAME}' not found in TIGER dataset")
    seattle = seattle.to_crs(epsg=4326)[["NAME", "geometry"]]
    seattle.to_file(OUT_PATH, driver="GeoJSON")
    area_km2 = float(seattle.geometry.area.sum() * 111.32 * 111.32)
    print(
        f"Wrote {OUT_PATH} — {len(seattle)} feature(s), "
        f"~{area_km2:.0f} km²"
    )


if __name__ == "__main__":
    main()
