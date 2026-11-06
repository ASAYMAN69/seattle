#!/usr/bin/env python3
"""Generate dev-only JSON mocks from the real prepared parquet files.

Writes (only if missing, or when --force is passed):
  web/dev-mock/sensitivity.json        — sensitivity.parquet rows
  web/dev-mock/acs-demographics.json    — acs_demographics.parquet rows

The values are the real prepared data (nothing fabricated). These mocks feed
the dev-only API server (scripts/dev-api.mjs). They are gitignored.

Requires pandas + pyarrow (parquet engine). Example:
    python3 -m venv --system-site-packages /tmp/dn-venv
    /tmp/dn-venv/bin/pip install pyarrow
    /tmp/dn-venv/bin/python scripts/gen-dev-mock.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREPARED = ROOT / "data" / "prepared"
OUT = Path(__file__).resolve().parents[1] / "dev-mock"

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    sys.exit("pandas is required (pip install pandas)")

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


def clean(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if np is not None and isinstance(value, np.ndarray):
        return [clean(v) for v in value.tolist()]
    if np is not None and isinstance(value, (np.integer, np.floating)):
        value = value.item()
    if isinstance(value, (int, float)) and value == -666_666_666:
        return None
    return value


def frame_to_records(frame):
    rows = []
    for _, row in frame.iterrows():
        rec = {}
        for col in frame.columns:
            v = clean(row[col])
            if isinstance(v, list):
                v = [clean(x) for x in v]
            rec[str(col)] = v
        rows.append(rec)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    sens_path = PREPARED / "equity" / "sensitivity.parquet"
    acs_path = PREPARED / "census" / "acs_demographics.parquet"

    if not sens_path.exists() or not acs_path.exists():
        sys.exit(
            "Prepared parquet files not found. Run the analysis pipeline first "
            "(scripts/run_analysis.py)."
        )

    sens = pd.read_parquet(sens_path)
    acs = pd.read_parquet(acs_path)

    for name, frame in (("sensitivity.json", sens), ("acs-demographics.json", acs)):
        dest = OUT / name
        if dest.exists() and "--force" not in sys.argv:
            print(f"skip (exists): {dest}")
            continue
        dest.write_text(json.dumps(frame_to_records(frame), indent=2), encoding="utf-8")
        print(f"wrote: {dest} ({len(frame)} rows)")

    print("Mock generation complete. Now run `npm run dev` (with the API proxy "
          "pointing at http://localhost:8000).")


if __name__ == "__main__":
    main()
