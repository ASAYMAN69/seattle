"""Fetch opportunity POIs for the Seattle Transit Equity Index.

Produces four GeoJSON files (EPSG:4326) under ``data/prepared/opportunities/``:

- ``jobs.geojson``        — workplace employment points from Census LEHD/LODES
  (Washington, 2022 Workplace Area Characteristics), filtered to King County
  (FIPS 53033). Each point is a census block centroid with ``weight`` = total
  jobs in that block (LODES ``C000`` column). ``name`` = 15-digit block GEOID.
- ``healthcare.geojson``  — OSM ``amenity`` in {hospital, clinic} inside the
  Seattle boundary bbox (expanded ~0.03°).
- ``schools.geojson``     — OSM ``amenity``=school inside the same bbox.
- ``food.geojson``        — OSM ``shop`` in {supermarket, grocery} OR
  ``amenity``=food_bank inside the same bbox.

Sources:
- LODES Workplace Area Characteristics (WA 2022):
  https://lehd.ces.census.gov/data/lodes/LODES8/wa/wac/wa_wac_S000_JT00_2022.csv.gz
  (The brief's LODES7 URL 404s; LODES8 is the current release for the same
  year/measure. The "csv.gz" payload is served as plain CSV.)
- TIGER/Line 2020 tabblock20 (WA):
  https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_53_tabblock20.zip
- OpenStreetMap via the Overpass API (overpy).
"""

from __future__ import annotations

import io
import sys
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point

try:
    import overpy
except ImportError:  # pragma: no cover
    overpy = None

ROOT = Path(__file__).resolve().parents[1]
RAW_OPP = ROOT / "data" / "raw" / "opportunities"
PREP_OPP = ROOT / "data" / "prepared" / "opportunities"

LODES_URL = (
    "https://lehd.ces.census.gov/data/lodes/LODES8/wa/wac/"
    "wa_wac_S000_JT00_2022.csv.gz"
)
TIGER_BLOCK_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/"
    "tl_2020_53_tabblock20.zip"
)
TIGER_BLOCK_DIR = RAW_OPP / "tiger_block20"

# Overpass mirrors; we rotate on hard failures and back off on 429
# (respecting Overpass etiquette). overpass-api.de is primary; osm.ch is a
# fallback (it occasionally returns empty JSON/HTML when overloaded, which is
# treated as a failure below). Unreachable mirrors are excluded to avoid long
# connect timeouts.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]
USER_AGENT = "SeattleTransitEquity/1.0 (DataNova 2026 hackathon)"

HEADERS = {"User-Agent": USER_AGENT, "Accept": "*/*"}


def download(url: str, out_path: Path, timeout: int = 300, tries: int = 3):
    """Download ``url`` to ``out_path`` with retries on transient errors."""
    last_err: Exception | None = None
    for attempt in range(tries):
        try:
            resp = requests.get(url, timeout=timeout, headers=HEADERS)
            if resp.status_code == 429:
                raise RuntimeError("HTTP 429 rate-limited")
            resp.raise_for_status()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(resp.content)
            return out_path
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt < tries - 1:
                time.sleep(2 + attempt * 2)
    raise RuntimeError(f"Failed to download {url}: {last_err}")


def read_lodes_jobs() -> pd.DataFrame:
    """Return LODES WA 2022 WAC rows for King County (FIPS 53033)."""
    raw_path = RAW_OPP / "lodes" / "wa_wac_S000_JT00_2022.csv.gz"
    download(LODES_URL, raw_path)
    try:
        df = pd.read_csv(raw_path, compression="gzip")
    except Exception:
        # Some mirrors serve the payload as plain CSV despite the .gz name.
        df = pd.read_csv(raw_path)
    df["w_geocode"] = df["w_geocode"].astype(str).str.zfill(15)
    king = df[df["w_geocode"].str.startswith("53033")].copy()
    if king.empty:
        raise RuntimeError("No King County rows found in LODES WAC data")
    return king


def load_king_county_blocks() -> gpd.GeoDataFrame:
    """Load TIGER 2020 tabblock20 for WA, filtered to King County (033)."""
    zpath = RAW_OPP / "tiger_block20.zip"
    download(TIGER_BLOCK_URL, zpath)
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(TIGER_BLOCK_DIR)
    shp = next(TIGER_BLOCK_DIR.glob("*.shp"))
    blocks = gpd.read_file(shp)
    blocks = blocks[blocks["COUNTYFP20"] == "033"].copy()
    blocks["GEOID20"] = blocks["GEOID20"].astype(str).str.zfill(15)
    # Project to UTM 10N for accurate centroids, then back to 4326.
    blocks = blocks.to_crs(epsg=32610)
    blocks["centroid"] = blocks.geometry.centroid
    centroids = (
        gpd.GeoDataFrame(blocks[["GEOID20"]], geometry=blocks["centroid"])
        .set_crs(epsg=32610)
        .to_crs(epsg=4326)
    )
    return centroids


def build_jobs() -> gpd.GeoDataFrame:
    """Build the jobs GeoDataFrame (King County block centroids, weight=C000)."""
    jobs = read_lodes_jobs()
    centroids = load_king_county_blocks()
    merged = jobs.merge(
        centroids, left_on="w_geocode", right_on="GEOID20", how="inner"
    )
    if merged.empty:
        raise RuntimeError("No LODES rows matched King County block centroids")
    gdf = gpd.GeoDataFrame(
        {
            "name": merged["w_geocode"],
            "weight": merged["C000"].astype(int),
            "category": "jobs",
        },
        geometry=merged.geometry,
        crs="EPSG:4326",
    )
    return gdf


def overpass_query(query: str, tries: int = 12) -> overpy.Result:
    """Run one Overpass query with endpoint rotation, retry and 429 backoff.

    Transport is driven by ``requests`` (so we can set a proper User-Agent and
    observe 429s); responses are parsed with overpy's ``Result.from_json``.

    A 200 response with a non-JSON body or an empty element set is treated as a
    failure (some mirrors return empty JSON/HTML when overloaded) and we retry
    on another endpoint/attempt.
    """
    if overpy is None:
        raise RuntimeError("overpy is not installed")
    last_err: Exception | None = None
    for attempt in range(tries):
        endpoint = OVERPASS_ENDPOINTS[attempt % len(OVERPASS_ENDPOINTS)]
        try:
            resp = requests.post(
                endpoint,
                data={"data": query},
                timeout=(10, 60),
                headers=HEADERS,
            )
            if resp.status_code == 429:  # Respect Overpass etiquette: back off.
                time.sleep(2 + attempt % 4)
                continue
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "json" not in content_type:
                raise RuntimeError(
                    f"unexpected content-type {content_type!r} from {endpoint}"
                )
            payload = resp.json()
            if not payload.get("elements"):
                raise RuntimeError(f"empty element set from {endpoint}")
            return overpy.Result.from_json(payload)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            # Back off 2-5s before trying the next endpoint / attempt.
            time.sleep(2 + attempt % 4)
    raise RuntimeError(f"Overpass query failed after {tries} tries: {last_err}")


def build_osm_points(category: str, query: str, bbox: tuple) -> gpd.GeoDataFrame:
    """Run an Overpass query and flatten node/way results to points.

    ``bbox`` is (miny, minx, maxy, maxx) as used in the Overpass query; final
    points are filtered to it because ``out center`` on ways that straddle the
    bbox edge can yield centers slightly outside it.
    """
    result = overpass_query(query)
    rows: list[dict] = []
    for node in result.nodes:
        rows.append({"name": node.tags.get("name"), "geom": Point(node.lon, node.lat)})
    for way in result.ways:
        lon = getattr(way, "center_lon", None)
        lat = getattr(way, "center_lat", None)
        if lon is not None and lat is not None:
            rows.append({"name": way.tags.get("name"), "geom": Point(lon, lat)})
    gdf = gpd.GeoDataFrame(rows, geometry="geom", crs="EPSG:4326")
    gdf["weight"] = 1
    gdf["category"] = category
    miny, minx, maxy, maxx = bbox
    inside = (
        (gdf.geometry.x >= minx)
        & (gdf.geometry.x <= maxx)
        & (gdf.geometry.y >= miny)
        & (gdf.geometry.y <= maxy)
    )
    return gdf[inside].reset_index(drop=True)


def main() -> None:
    PREP_OPP.mkdir(parents=True, exist_ok=True)
    RAW_OPP.mkdir(parents=True, exist_ok=True)

    # --- Jobs (Census LEHD/LODES) ---
    jobs = build_jobs()
    jobs_path = PREP_OPP / "jobs.geojson"
    jobs.to_file(jobs_path, driver="GeoJSON")
    print(
        f"jobs: {len(jobs)} points, {int(jobs['weight'].sum()):,} total jobs -> "
        f"{jobs_path.name}"
    )

    # --- Bbox from clean boundary, expanded ~0.03° ---
    boundary = gpd.read_file(ROOT / "data" / "prepared" / "seattle_boundary.geojson")
    minx, miny, maxx, maxy = boundary.total_bounds
    pad = 0.03
    bbox = (miny - pad, minx - pad, maxy + pad, maxx + pad)
    bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
    print(f"OSM bbox: {bbox_str}")

    specs = {
        "healthcare": (
            f'[out:json][timeout:90];('
            f'node["amenity"~"^(hospital|clinic)$"]({bbox_str});'
            f'way["amenity"~"^(hospital|clinic)$"]({bbox_str});'
            f');out center;'
        ),
        "schools": (
            f'[out:json][timeout:90];('
            f'node["amenity"="school"]({bbox_str});'
            f'way["amenity"="school"]({bbox_str});'
            f');out center;'
        ),
        "food": (
            f'[out:json][timeout:90];('
            f'node["shop"~"^(supermarket|grocery)$"]({bbox_str});'
            f'way["shop"~"^(supermarket|grocery)$"]({bbox_str});'
            f'node["amenity"="food_bank"]({bbox_str});'
            f'way["amenity"="food_bank"]({bbox_str});'
            f');out center;'
        ),
    }

    for category, query in specs.items():
        gdf = build_osm_points(category, query, bbox)
        out_path = PREP_OPP / f"{category}.geojson"
        gdf.to_file(out_path, driver="GeoJSON")
        named = int(gdf["name"].notna().sum())
        print(
            f"{category}: {len(gdf)} points ({named} named) -> {out_path.name}"
        )

    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
