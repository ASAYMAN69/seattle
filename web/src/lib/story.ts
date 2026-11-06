/**
 * Human story anchor — deterministically pick ONE real low-income block
 * group from the already-loaded equity features (no extra fetch, no
 * invented figures) and fill its narrative from prepared fields only.
 *
 * Selection rule (documented): candidates are block groups with
 * poverty_pct ≥ 25%, population ≥ 500, need_index ≥ 0.30, and gap < 0
 * (underserved). Among them, prefer low income: lowest median_income,
 * then most negative gap, then lowest poverty (for tie-break stability).
 * Fallbacks relax poverty to ≥ 20%, then ≥ 0%, never fabricating.
 *
 * No travel-time field exists in the prepared data (equity carries only
 * 0–1 access scores; sensitivity carries wait-saving in minutes) — so the
 * narrative describes access qualitatively from scores/grades.
 */
import { fmtCurrency, fmtInt, fmtPct } from "./format";
import type { EquityFeature, EquityFeatureCollection } from "../types";

export interface StoryAnchor {
  geoid: string;
  tract: string | null;
  bg: string | null;
  population: number | null;
  povertyPct: number | null;
  zeroCarPct: number | null;
  medianIncome: number | null;
  needIndex: number;
  accessOverall: number;
  gap: number;
  jobsAccess: number;
  healthcareAccess: number;
  foodAccess: number;
  schoolsAccess: number;
  grade: string | null;
}

function isFiniteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function pickFrom(features: EquityFeature[], minPoverty: number): EquityFeature | null {
  const pool = features.filter((f) => {
    const p = f.properties;
    if (!isFiniteNumber(p.poverty_pct) || p.poverty_pct < minPoverty) return false;
    if (!isFiniteNumber(p.pop_total) || p.pop_total < 500) return false;
    if (!isFiniteNumber(p.need_index) || p.need_index < 0.3) return false;
    if (!isFiniteNumber(p.gap) || p.gap >= 0) return false;
    return true;
  });
  pool.sort((a, b) => {
    const pa = a.properties;
    const pb = b.properties;
    const ia = isFiniteNumber(pa.median_income) ? pa.median_income : Number.POSITIVE_INFINITY;
    const ib = isFiniteNumber(pb.median_income) ? pb.median_income : Number.POSITIVE_INFINITY;
    if (ia !== ib) return ia - ib;
    if (pa.gap !== pb.gap) return pa.gap - pb.gap;
    const va = isFiniteNumber(pa.poverty_pct) ? pa.poverty_pct : 0;
    const vb = isFiniteNumber(pb.poverty_pct) ? pb.poverty_pct : 0;
    if (vb !== va) return vb - va;
    return String(pa.geoid).localeCompare(String(pb.geoid));
  });
  return pool[0] ?? null;
}

/** Deterministic anchor pick: poverty ≥ 25% → ≥ 20% → ≥ 0%. */
export function pickStoryAnchor(equity: EquityFeatureCollection): EquityFeature | null {
  const features = equity.features;
  if (!features.length) return null;
  return (
    pickFrom(features, 0.25) ?? pickFrom(features, 0.2) ?? pickFrom(features, 0)
  );
}

export function toStoryAnchor(feature: EquityFeature): StoryAnchor {
  const p = feature.properties;
  return {
    geoid: String(p.geoid),
    tract: p.TRACTCE ?? null,
    bg: p.BLKGRPCE ?? null,
    population: p.pop_total,
    povertyPct: p.poverty_pct,
    zeroCarPct: p.zero_car_pct,
    medianIncome: p.median_income,
    needIndex: p.need_index,
    accessOverall: p.access_overall,
    gap: p.gap,
    jobsAccess: p.jobs_access,
    healthcareAccess: p.healthcare_access,
    foodAccess: p.food_access,
    schoolsAccess: p.schools_access,
    grade: p.grade ? String(p.grade) : null,
  };
}

/** Qualitative weakest-category sentence from prepared access scores. */
export function weakestCategoryLine(a: StoryAnchor): string {
  const cats: Array<[string, number]> = [
    ["jobs", a.jobsAccess],
    ["healthcare", a.healthcareAccess],
    ["food", a.foodAccess],
    ["schools", a.schoolsAccess],
  ];
  const weak = cats.filter(([, v]) => v <= 0.01);
  const fmt = (names: string[]) =>
    names.length > 1
      ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`
      : names[0]!;
  if (weak.length >= 3) {
    return `Transit access scores sit near zero for ${fmt(weak.map(([n]) => n))} — getting there is a real trip on any given day.`;
  }
  if (weak.length > 0) {
    return `The thinnest thread is ${fmt(weak.map(([n]) => n))}: access scores there sit near zero.`;
  }
  const lowest = [...cats].sort((x, y) => x[1] - y[1])[0]!;
  return `The lowest score is ${lowest[0]} access at ${fmtPct(lowest[1])} — the other categories sit a little higher, but not by much.`;
}

/**
 * One-paragraph, real-numbers-only narrative. No commute-minutes claim —
 * the prepared data carries no travel-time field.
 */
export function storyNarrative(a: StoryAnchor, nRecommendations: number): string {
  const id = a.tract ? `Tract ${a.tract}${a.bg ? ` / BG ${a.bg}` : ""}` : "this block group";
  const income =
    a.medianIncome != null ? `The median household income is ${fmtCurrency(a.medianIncome)}.` : "";
  const rec =
    nRecommendations > 0
      ? ` ${nRecommendations} corridor recommendation${nRecommendations > 1 ? "s" : ""} target${nRecommendations > 1 ? "" : "s"} this area — open the report card to see which bus gets help first.`
      : " No corridor recommendation targets this block group yet, which is exactly the gap the index is built to surface.";
  return (
    `Meet block group ${a.geoid} (${id}) — home to ${fmtInt(a.population)} residents, ` +
    `where ${fmtPct(a.povertyPct)} live in poverty and ${fmtPct(a.zeroCarPct)} of households have no car. ` +
    `Need index ${a.needIndex.toFixed(2)} against overall access ${a.accessOverall.toFixed(2)} ` +
    `(equity gap ${a.gap >= 0 ? "+" : "−"}${Math.abs(a.gap).toFixed(2)}). ` +
    `${weakestCategoryLine(a)} ${income}${rec}`
  );
}
