"""Download real GTFS static feeds for King County Metro and Sound Transit.

Saves the zips to ``data/raw/gtfs/``:

- ``kc_metro_gtfs.zip``   — King County Metro (bus) static GTFS
- ``sound_transit_gtfs.zip`` — Sound Transit (rail / Link, ST Express) static GTFS

Source URLs (official, free, no API key):

- King County Metro is published at http://metro.kingcounty.gov/GTFS/google_transit.zip
  (host ``metro.kingcounty.gov`` was not reachable from the sandbox at build
  time, so we default to the official mirror Sound Transit hosts on its own
  domain: https://www.soundtransit.org/GTFS-KCM/google_transit.zip).
- Sound Transit's static feed is published at
  https://www.soundtransit.org/GTFS-rail/40_gtfs.zip (the legacy
  /sites/default/files/GTFS/sound_transit.zip URL now returns 404).

Both URLs can be overridden with the env vars ``KC_GTFS_URL`` and
``ST_GTFS_URL``.
"""

import io
import os
import sys
import zipfile
from pathlib import Path

import requests

DEFAULT_URLS = {
    "kc": "https://www.soundtransit.org/GTFS-KCM/google_transit.zip",
    "st": "https://www.soundtransit.org/GTFS-rail/40_gtfs.zip",
}
ENV_VARS = {
    "kc": "KC_GTFS_URL",
    "st": "ST_GTFS_URL",
}
OUT_FILES = {
    "kc": "kc_metro_gtfs.zip",
    "st": "sound_transit_gtfs.zip",
}
REQUIRED_MEMBERS = ("stops.txt", "routes.txt")

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "gtfs"


def download_gtfs(name: str, url: str, out_path: Path) -> tuple[int, int]:
    """Download ``url``, validate it is a GTFS zip, and save to ``out_path``.

    Returns ``(bytes_written, n_files_in_zip)``.
    """
    try:
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to download GTFS feed '{name}' from {url}: {exc}") from exc

    try:
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = set(zf.namelist())
            bad = zf.testzip()
            if bad is not None:
                raise ValueError(f"corrupt member in zip: {bad}")
    except zipfile.BadZipFile as exc:
        raise ValueError(
            f"Downloaded file for '{name}' is not a valid zip (status "
            f"{resp.status_code}, {len(resp.content)} bytes from {url})"
        ) from exc

    missing = [m for m in REQUIRED_MEMBERS if m not in names]
    if missing:
        raise ValueError(
            f"GTFS feed '{name}' from {url} is missing required files: {missing}"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(resp.content)
    return len(resp.content), len(names)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("kc", "st"):
        url = os.environ.get(ENV_VARS[name], DEFAULT_URLS[name])
        out_path = RAW_DIR / OUT_FILES[name]
        size, n_files = download_gtfs(name, url, out_path)
        print(
            f"{name}: {out_path.name} — {size / 1e6:.1f} MB, "
            f"{n_files} files (source: {url})"
        )


if __name__ == "__main__":
    sys.exit(main())
