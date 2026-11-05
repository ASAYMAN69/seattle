"""Parse GTFS static zips into tidy per-agency frames and write merged parquet.

Reads the raw CSV members of a GTFS zip with pandas (no date-window
filtering), keeps only the columns the rest of the project needs, adds a
``source`` column ("kc" | "st"), and writes four merged parquet files to
``data/prepared/gtfs/``:

- ``stops.parquet``     — stop_id, stop_name, stop_lat, stop_lon, source
- ``routes.parquet``    — route_id, route_short_name, route_long_name,
                           route_type, agency_id, source
- ``stop_times.parquet`` — trip_id, stop_id, stop_sequence, arrival_time,
                           departure_time, source
- ``calendar.parquet``  — service_id, monday..sunday, start_date, end_date,
                           source

Public API: ``parse_gtfs(zip_path: Path, source: str) -> dict[str, pd.DataFrame]``
"""

import sys
import zipfile
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "stops": ["stop_id", "stop_name", "stop_lat", "stop_lon"],
    "routes": [
        "route_id",
        "route_short_name",
        "route_long_name",
        "route_type",
        "agency_id",
    ],
    "stop_times": [
        "trip_id",
        "stop_id",
        "stop_sequence",
        "arrival_time",
        "departure_time",
    ],
    "calendar": [
        "service_id",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "start_date",
        "end_date",
    ],
}

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "gtfs"
PREPARED_DIR = Path(__file__).resolve().parents[1] / "data" / "prepared" / "gtfs"

ZIP_TO_SOURCE = {
    "kc_metro_gtfs.zip": "kc",
    "sound_transit_gtfs.zip": "st",
}


def _read_member(zip_path: Path, member: str) -> pd.DataFrame:
    """Read one CSV member of a GTFS zip into a DataFrame."""
    with zipfile.ZipFile(zip_path) as zf:
        if member not in zf.namelist():
            raise FileNotFoundError(f"{member} not found in {zip_path.name}")
        with zf.open(member) as fh:
            return pd.read_csv(fh)


STRING_COLUMNS = [
    "stop_id",
    "stop_name",
    "route_id",
    "route_short_name",
    "route_long_name",
    "agency_id",
    "trip_id",
    "arrival_time",
    "departure_time",
    "service_id",
    "start_date",
    "end_date",
]


def _coerce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Small dtype normalization for the columns we keep."""
    out = df.copy()
    for col in STRING_COLUMNS:
        if col in out.columns:
            out[col] = out[col].astype("string")
    if "stop_lat" in out.columns:
        out["stop_lat"] = pd.to_numeric(out["stop_lat"], errors="coerce")
    if "stop_lon" in out.columns:
        out["stop_lon"] = pd.to_numeric(out["stop_lon"], errors="coerce")
    if "stop_sequence" in out.columns:
        out["stop_sequence"] = (
            pd.to_numeric(out["stop_sequence"], errors="coerce")
            .astype("Int64")
        )
    if "route_type" in out.columns:
        out["route_type"] = (
            pd.to_numeric(out["route_type"], errors="coerce").astype("Int64")
        )
    day_cols = [
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
    ]
    for col in day_cols:
        if col in out.columns:
            out[col] = (
                pd.to_numeric(out[col], errors="coerce").astype("Int64")
            )
    return out


def parse_gtfs(zip_path: Path, source: str) -> dict[str, pd.DataFrame]:
    """Parse one GTFS zip into the four required frames.

    Each frame contains only the project's required columns plus a
    ``source`` column set to ``source``.
    """
    if not Path(zip_path).exists():
        raise FileNotFoundError(f"GTFS zip not found: {zip_path}")

    # Route table column order differs between feeds (agency_id first vs later);
    # select by name so order never matters.
    route_cols = REQUIRED_COLUMNS["routes"]
    routes = _read_member(zip_path, "routes.txt")
    missing_route = [c for c in route_cols if c not in routes.columns]
    if missing_route:
        raise ValueError(
            f"routes.txt missing columns {missing_route} in {Path(zip_path).name}"
        )
    routes = routes[route_cols]

    stops = _read_member(zip_path, "stops.txt")
    stop_cols = REQUIRED_COLUMNS["stops"]
    missing_stop = [c for c in stop_cols if c not in stops.columns]
    if missing_stop:
        raise ValueError(
            f"stops.txt missing columns {missing_stop} in {Path(zip_path).name}"
        )
    stops = stops[stop_cols]

    stop_times = _read_member(zip_path, "stop_times.txt")
    st_cols = REQUIRED_COLUMNS["stop_times"]
    missing_st = [c for c in st_cols if c not in stop_times.columns]
    if missing_st:
        raise ValueError(
            f"stop_times.txt missing columns {missing_st} in {Path(zip_path).name}"
        )
    stop_times = stop_times[st_cols]

    calendar = _read_member(zip_path, "calendar.txt")
    cal_cols = REQUIRED_COLUMNS["calendar"]
    missing_cal = [c for c in cal_cols if c not in calendar.columns]
    if missing_cal:
        raise ValueError(
            f"calendar.txt missing columns {missing_cal} in {Path(zip_path).name}"
        )
    calendar = calendar[cal_cols]

    frames = {
        "stops": _coerce_dtypes(stops),
        "routes": _coerce_dtypes(routes),
        "stop_times": _coerce_dtypes(stop_times),
        "calendar": _coerce_dtypes(calendar),
    }
    for frame in frames.values():
        frame["source"] = source

    return frames


def main() -> None:
    PREPARED_DIR.mkdir(parents=True, exist_ok=True)

    all_frames: dict[str, list[pd.DataFrame]] = {
        key: [] for key in REQUIRED_COLUMNS
    }
    for zip_name, source in ZIP_TO_SOURCE.items():
        zip_path = RAW_DIR / zip_name
        if not zip_path.exists():
            raise FileNotFoundError(
                f"{zip_path} missing — run scripts/fetch_gtfs.py first"
            )
        frames = parse_gtfs(zip_path, source)
        for key, frame in frames.items():
            all_frames[key].append(frame)
        print(
            f"{source}: stops={len(frames['stops']):,} "
            f"routes={len(frames['routes']):,} "
            f"stop_times={len(frames['stop_times']):,} "
            f"calendar={len(frames['calendar']):,}"
        )

    for key, parts in all_frames.items():
        merged = pd.concat(parts, ignore_index=True)
        out_path = PREPARED_DIR / f"{key}.parquet"
        merged.to_parquet(out_path, index=False)
        print(f"{key}: {len(merged):,} rows -> {out_path}")


if __name__ == "__main__":
    sys.exit(main())
