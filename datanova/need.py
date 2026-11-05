"""Need Index for the Seattle Transit Equity Index (Task 2.3).

Combines five ACS block-group indicators into a single transit-need score in
[0, 1], where higher = more need for transit investment/services.
"""

from __future__ import annotations

import pandas as pd

# Indicators already expressed as shares in [0, 1]; higher = more need.
PCT_INDICATORS = (
    "poverty_pct",
    "zero_car_pct",
    "minority_pct",
    "elderly_pct",
)

INCOME_COL = "median_income"

# The ACS bulk Summary File encodes unreleased median household income as a
# large negative value (e.g. -666,666,666); non-positive incomes are not
# plausible and are treated as missing (component skipped).
INCOME_SUPPRESSED_MAX = 0


def compute_need_index(acs: pd.DataFrame) -> pd.DataFrame:
    """Compute the composite transit-need index per block group.

    Method
    ------
    1. Normalize each indicator to [0, 1] where higher = more transit need:
       - ``poverty_pct``, ``zero_car_pct``, ``minority_pct``, ``elderly_pct``
         are already shares in [0, 1]; they are used as-is after defensively
         clipping to [0, 1].
       - ``median_income`` is inverted and min-max scaled across all King
         County block groups: max income -> 0 need, min income -> 1 need.
         Non-finite and non-positive incomes (including the ACS suppression
         code -666,666,666 found in the prepared data) are treated as missing
         and *skip* this component.
    2. The need index for a block group is the mean of its available normalized
       indicators (missing components are skipped).
    3. If every indicator is missing for a block group, the need index is NaN.

    Output is deterministic and independent of input row order: the returned
    frame has exactly columns ``geoid`` and ``need_index`` and is sorted by
    ``geoid``.

    Parameters
    ----------
    acs : pd.DataFrame
        Must contain ``geoid`` and at least one indicator column.

    Returns
    -------
    pd.DataFrame
        ``geoid`` (str) and ``need_index`` (float in [0, 1] or NaN).
    """
    df = acs.copy()

    comps: dict[str, pd.Series] = {}
    for col in PCT_INDICATORS:
        if col in df.columns:
            comps[col] = df[col].clip(lower=0.0, upper=1.0)

    if INCOME_COL in df.columns:
        inc = pd.to_numeric(df[INCOME_COL], errors="coerce")
        valid = inc.where((inc > INCOME_SUPPRESSED_MAX) & inc.notna())
        lo = float(valid.min())
        hi = float(valid.max())
        if pd.isna(lo):
            # No usable income anywhere -> income component skipped everywhere.
            comps[INCOME_COL] = pd.Series(float("nan"), index=df.index)
        elif lo == hi:
            # Constant income carries no relative signal -> neutral for rows
            # with a usable income; still skipped for missing-income rows.
            neutral = pd.Series(0.5, index=df.index)
            comps[INCOME_COL] = neutral.where(valid.notna())
        else:
            norm = (valid - lo) / (hi - lo)  # 0 = lowest income, 1 = highest
            income_need = (1.0 - norm).clip(lower=0.0, upper=1.0)
            comps[INCOME_COL] = income_need

    if not comps:
        raise ValueError("acs must contain at least one need-indicator column")

    table = pd.concat(comps, axis=1)
    need = table.mean(axis=1, skipna=True)  # all-NaN row -> NaN

    out = pd.DataFrame({"geoid": df["geoid"].astype(str), "need_index": need})
    return out.sort_values("geoid").reset_index(drop=True)
