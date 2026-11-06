/**
 * Commute narrator — mascot-led, wait/ride/walk style breakdown for the
 * anchor block group from prepared fields only.
 *
 * Data honesty: the prepared data carries no travel-time field (equity =
 * 0–1 access scores; sensitivity = wait-saving minutes + headway).
 * Numbers below cite their source fields; anything the data lacks is
 * described qualitatively, never invented.
 */
import { fmtCurrency, fmtInt, fmtMinutes, fmtPct } from "./format";
import type { EquityFeature, RecommendationFeature, SensitivityRecord } from "../types";

export interface NarratorStep {
  kicker: string;
  claim: string;
  detail: string;
}

const accessLabel = (v: number): string =>
  v <= 0.01 ? "near zero" : v >= 0.99 ? "full" : fmtPct(v);

export function buildNarratorSteps(
  feature: EquityFeature,
  recommendations: RecommendationFeature[],
  sensitivity: SensitivityRecord[],
): NarratorStep[] {
  const p = feature.properties;
  const geoid = String(p.geoid);
  const recs = recommendations.filter((f) =>
    (f.properties.geoids ?? []).includes(geoid),
  );
  const rec = recs.sort(
    (a, b) => (b.properties.affected_pop ?? 0) - (a.properties.affected_pop ?? 0),
  )[0];
  const recProps = rec?.properties;
  const sens = recProps
    ? sensitivity.find(
        (r) => String(r.route_id ?? "") === String(recProps.route_id ?? ""),
      )
    : undefined;

  const steps: NarratorStep[] = [];

  // 1 · Wait (real headway + model saving when a recommendation exists).
  if (recProps && recProps.headway_min_current != null) {
    const saving = recProps.wait_saving_min;
    steps.push({
      kicker: "Wait",
      claim: `${(recProps.headway_min_current).toFixed(1)} min between buses`,
      detail: saving != null
        ? `Route ${escapePlain(recProps.corridor.replace(/^Route\\s+/i, "") || "headway")} runs about every ${fmtMinutes(recProps.headway_min_current)} in the AM peak. If the recommendation ships, the precomputed model saves roughly ${fmtMinutes(saving)} of waiting.`
        : `Route ${escapePlain(recProps.corridor)} runs about every ${fmtMinutes(recProps.headway_min_current)} in the AM peak.`,
    });
  } else {
    steps.push({
      kicker: "Wait",
      claim: "Waiting is part of the trip",
      detail: "No corridor recommendation targets this block group yet, so there is no headway figure to quote. The what-if tab shows what more frequency would buy elsewhere.",
    });
  }

  // 2 · Ride (access scores — what the data says you can reach).
  const rideBits = [
    `jobs ${accessLabel(p.jobs_access)}`,
    `healthcare ${accessLabel(p.healthcare_access)}`,
    `food ${accessLabel(p.food_access)}`,
    `schools ${accessLabel(p.schools_access)}`,
  ];
  steps.push({
    kicker: "Ride",
    claim: "What the ride can reach",
    detail: `Transit access scores: ${rideBits.join(", ")}. The scores, not a travel-time table, are what the data carries — near zero means the model found almost nothing reachable.`,
  });

  // 3 · Walk (qualitative; zero-car share is real).
  steps.push({
    kicker: "Walk",
    claim: "The first mile is on foot",
    detail: `${fmtPct(p.zero_car_pct)} of households here have no car, so every trip starts on foot. The data does not carry walking times — under a third is all we should claim.`,
  });

  // 4 · After (real recommendation + gain; estimated, labeled).
  const gain = sens?.est_access_gain_mean;
  steps.push({
    kicker: "If recommendations ship",
    claim: recProps ? `Route ${escapePlain(recProps.corridor.replace(/^Route\\s+/i, "") || "frequency")} gets help first` : "The gap is the point",
    detail: recProps
      ? `The corridor targets about ${fmtInt(recProps.affected_pop)} residents. The sensitivity table estimates a mean access gain of ${gain != null ? `+${(gain * 100).toFixed(1)} pp` : "n/a"} for this corridor (estimate, no re-routing). Median income here is ${fmtCurrency(p.median_income)}.`
      : `Closing this gap is the index's whole argument: high need, low access, real people.`,
  });

  void gain;
  return steps;
}

function escapePlain(s: string): string {
  return s.replace(/[<>&"]/g, "");
}
