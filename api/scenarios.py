"""Time-of-day scenario helpers for the Seattle Transit Equity Index API.

Two scenarios are supported:

- ``am_peak`` (default): the real, prepared weekday AM-peak equity numbers.
- ``off_peak``: an **approximation** — the AM-peak numbers adjusted by an
  off-peak frequency factor. It is NOT a fresh routed network; the feeds lack
  ``trips.txt`` and the analysis assumes weekday AM peak. This module documents
  the approximation precisely so the frontend can label it honestly.

Adjustment model (transparent, no routing, no new data):

- Off-peak frequency multiplier ``m = 0.5`` (half of AM-peak frequency).
- Headway ``H = 14.0`` min (implied by the documented 7-min static wait:
  wait = headway/2).
- Wait saving ``s(m) = clamp((H/2) * (1 - 1/m), -3.5, 3.5)`` minutes, which is
  the signed generalisation of ``min((headway/2)*(1-1/m), 3.5)`` from
  ``app/views/whatif.py`` (``wait_saving_min``). Reference at ``m = 2.0``:
  ``s_ref = 3.5`` min.
- Access ratio ``r = s(m) / s_ref`` (``-1.0`` for off-peak).
- Per block group, per category access ``a`` is adjusted:
  ``a' = clamp(a + r * SCALE * (1 - a), 0, 1)`` with ``SCALE = 0.5``.
  This is proportional to the category access gap ``(1 - a)`` and reduces to the
  identity (no change) when ``r = 0`` (i.e. ``m = 1.0``, AM peak).
- ``access_overall'`` is recomputed as the mean of the four adjusted category
  accesses; ``gap' = access_overall' - need_index`` (need is unchanged).
- Grades and need_index are NOT recomputed (documented limitation).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Documented off-peak parameters
# ---------------------------------------------------------------------------

OFF_PEAK_MULTIPLIER: float = 0.5
REFERENCE_MULTIPLIER: float = 2.0
HEADWAY_MIN: float = 14.0
MAX_WAIT_SAVING_MIN: float = 3.5
ACCESS_SCALE: float = 0.5

VALID_TIME_OF_DAY: tuple[str, ...] = ("am_peak", "off_peak")

AM_PEAK_NOTE = (
    "Equity scores, letter grades, and ACS statistics are from the prepared "
    "DataNova 2026 transit-equity analysis (weekday AM peak). The equity gap = "
    "access − need (positive = better served). No live routing or API keys."
)

OFF_PEAK_NOTE = (
    "OFF-PEAK APPROXIMATION (not a fresh routed network): AM-peak equity "
    "numbers adjusted by an off-peak frequency factor (m=0.5x peak frequency, "
    "headway 14 min, wait saving -3.5 min). Category access values are "
    "interpolated proportionally to (1 - access) gaps at scale 0.5; "
    "access_overall is recomputed as their mean; gap = access_overall - need. "
    "Grades and need_index are NOT recomputed. Feeds lack trips.txt; the "
    "analysis assumes weekday AM peak."
)

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "am_peak",
        "label": "Weekday AM peak (real)",
        "is_full_compute": True,
        "basis": (
            "Prepared AM-peak equity analysis (GTFS weekday; frequency is the "
            "median over the full schedule, treated as AM-peak service)."
        ),
        "approximations": [],
        "limitations": [
            "AM-peak frequency approximates all service patterns (no trips.txt "
            "weekday filter).",
        ],
        "narrative": (
            "Real, precomputed equity scores for weekday AM-peak service."
        ),
    },
    {
        "id": "off_peak",
        "label": "Off-peak (approximate what-if)",
        "is_full_compute": False,
        "basis": (
            "AM-peak numbers adjusted by an off-peak frequency factor "
            "(m=0.5x peak frequency, headway 14 min)."
        ),
        "approximations": [
            "frequency multiplier m=0.5",
            "headway 14 min (implied by 7-min static wait)",
            "wait saving s(m)=clamp((H/2)*(1-1/m), -3.5, 3.5) = -3.5 min",
            "access gain proportional to (1 - access) gaps at scale 0.5",
            "access_overall recomputed as mean of adjusted category accesses",
            "no re-routing, no new data ingestion",
        ],
        "limitations": [
            "Not a fresh routed network; feeds lack trips.txt.",
            "Grades and need_index are not recomputed.",
            "Linear scaling is a documented, conservative ceiling.",
        ],
        "narrative": (
            "Approximate off-peak scenario: lower frequency reduces access, "
            "scaled by category access gaps. Labelled as an approximation."
        ),
    },
]


def scenario_descriptor(scenario_id: str) -> dict[str, Any]:
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return s
    raise ValueError(f"Unknown scenario: {scenario_id!r}")


def wait_saving_min(headway_min: float, multiplier: float) -> float:
    """Signed wait saving, clamped to [-MAX, MAX]."""
    if headway_min is None or (isinstance(headway_min, float) and np.isnan(headway_min)):
        return 0.0
    try:
        if pd.isna(headway_min):
            return 0.0
    except (TypeError, ValueError):
        pass
    m = float(multiplier)
    if m <= 0:
        return 0.0
    saving = (float(headway_min) / 2.0) * (1.0 - 1.0 / m)
    return float(max(-MAX_WAIT_SAVING_MIN, min(MAX_WAIT_SAVING_MIN, saving)))


def off_peak_ratio() -> float:
    s_off = wait_saving_min(HEADWAY_MIN, OFF_PEAK_MULTIPLIER)
    s_ref = wait_saving_min(HEADWAY_MIN, REFERENCE_MULTIPLIER)
    if s_ref == 0:
        return 0.0
    return float(s_off / s_ref)


def adjust_access(value: Any, ratio: float) -> float | None:
    """Adjust a single category access value."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if not np.isfinite(v):
        return None
    adjusted = v + ratio * ACCESS_SCALE * (1.0 - v)
    return float(max(0.0, min(1.0, adjusted)))


def is_off_peak(time_of_day: str) -> bool:
    return str(time_of_day).strip() == "off_peak"


def adjusted_equity_frame(prepared: dict[str, Any], time_of_day: str) -> pd.DataFrame:
    """Return equity_scores DataFrame, adjusted for off-peak if requested.

    For am_peak, returns the original (a copy). For off_peak, returns a copy with
    category access columns overwritten by adjusted values and access_overall
    recomputed.
    """
    equity = prepared["equity_scores"]
    df = equity.copy()
    if not is_off_peak(time_of_day):
        return df

    ratio = off_peak_ratio()
    for col in ("jobs_access", "healthcare_access", "schools_access", "food_access"):
        if col in df.columns:
            df[col] = df[col].map(lambda v: adjust_access(v, ratio))

    # Recompute access_overall as mean of adjusted category accesses.
    cat_cols = [c for c in ("jobs_access", "healthcare_access", "schools_access", "food_access") if c in df.columns]
    if cat_cols:
        df["access_overall"] = df[cat_cols].astype(float).mean(axis=1)

    # Recompute gap = access_overall - need_index.
    if "need_index" in df.columns and "access_overall" in df.columns:
        df["gap"] = df["access_overall"].astype(float) - df["need_index"].astype(float)

    return df


def equity_methodology_note(time_of_day: str) -> str:
    return OFF_PEAK_NOTE if is_off_peak(time_of_day) else AM_PEAK_NOTE


def validate_time_of_day(value: str) -> str:
    v = str(value).strip()
    if v not in VALID_TIME_OF_DAY:
        raise ValueError(
            f"Unknown time_of_day {value!r}; expected one of {list(VALID_TIME_OF_DAY)}."
        )
    return v
