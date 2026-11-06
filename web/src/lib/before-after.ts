/**
 * Before / After model — "If top recommendations ship".
 *
 * Honest, prepared-data-only simulation (no re-routing, no new endpoint):
 * for each block group in a recommendation's `geoids`, the after-access is
 * `clamp(access_overall + corridor_gain, 0, 1)` where `corridor_gain` is
 * the corridor's precomputed `est_access_gain_mean` from the sensitivity
 * table (reference 2.0× frequency). Need is held fixed, so after-gap is
 * `after-access − need`. Non-covered block groups are unchanged.
 *
 * Corridors join recommendations ↔ sensitivity by `route_id`
 * (normalized via `routeKey`, same as the what-if explorer).
 */
import { routeKey } from "./interpolation";
import type { SensitivityRecord } from "../types";

export interface GainInput {
  geoids?: string[];
  route_id: string | null;
}

export function computeGainsByGeoid(
  recommendations: GainInput[],
  sensitivity: SensitivityRecord[],
): Map<string, number> {
  const gainByRoute = new Map<string, number>();
  for (const row of sensitivity) {
    const key = routeKey(row.route_id);
    if (!key) continue;
    const gain = row.est_access_gain_mean;
    if (typeof gain !== "number" || !Number.isFinite(gain)) continue;
    gainByRoute.set(key, gain);
  }
  const gains = new Map<string, number>();
  for (const rec of recommendations) {
    const gain = gainByRoute.get(routeKey(rec.route_id) ?? "");
    if (gain == null) continue;
    for (const geoid of rec.geoids ?? []) {
      const g = String(geoid);
      // Multiple corridors hitting one block group: take the max gain
      // (documented choice; overlaps are rare — 25 BGs / 14 corridors).
      gains.set(g, Math.max(gains.get(g) ?? 0, gain));
    }
  }
  return gains;
}

export function afterAccess(access: number, gain: number | undefined): number {
  const g = gain ?? 0;
  const v = access + g;
  if (v < 0) return 0;
  if (v > 1) return 1;
  return v;
}
