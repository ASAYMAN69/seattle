#!/usr/bin/env python3
"""Phase-2 analysis pipeline (Task 2.4, Seattle Transit Equity Index).

Orchestrates the full end-to-end run over the real prepared data:

    GTFS -> network -> accessibility -> need -> equity -> recommendations
    -> prepared outputs under data/prepared/equity/

Outputs
-------
- ``equity_scores.geojson``  — block groups + all scores/grades (EPSG:4326)
- ``equity_scores.parquet``  — same table (no geometry), for app convenience
- ``report_cards.json``       — per-geoid grades + summary stats
- ``recommendations.geojson`` — recommendation points/lines with attributes
- ``sensitivity.parquet``     — what-if (2x frequency) support per route

Run: ``.venv/bin/python scripts/run_analysis.py``
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datanova.accessibility import CATEGORY_ORDER, compute_access_scores  # noqa: E402
from datanova.equity import compute_equity  # noqa: E402
from datanova.need import compute_need_index  # noqa: E402
from datanova.network import build_network  # noqa: E402
from datanova.recommend import (  # noqa: E402
    _gain_per_bg,
    _load_calendar,
    _load_stop_times,
    _load_trips_map,
    _weekday_service_ids,
    recommend,
    recommendations_geodataframe,
)

GTFS_DIR = ROOT / "data" / "prepared" / "gtfs"
BG_PATH = ROOT / "data" / "prepared" / "census" / "block_groups.geojson"
ACS_PATH = ROOT / "data" / "prepared" / "census" / "acs_demographics.parquet"
OPP_DIR = ROOT / "data" / "prepared" / "opportunities"
OUT_DIR = ROOT / "data" / "prepared" / "equity"


def _minutes() -> float:
    return time.time()


def _clean(value):
    """JSON-safe scalar: NaN/inf -> None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (np.floating, float)) and not np.isfinite(value):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value)
    return value


def _finite_mean(s: pd.Series) -> float | None:
    v = pd.to_numeric(s, errors="coerce").dropna()
    return float(v.mean()) if len(v) else None


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t_total = _minutes()

    # -- 1/7 network -----------------------------------------------------
    print("[1/7] building transit network ...")
    t = _minutes()
    net = build_network(GTFS_DIR)
    print(f"        network built in {_minutes() - t:.1f}s "
          f"({len(net.stops):,} stops, {len(net.edges):,} edges)")

    # -- 2/7 inputs ------------------------------------------------------
    print("[2/7] loading census + opportunities ...")
    bg = gpd.read_file(BG_PATH)
    opps = {c: gpd.read_file(OPP_DIR / f"{c}.geojson") for c in CATEGORY_ORDER}
    print(f"        {len(bg):,} block groups; "
          + ", ".join(f"{c}={len(opps[c]):,}" for c in CATEGORY_ORDER))

    # -- 3/7 accessibility ------------------------------------------------
    print("[3/7] computing accessibility scores ...")
    t = _minutes()
    access = compute_access_scores(bg, opps, net)
    print(f"        accessibility computed in {_minutes() - t:.1f}s")

    # -- 4/7 need ---------------------------------------------------------
    print("[4/7] computing need index ...")
    acs = pd.read_parquet(ACS_PATH)
    need = compute_need_index(acs)
    print(f"        need index computed for {len(need):,} block groups")

    # -- 5/7 equity -------------------------------------------------------
    print("[5/7] computing equity scores + grades ...")
    equity = compute_equity(access, need)
    pop_map = acs[["geoid", "pop_total"]].copy()
    pop_map["geoid"] = pop_map["geoid"].astype(str)
    equity = equity.merge(pop_map, on="geoid", how="left")
    equity = equity.merge(bg[["geoid", "geometry"]], on="geoid", how="left")
    equity["geoid"] = equity["geoid"].astype(str)

    # -- 6/7 recommendations ----------------------------------------------
    print("[6/7] generating recommendations ...")
    t = _minutes()
    recs = recommend(equity, bg, net, GTFS_DIR)
    print(f"        recommendations generated in {_minutes() - t:.1f}s "
          f"({len(recs)} corridors)")

    # -- 7/7 outputs ------------------------------------------------------
    print("[7/7] writing prepared outputs ...")

    # equity scores (GeoJSON + parquet convenience copy)
    eq_out = bg.copy()
    eq_out["geoid"] = eq_out["geoid"].astype(str)
    eq_out = eq_out.merge(equity.drop(columns=["geometry"]), on="geoid", how="left")
    eq_out.to_file(OUT_DIR / "equity_scores.geojson", driver="GeoJSON")
    eq_out.drop(columns=["geometry"]).to_parquet(
        OUT_DIR / "equity_scores.parquet", index=False
    )

    # report cards
    grade_counts = (
        equity["grade"].dropna().astype(str).value_counts().sort_index().to_dict()
    )
    cards = {}
    for _, row in equity.iterrows():
        cards[row["geoid"]] = {
            col: _clean(row[col])
            for col in equity.columns
            if col not in ("geometry",)
        }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": {
            "n_block_groups": int(len(equity)),
            "n_with_grade": int(equity["grade"].notna().sum()),
            "grade_counts": grade_counts,
            "mean_access_overall": _finite_mean(equity["access_overall"]),
            "mean_need": _finite_mean(equity["need_index"]),
            "mean_gap": _finite_mean(equity["gap"]),
            "median_gap": _finite_mean(equity["gap"]),
            "n_recommendations": len(recs),
            "total_recommended_population": int(
                sum(r["affected_pop"] for r in recs)
            ),
        },
        "report_cards": cards,
    }
    with open(OUT_DIR / "report_cards.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    # recommendations (lines for routes, points for coverage gaps)
    stop_times = _load_stop_times(GTFS_DIR)
    trips_map = _load_trips_map(GTFS_DIR)
    wd = _weekday_service_ids(_load_calendar(GTFS_DIR))
    rec_gdf = recommendations_geodataframe(
        recs,
        net,
        equity=equity,
        stop_times=stop_times,
        trips_map=trips_map,
        weekday_service_ids=wd,
    )
    rec_gdf.to_file(OUT_DIR / "recommendations.geojson", driver="GeoJSON")

    # sensitivity (what-if: 2x frequency)
    sens_rows = []
    for r in recs:
        gains = _gain_per_bg(r, equity)
        est_mean = float(np.mean(list(gains.values()))) if gains else 0.0
        sub = equity[
            equity["geoid"].astype(str).isin(set(r["geoids"]))
        ]
        w = sub["pop_total"].fillna(0.0).to_numpy(dtype=float)
        vals = np.array(
            [gains.get(str(gid), 0.0) for gid in sub["geoid"].astype(str)],
            dtype=float,
        )
        est_popweighted = (
            float(np.average(vals, weights=w)) if w.sum() > 0 else est_mean
        )
        sens_rows.append(
            {
                "route_id": r["route_id"],
                "corridor": r["corridor"],
                "action": r["action"],
                "affected_pop": r["affected_pop"],
                "n_block_groups": r["n_block_groups"],
                "geoids": r["geoids"],
                "am_peak_trips": r["am_peak_trips"],
                "headway_min_current": r["headway_min_current"],
                "wait_saving_min": r["wait_saving_min"],
                "est_access_gain_mean": est_mean,
                "est_access_gain_popweighted": est_popweighted,
            }
        )
    sens = pd.DataFrame(sens_rows)
    sens.to_parquet(OUT_DIR / "sensitivity.parquet", index=False)

    # -- summary ----------------------------------------------------------
    elapsed = _minutes() - t_total
    print()
    print("=" * 72)
    print("SEATTLE TRANSIT EQUITY INDEX — PHASE 2 ANALYSIS SUMMARY")
    print("=" * 72)
    print(f"block groups                     : {len(equity):,}")
    print(f"block groups with a grade        : {report['summary']['n_with_grade']:,}")
    print(f"grade distribution               : {json.dumps(grade_counts)}")
    print(f"mean access_overall             : {report['summary']['mean_access_overall']:.4f}")
    print(f"mean need_index                  : {report['summary']['mean_need']:.4f}")
    print(f"mean gap (access - need)         : {report['summary']['mean_gap']:.4f}")
    print(f"recommendations                  : {len(recs)}")
    print(f"total recommended population      : {report['summary']['total_recommended_population']:,}")
    print(f"total pipeline runtime            : {elapsed:.1f}s")
    print()
    print("top 10 recommendations by affected population:")
    for i, r in enumerate(recs[:10], start=1):
        print(
            f"  {i:2d}. {r['corridor']:<28} pop={r['affected_pop']:>7,}  "
            f"bgs={r['n_block_groups']:>4}  "
            f"headway={r['headway_min_current'] if r['headway_min_current'] is not None else float('nan'):5.1f}min  "
            f"{r['action']}"
        )
    print("-" * 72)
    print("outputs:")
    for name in (
        "equity_scores.geojson",
        "equity_scores.parquet",
        "report_cards.json",
        "recommendations.geojson",
        "sensitivity.parquet",
    ):
        p = OUT_DIR / name
        print(f"  {p.relative_to(ROOT)}  ({p.stat().st_size / 1024:.0f} KiB)")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
