/**
 * What-if frequency explorer — faithful TypeScript port of the documented
 * interpolation/extrapolation model in `app/views/whatif.py` (Task 3.3).
 *
 * Model (documented in whatif.py): doubling frequency halves expected wait;
 * with a 7-minute static wait the saving is min(headway/4, 3.5) minutes; the
 * access gain per corridor is a linear scaling of the precomputed reference
 * (2.0×) gain by the wait-saving ratio, capped at 1.0. The affected catchment
 * population is real data and is independent of frequency.
 */
import type { SensitivityRecord } from "../types";

export const FREQ_MIN = 1.0;
export const FREQ_MAX = 3.0;
export const FREQ_DEFAULT = 2.0;
export const REFERENCE_MULTIPLIER = 2.0;
export const MAX_WAIT_SAVING_MIN = 3.5;

export function clampMultiplier(multiplier: number): number {
  return Math.min(Math.max(Number(multiplier) || FREQ_MIN, FREQ_MIN), FREQ_MAX);
}

/** Normalize a route id (null/NaN coverage row → null; string-safe). */
export function routeKey(routeId: unknown): string | null {
  if (routeId === null || routeId === undefined) return null;
  const text = String(routeId).trim();
  return text || null;
}

export function waitSavingMin(headwayMin: number | null | undefined, multiplier: number): number {
  if (headwayMin === null || headwayMin === undefined || Number.isNaN(headwayMin)) {
    return 0;
  }
  const m = clampMultiplier(multiplier);
  const saving = (headwayMin / 2) * (1 - 1 / m);
  return Math.min(saving, MAX_WAIT_SAVING_MIN);
}

export interface WhatIfProjection {
  route_id: string | null;
  corridor: string;
  action: string;
  affected_pop: number;
  multiplier: number;
  wait_saving_min: number;
  reference_wait_saving_min: number;
  gain_mean: number;
  gain_popweighted: number;
  benefited_pop: number;
}

export function lookupSensitivityRow(
  rows: SensitivityRecord[],
  routeId: unknown,
): SensitivityRecord | undefined {
  const target = routeKey(routeId);
  return rows.find((r) => routeKey(r.route_id) === target);
}

export function whatIfProjection(
  routeId: unknown,
  multiplier: number,
  rows: SensitivityRecord[],
): WhatIfProjection | null {
  const row = lookupSensitivityRow(rows, routeId);
  if (!row) return null;

  const m = clampMultiplier(multiplier);
  const sav = waitSavingMin(row.headway_min_current, m);

  // Reference wait saving: prefer the table's stored 2.0× value; fall back to
  // the model formula when it is missing/NaN/≤0.
  let savRef = typeof row.wait_saving_min === "number" ? row.wait_saving_min : 0;
  if (!(savRef > 0)) savRef = waitSavingMin(row.headway_min_current, REFERENCE_MULTIPLIER);

  const gainRatio = savRef > 0 ? sav / savRef : 0;
  const benefitFraction = Math.min(gainRatio, 1);

  const affected = typeof row.affected_pop === "number" ? row.affected_pop : 0;
  const gain = (col: keyof SensitivityRecord): number => {
    const ref = row[col];
    return typeof ref === "number" && Number.isFinite(ref) ? ref * gainRatio : 0;
  };

  return {
    route_id: routeKey(row.route_id),
    corridor: row.corridor,
    action: row.action,
    affected_pop: affected,
    multiplier: m,
    wait_saving_min: sav,
    reference_wait_saving_min: savRef,
    gain_mean: gain("est_access_gain_mean"),
    gain_popweighted: gain("est_access_gain_popweighted"),
    benefited_pop: Math.round(affected * benefitFraction),
  };
}

/** All recommended corridors (incl. coverage-gap row), by affected pop desc. */
export function sensitivityCorridors(rows: SensitivityRecord[]): SensitivityRecord[] {
  return [...rows].sort((a, b) => {
    const pa = a.affected_pop ?? 0;
    const pb = b.affected_pop ?? 0;
    return pb - pa;
  });
}
