/**
 * Drilldown "needs" helpers — grade-driven need card, geometry centroid,
 * and nearest-corridor distance ranking. Split out of
 * components/drilldown.ts during Task 010 modularization. Data semantics
 * unchanged.
 */
import { escapeHtml } from "./format";
import { busSvg } from "./mascot";
import type { EquityFeature, RecommendationFeature, RecommendationProperties } from "../types";

/** Bounding-box centroid of the feature geometry (for distance rank). */
export function featureCentroid(
  f: EquityFeature,
): { lat: number; lon: number } | null {
  const geom = f.geometry;
  if (!geom) return null;
  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLon = Infinity;
  let maxLon = -Infinity;
  const visit = (coords: unknown): void => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      const [lon, lat] = coords as [number, number];
      minLon = Math.min(minLon, lon);
      maxLon = Math.max(maxLon, lon);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
      return;
    }
    for (const c of coords) visit(c);
  };
  visit(geom.coordinates);
  if (!Number.isFinite(minLat)) return null;
  return { lat: (minLat + maxLat) / 2, lon: (minLon + maxLon) / 2 };
}

export function nearestCorridor(
  feature: EquityFeature,
  recommendations: RecommendationFeature[],
): {
  corridor: string;
  distKm: number | null;
} | null {
  const c = featureCentroid(feature);
  if (!c || recommendations.length === 0) return null;
  let best: { corridor: string; dist: number } | null = null;
  for (const f of recommendations) {
    const props = f.properties as RecommendationProperties;
    const { centroid_lat, centroid_lon } = props;
    if (typeof centroid_lat !== "number" || typeof centroid_lon !== "number") continue;
    const dLat = (centroid_lat - c.lat) * 111;
    const dLon = (centroid_lon - c.lon) * 111 * Math.cos((c.lat * Math.PI) / 180);
    const dist = Math.hypot(dLat, dLon);
    if (!best || dist < best.dist) best = { corridor: props.corridor, dist };
  }
  if (!best) return null;
  return { corridor: best.corridor, distKm: best.dist };
}

/**
 * Grade-driven "What this area needs" card (no corridor serves this
 * block group): worst category grade → one-sentence need + nearest
 * corridor by centroid distance (labelled nearest, never serving).
 */
export function buildNeedsCard(
  p: EquityFeature["properties"],
  feature: EquityFeature,
  recommendations: RecommendationFeature[],
): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "dn-needs";
  const cats: Array<[string, string | null]> = [
    ["Jobs", p.jobs_grade],
    ["Healthcare", p.healthcare_grade],
    ["Schools", p.schools_grade],
    ["Food", p.food_grade],
  ];
  const rank = (g: string | null): number =>
    ({ A: 0, B: 1, C: 2, D: 3, F: 4 })[String(g ?? "").trim().toUpperCase()] ?? 5;
  const worst = [...cats].sort((a, b) => rank(b[1]) - rank(a[1]))[0]!;
  const worstLabel = `${worst[0]} ${String(worst[1] ?? "—").trim().toUpperCase() || "—"}`;
  const needSentence =
    worst[0] === "Jobs"
      ? "Improving job access matters most here — the Jobs grade is the thinnest thread."
      : `${worst[0]} access is the thinnest thread — the ${worstLabel} grade says it plainly.`;
  const nearest = nearestCorridor(feature, recommendations);
  const nearHtml =
    nearest && nearest.distKm != null
      ? `<div class="dn-rec-pop">Nearest corridor (not serving here): ${escapeHtml(nearest.corridor)} · ≈ ${nearest.distKm.toFixed(1)} km from this block group’s center.</div>`
      : nearest
        ? `<div class="dn-rec-pop">Nearest corridor (not serving here): ${escapeHtml(nearest.corridor)}.</div>`
        : "";
  wrap.innerHTML =
    `<span class="dn-mascot" aria-hidden="true">${busSvg({ size: 56 })}</span>` +
    `<div class="dn-needs-lead">${escapeHtml(needSentence)}</div>` +
    `<div class="dn-rec-pop">Overall grade ${escapeHtml(String(p.grade ?? "—").trim().toUpperCase() || "—")} · gap ${p.gap >= 0 ? "+" : "−"}${Math.abs(p.gap).toFixed(2)} (access − need).</div>` +
    nearHtml;
  return wrap;
}
