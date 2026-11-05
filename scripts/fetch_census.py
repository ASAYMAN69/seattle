"""Fetch real Census data for King County, WA (Seattle metro) — Task 1.2.

Step 1 — Block-group geometry:
    TIGER/Line 2023 Block Groups for Washington (tl_2023_53_bg.zip)
    -> extract -> read with geopandas -> filter COUNTYFP == "033" (King County)
    -> write data/prepared/census/block_groups.geojson

Step 2 — ACS 5-year (2022) block-group demographics:
    Preferred source: Census Data API
        https://api.census.gov/data/2022/acs/acs5
        get=<variables>&for=block%20group:*&in=state:53%20county:033
        Uses CENSUS_API_KEY env var if set; attempts unauthenticated otherwise.
    Fallback source (no key available): the official Census table-based ACS
        5-year Summary File bulk .dat tables (real data, no key required):
        https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/data/5YRData/
        NOTE: that source does not publish the original B17001/B08201 tables at
        block-group level, so block-group-level equivalents are used:
        B17021 (poverty status) and B25044 (tenure by vehicles available).
    -> derive percentages -> write data/prepared/census/acs_demographics.parquet

Outputs (owned by this task):
    data/raw/census/tiger_bg/                    (extracted TIGER shapefile)
    data/prepared/census/block_groups.geojson
    data/prepared/census/acs_demographics.parquet
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

HTTP_ATTEMPTS = 5
HTTP_BACKOFF_BASE = 1.5  # seconds; doubles per retry


def http_get_with_retry(
    url: str,
    *,
    params: dict | None = None,
    stream: bool = False,
    timeout: int = 300,
    attempts: int = HTTP_ATTEMPTS,
) -> requests.Response:
    """GET with retry/backoff to ride out transient DNS/network failures."""
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, params=params, stream=stream, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == attempts:
                break
            wait = HTTP_BACKOFF_BASE * (2 ** (attempt - 1))
            print(f"    retry {attempt}/{attempts - 1} for {url} in {wait:.0f}s "
                  f"({type(exc).__name__})")
            time.sleep(wait)
    raise last_exc if last_exc else RuntimeError(f"GET failed: {url}")  # type: ignore[misc]

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "census"
TIGER_EXTRACT_DIR = RAW_DIR / "tiger_bg"
PREPARED_DIR = ROOT / "data" / "prepared" / "census"
BG_GEOJSON_PATH = PREPARED_DIR / "block_groups.geojson"
ACS_PARQUET_PATH = PREPARED_DIR / "acs_demographics.parquet"

TIGER_BG_URL = "https://www2.census.gov/geo/tiger/TIGER2023/BG/tl_2023_53_bg.zip"
ACS_API_URL = "https://api.census.gov/data/2022/acs/acs5"
ACS_SF_BASE = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/"
    "2022/table-based-SF/data/5YRData"
)

STATE_FIPS = "53"   # Washington
COUNTY_FIPS = "033"  # King County
BG_GEOID_PREFIX = "1500000US"  # summary-file GEO_ID prefix for block groups
BG_KING_PREFIX = BG_GEOID_PREFIX + STATE_FIPS + COUNTY_FIPS  # ... + "53033"

KING_COUNTY_POP_REF = 2_269_000  # ACS 5-yr 2022 King County population (approx.)

# ACS variables (as named by the Census Data API).
ACS_VARIABLES = [
    "B19013_001E",  # median household income
    "B17001_001E",  # poverty universe (population for whom poverty determined)
    "B17001_002E",  # income in past 12 months below poverty level
    "B08201_001E",  # total households (vehicle availability universe)
    "B08201_002E",  # households with no vehicle available
    "B03002_001E",  # total race universe
    "B03002_003E",  # not Hispanic or Latino: White alone
    "B01001_001E",  # total population
    *[f"B01001_{i:03d}E" for i in range(20, 26)],  # male 65 years and over
    *[f"B01001_{i:03d}E" for i in range(44, 50)],  # female 65 years and over
]
ELDERLY_COLS = [
    *[f"B01001_{i:03d}E" for i in range(20, 26)],
    *[f"B01001_{i:03d}E" for i in range(44, 50)],
]

# ACS tables needed for the bulk Summary File fallback (API variable -> table).
# NOTE: The table-based Summary File does NOT publish the original B17001
# (poverty by sex/age) or B08201 (vehicle availability) tables at block-group
# level (they stop at tracts). We use the block-group-level equivalents:
#   B17021 (poverty status by living arrangement) -> poverty_pct
#   B25044 (tenure by vehicles available) -> zero_car_pct
#   (B25044: E001 = total occupied housing units, E003 = owner no vehicle,
#    E010 = renter no vehicle)
SF_TABLES = {
    "B19013": ["B19013_001E"],
    "B17021": ["B17021_001E", "B17021_002E"],
    "B25044": ["B25044_001E", "B25044_003E", "B25044_010E"],
    "B03002": ["B03002_001E", "B03002_003E"],
    "B01001": ["B01001_001E", *ELDERLY_COLS],
}


def api_var_to_sf_col(var: str) -> str:
    """Map API variable name (B19013_001E) -> Summary File column (B19013_E001)."""
    return var[:-1].replace("_", "_E")


# ---------------------------------------------------------------------------
# Step 1: TIGER/Line block-group geometry
# ---------------------------------------------------------------------------

def fetch_tiger_bg_zip(url: str = TIGER_BG_URL, timeout: int = 300) -> bytes:
    resp = http_get_with_retry(url, timeout=timeout)
    return resp.content


def extract_and_read_bg_shapefile(zip_bytes: bytes, extract_dir: Path) -> gpd.GeoDataFrame:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(extract_dir)
    shp_path = next(extract_dir.glob("*.shp"))
    return gpd.read_file(shp_path)


def build_block_groups() -> gpd.GeoDataFrame:
    """Fetch TIGER WA block groups, keep King County, write GeoJSON."""
    print("[1/2] Fetching TIGER/Line 2023 block groups for Washington ...")
    gdf = extract_and_read_bg_shapefile(fetch_tiger_bg_zip(), TIGER_EXTRACT_DIR)
    print(f"    read {len(gdf)} block-group features for WA")
    king = gdf[gdf["COUNTYFP"] == COUNTY_FIPS].copy()
    if king.empty:
        raise RuntimeError("No King County block groups found in TIGER dataset")
    king = king.to_crs(epsg=4326)
    king["geoid"] = king["GEOID"].astype(str).str.zfill(12)
    cols = ["geoid", "GEOID", "STATEFP", "COUNTYFP", "TRACTCE", "BLKGRPCE", "geometry"]
    king = king[cols]
    PREPARED_DIR.mkdir(parents=True, exist_ok=True)
    king.to_file(BG_GEOJSON_PATH, driver="GeoJSON")
    print(f"    wrote {BG_GEOJSON_PATH} — {len(king)} King County block groups")
    return king


# ---------------------------------------------------------------------------
# Step 2a: ACS via Census Data API
# ---------------------------------------------------------------------------

def fetch_acs_api(api_key: str | None = None, timeout: int = 300) -> pd.DataFrame:
    params = {
        "get": ",".join(ACS_VARIABLES),
        "for": "block group:*",
        "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS}",
    }
    if api_key:
        params["key"] = api_key
    resp = http_get_with_retry(ACS_API_URL, params=params, timeout=timeout)
    try:
        payload = resp.json()
    except ValueError as exc:
        raise RuntimeError(
            "Census API did not return JSON (it likely requires an API key); "
            f"status={resp.status_code}"
        ) from exc
    header, *rows = payload
    df = pd.DataFrame(rows, columns=header)
    df["geoid"] = (
        df["state"]
        + df["county"]
        + df["tract"].str.zfill(6)
        + df["block group"].str.zfill(1)
    )
    df = df[["geoid"] + ACS_VARIABLES]
    return df


# ---------------------------------------------------------------------------
# Step 2b: ACS via Census table-based Summary File (bulk, no key)
# ---------------------------------------------------------------------------

def _stream_download(url: str, dest: Path, timeout: int = 900) -> None:
    with http_get_with_retry(url, stream=True, timeout=timeout) as resp:
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 512):
                fh.write(chunk)


def _read_filtered_sf_table(dat_path: Path, api_cols: list[str]) -> pd.DataFrame:
    """Read one .dat table, keep only King County block-group rows."""
    keep_cols = {api_var_to_sf_col(c) for c in api_cols} | {"GEO_ID"}
    frames = []
    for chunk in pd.read_csv(
        dat_path,
        sep="|",
        dtype=str,
        chunksize=200_000,
        usecols=lambda c: c in keep_cols,
    ):
        sub = chunk[chunk["GEO_ID"].str.startswith(BG_KING_PREFIX, na=False)]
        if not sub.empty:
            frames.append(sub)
    if not frames:
        return pd.DataFrame(columns=sorted(keep_cols))
    return pd.concat(frames, ignore_index=True)


def fetch_acs_sf(work_dir: Path) -> pd.DataFrame:
    """Download and parse the 5 needed ACS tables -> geoid-keyed raw frame."""
    work_dir.mkdir(parents=True, exist_ok=True)
    print("[2/2] Census API unavailable; falling back to official Census")
    print("       table-based ACS 5-year Summary File (bulk .dat tables, no key)")
    merged: pd.DataFrame | None = None
    for table, api_cols in SF_TABLES.items():
        fname = f"acsdt5y2022-{table.lower()}.dat"
        url = f"{ACS_SF_BASE}/{fname}"
        dest = work_dir / fname
        print(f"    downloading {url}")
        _stream_download(url, dest)
        print(f"    parsing {fname} ...")
        t = _read_filtered_sf_table(dest, api_cols)
        print(f"      {len(t)} King County block-group rows kept")
        t = t.rename(columns={api_var_to_sf_col(c): c for c in api_cols})
        geoid = t.pop("GEO_ID").str.replace(BG_GEOID_PREFIX, "", regex=False)
        t.insert(0, "geoid", geoid)
        merged = t if merged is None else merged.merge(t, on="geoid", how="outer")
        dest.unlink(missing_ok=True)  # don't keep GB-scale intermediates
    if merged is None:
        raise RuntimeError("No ACS Summary File data could be read")
    cols = ["geoid"] + [c for c in merged.columns if c != "geoid"]
    return merged[cols].copy()


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------

def safe_pct(num: pd.Series, den: pd.Series) -> pd.Series:
    """num/den as a share, NaN-safe.

    - Genuinely missing numerators/denominators (unparseable or absent) stay NaN.
    - A zero universe (den == 0) yields 0.0 by definition.
    """
    num = pd.to_numeric(num, errors="coerce")
    den = pd.to_numeric(den, errors="coerce")
    out = num.div(den.where(den != 0))
    return out.mask(den.eq(0), 0.0)


def _to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _normalize_api_frame(acs: pd.DataFrame) -> pd.DataFrame:
    """Map raw API frame -> canonical internal columns."""
    f = pd.DataFrame({"geoid": acs["geoid"].astype(str)})
    f["median_income"] = _to_num(acs["B19013_001E"])
    f["pov_universe"] = _to_num(acs["B17001_001E"])
    f["pov_below"] = _to_num(acs["B17001_002E"])
    f["hh_total"] = _to_num(acs["B08201_001E"])
    f["hh_nocar"] = _to_num(acs["B08201_002E"])
    f["race_total"] = _to_num(acs["B03002_001E"])
    f["race_nhwhite"] = _to_num(acs["B03002_003E"])
    f["pop_total"] = _to_num(acs["B01001_001E"])
    f["elderly_sum"] = sum(_to_num(acs[c]) for c in ELDERLY_COLS)
    return f


def _normalize_sf_frame(acs: pd.DataFrame) -> pd.DataFrame:
    """Map raw Summary File frame -> canonical internal columns.

    Uses block-group-level table equivalents B17021 (poverty) and B25044
    (vehicle availability) because B17001 / B08201 are not published at the
    block-group level in the table-based Summary File.
    """
    f = pd.DataFrame({"geoid": acs["geoid"].astype(str)})
    f["median_income"] = _to_num(acs["B19013_001E"])
    f["pov_universe"] = _to_num(acs["B17021_001E"])
    f["pov_below"] = _to_num(acs["B17021_002E"])
    f["hh_total"] = _to_num(acs["B25044_001E"])
    f["hh_nocar"] = _to_num(acs["B25044_003E"]) + _to_num(acs["B25044_010E"])
    f["race_total"] = _to_num(acs["B03002_001E"])
    f["race_nhwhite"] = _to_num(acs["B03002_003E"])
    f["pop_total"] = _to_num(acs["B01001_001E"])
    f["elderly_sum"] = sum(_to_num(acs[c]) for c in ELDERLY_COLS)
    return f


def derive_acs_features(norm: pd.DataFrame) -> pd.DataFrame:
    out = norm[["geoid"]].copy()
    out["median_income"] = norm["median_income"]
    out["poverty_pct"] = safe_pct(norm["pov_below"], norm["pov_universe"])
    out["zero_car_pct"] = safe_pct(norm["hh_nocar"], norm["hh_total"])
    minority_num = norm["race_total"] - norm["race_nhwhite"]
    out["minority_pct"] = safe_pct(minority_num, norm["race_total"])
    out["elderly_pct"] = safe_pct(norm["elderly_sum"], norm["pop_total"])
    out["pop_total"] = norm["pop_total"]
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    build_block_groups()

    api_key = os.environ.get("CENSUS_API_KEY")
    acs: pd.DataFrame
    source_desc: str
    normalize = _normalize_api_frame

    if api_key:
        print(f"[2/2] Fetching ACS via Census API (key: {api_key[:4]}...{api_key[-2:]})")
        try:
            acs = fetch_acs_api(api_key)
            source_desc = "Census Data API (keyed)"
        except Exception as exc:  # noqa: BLE001
            print(f"    API call failed ({exc}); falling back to Summary File")
            acs = fetch_acs_sf(Path(tempfile.gettempdir()) / "opencode" / "census_sf_tmp")
            normalize = _normalize_sf_frame
            source_desc = "Census table-based ACS Summary File (bulk, no key)"
    else:
        print("[2/2] Fetching ACS via Census API (unauthenticated attempt) ...")
        try:
            acs = fetch_acs_api(None)
            source_desc = "Census Data API (unauthenticated)"
        except Exception as exc:  # noqa: BLE001
            print(f"    unauthenticated API failed ({exc})")
            print("    -> set CENSUS_API_KEY to use the API, OR keep using the")
            print("       official bulk Summary File fallback (real data, no key).")
            acs = fetch_acs_sf(Path(tempfile.gettempdir()) / "opencode" / "census_sf_tmp")
            normalize = _normalize_sf_frame
            source_desc = "Census table-based ACS Summary File (bulk, no key)"

    features = derive_acs_features(normalize(acs))
    PREPARED_DIR.mkdir(parents=True, exist_ok=True)
    features.to_parquet(ACS_PARQUET_PATH, index=False)

    pop_total = features["pop_total"].sum()
    joined_pct = 100.0 * (
        features["pop_total"].notna().sum() / len(features)
    ) if len(features) else 0.0
    print(f"    wrote {ACS_PARQUET_PATH} — {len(features)} block groups, "
          f"pop_total sum = {pop_total:,.0f} (~{joined_pct:.1f}% rows with pop)")
    print(f"    source: {source_desc}")
    print(f"    scope : King County, WA (FIPS {STATE_FIPS}{COUNTY_FIPS}); "
          f"plausible pop ref {KING_COUNTY_POP_REF:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
