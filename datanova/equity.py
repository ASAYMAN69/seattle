"""Equity scoring and report-card grades (Task 2.4, Seattle Transit Equity Index).

Combines per-block-group accessibility (Task 2.2) with the composite need
index (Task 2.3) into a single *equity gap* score and letter grades:

* ``access_overall`` — weighted mean of the four category access scores
  (jobs 0.40, healthcare 0.25, schools 0.15, food 0.20). The mean is NaN-safe:
  categories with a missing (NaN) access score are dropped and the remaining
  weights are renormalized so the score stays in [0, 1].
* ``gap`` = ``access_overall`` - ``need_index`` ∈ [-1, 1]; negative means
  need outstrips access (underserved), positive means access exceeds need.
* ``grade`` — letter A–F from fixed bands on ``gap`` (documented in
  :func:`grade_bands`); the same bands are applied per dimension using
  ``category_access - need_index`` to produce per-dimension grades.

Coordinate/interface conventions follow the earlier tasks: all ``geoid``
values are strings; ``access`` comes from ``datanova.accessibility.compute_access_scores``
and ``need`` from ``datanova.need.compute_need_index``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Weight of each opportunity category in the overall access score (sums to 1).
ACCESS_WEIGHTS: dict[str, float] = {
    "jobs": 0.40,
    "healthcare": 0.25,
    "schools": 0.15,
    "food": 0.20,
}

CATEGORY_ORDER = tuple(ACCESS_WEIGHTS.keys())

# Fixed letter-grade bands on the equity gap. Lower bound inclusive, upper
# bound exclusive (the top band is open-ended). Reused by the app through
# ``grade_bands()``.
GRADE_BANDS: dict[str, tuple[float, float]] = {
    "A": (0.25, float("inf")),
    "B": (0.10, 0.25),
    "C": (-0.05, 0.10),
    "D": (-0.20, -0.05),
    "F": (float("-inf"), -0.20),
}

GRADES = ("A", "B", "C", "D", "F")

# Output columns of compute_equity (schema contract).
ACCESS_COLS = tuple(f"{c}_access" for c in CATEGORY_ORDER)
PER_DIMENSION_GRADE_COLS = tuple(f"{c}_grade" for c in CATEGORY_ORDER)
EQUITY_OUTPUT_COLS = (
    ("geoid",) + ACCESS_COLS + ("access_overall", "need_index", "gap", "grade")
    + PER_DIMENSION_GRADE_COLS
)

# Column in the ``access`` input frame that carries the geoid.
GEOID_COL = "geoid"


def grade_bands() -> dict[str, tuple[float, float]]:
    """The fixed grade bands as ``{grade: (lower_inclusive, upper_exclusive)}``.

    ``upper`` is ``+inf`` for "A" and ``lower`` is ``-inf`` for "F". The
    bands are closed on the lower end and open on the upper end.
    """
    return {g: (lo, hi) for g, (lo, hi) in GRADE_BANDS.items()}


def grade_for_gap(gap: float) -> str:
    """Map a single gap value to a letter grade using the fixed bands."""
    if gap >= 0.25:
        return "A"
    if gap >= 0.10:
        return "B"
    if gap >= -0.05:
        return "C"
    if gap >= -0.20:
        return "D"
    return "F"


def _grade_series(gap: pd.Series) -> pd.Series:
    """Vectorized A–F grading of a gap Series (NaN in -> NaN out)."""
    out = pd.Series(np.nan, index=gap.index, dtype=object)
    valid = gap.notna()
    vals = gap[valid].to_numpy(dtype=float)
    labels = np.select(
        [
            vals >= 0.25,
            vals >= 0.10,
            vals >= -0.05,
            vals >= -0.20,
        ],
        ["A", "B", "C", "D"],
        default="F",
    )
    out.loc[valid] = labels
    return out


def _access_overall(access: pd.DataFrame) -> pd.Series:
    """NaN-safe weighted mean of category access scores (renormalized)."""
    w = np.array([ACCESS_WEIGHTS[c] for c in CATEGORY_ORDER], dtype=float)
    vals = access[list(ACCESS_COLS)].to_numpy(dtype=float)
    mask = np.isfinite(vals)
    ww = np.broadcast_to(w, vals.shape).copy()
    ww[~mask] = 0.0
    wsum = ww.sum(axis=1)
    # NaN * 0 is still NaN, so zero-out missing entries before multiplying.
    safe = np.where(mask, vals, 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        overall = (safe * ww).sum(axis=1) / wsum
    overall = np.where(wsum > 0, overall, np.nan)
    return pd.Series(overall, index=access.index)


def compute_equity(
    access: pd.DataFrame,
    need: pd.DataFrame,
) -> pd.DataFrame:
    """Combine accessibility and need into equity scores, gaps and grades.

    Parameters
    ----------
    access:
        ``compute_access_scores`` output: ``geoid`` + one score per category
        (``jobs_access``, ``healthcare_access``, ``schools_access``,
        ``food_access``), each in [0, 1] or NaN.
    need:
        ``compute_need_index`` output: ``geoid`` + ``need_index`` in
        [0, 1] or NaN.

    Returns
    -------
    pd.DataFrame
        One row per block group (``access`` row order) with columns:
        ``geoid, jobs_access, healthcare_access, schools_access, food_access,
        access_overall, need_index, gap, grade, jobs_grade, healthcare_grade,
        schools_grade, food_grade``.

        * ``access_overall`` — NaN-safe weighted mean (weights renormalized
          over available categories; NaN when no category is available).
        * ``gap`` = ``access_overall - need_index`` (NaN when either input is
          NaN).
        * ``grade`` — A–F from the fixed bands on ``gap`` (NaN when ``gap``
          is NaN).
        * ``{category}_grade`` — same bands applied to ``category_access
          - need_index``.
    """
    if GEOID_COL not in access.columns or GEOID_COL not in need.columns:
        raise ValueError("access and need must both contain a 'geoid' column")
    for col in ACCESS_COLS:
        if col not in access.columns:
            raise ValueError(f"access missing expected column {col!r}")
    if "need_index" not in need.columns:
        raise ValueError("need must contain a 'need_index' column")

    out = access.copy()
    out[GEOID_COL] = out[GEOID_COL].astype(str)

    need_map = need[[GEOID_COL, "need_index"]].copy()
    need_map[GEOID_COL] = need_map[GEOID_COL].astype(str)
    need_map = need_map.drop_duplicates(subset=[GEOID_COL])

    out = out.merge(need_map, on=GEOID_COL, how="left")

    out["access_overall"] = _access_overall(out)
    with np.errstate(invalid="ignore"):
        out["gap"] = out["access_overall"] - out["need_index"]
    out["grade"] = _grade_series(out["gap"])

    for cat in CATEGORY_ORDER:
        dim_gap = out[f"{cat}_access"] - out["need_index"]
        out[f"{cat}_grade"] = _grade_series(dim_gap)

    return out[list(EQUITY_OUTPUT_COLS)].reset_index(drop=True)
