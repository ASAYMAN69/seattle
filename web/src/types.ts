/**
 * Shared types for the Seattle Transit Equity Index SPA.
 *
 * These mirror the FastAPI contract (built in parallel by the Wizard agent)
 * and are shaped from the real prepared data under `data/prepared/`.
 * Keep field names in sync with `api/` and `app/views/`.
 */

/* ------------------------------------------------------------------ */
/* GeoJSON primitives                                                  */
/* ------------------------------------------------------------------ */

export interface GeoJsonGeometry {
  type: string;
  coordinates: unknown;
}

export interface GeoJsonFeature<P = Record<string, unknown>> {
  type: "Feature";
  geometry: GeoJsonGeometry | null;
  properties: P;
}

export interface GeoJsonFeatureCollection<P = Record<string, unknown>> {
  type: "FeatureCollection";
  features: GeoJsonFeature<P>[];
}

/* ------------------------------------------------------------------ */
/* Equity scores (block groups)                                        */
/* ------------------------------------------------------------------ */

export type Grade = "A" | "B" | "C" | "D" | "F";
export const UNKNOWN_GRADE = "#6b7280";

export interface EquityProperties {
  geoid: string;
  GEOID: string;
  STATEFP: string;
  COUNTYFP: string;
  TRACTCE: string;
  BLKGRPCE: string;
  /** Opportunity access scores (0–1, higher = better). */
  jobs_access: number;
  healthcare_access: number;
  schools_access: number;
  food_access: number;
  access_overall: number;
  /** Composite need index (0–1, higher = more need). */
  need_index: number;
  /** Access − need. Negative = underserved (red on the gap layer). */
  gap: number;
  grade: Grade | string | null;
  jobs_grade: Grade | string | null;
  healthcare_grade: Grade | string | null;
  schools_grade: Grade | string | null;
  food_grade: Grade | string | null;
  pop_total: number | null;
  /** ACS statistics (joined by the API — `GET /api/equity` is ACS-joined). */
  poverty_pct: number | null;
  zero_car_pct: number | null;
  median_income: number | null;
}

export type EquityFeature = GeoJsonFeature<EquityProperties>;
export type EquityFeatureCollection = GeoJsonFeatureCollection<EquityProperties>;

/* ------------------------------------------------------------------ */
/* Recommendations (corridors)                                         */
/* ------------------------------------------------------------------ */

export interface RecommendationProperties {
  route_id: string | null;
  corridor: string;
  action: string;
  affected_pop: number;
  n_block_groups: number;
  mean_gap: number;
  mean_need: number;
  mean_access_overall: number;
  am_peak_trips: number | null;
  headway_min_current: number | null;
  wait_saving_min: number | null;
  centroid_lat: number | null;
  centroid_lon: number | null;
  /** Block-group geoids the recommendation serves. */
  geoids: string[];
}

export type RecommendationFeature = GeoJsonFeature<RecommendationProperties>;
export type RecommendationFeatureCollection = GeoJsonFeatureCollection<RecommendationProperties>;

/* ------------------------------------------------------------------ */
/* Sensitivity table (what-if explorer)                                */
/* ------------------------------------------------------------------ */

export interface SensitivityRecord {
  route_id: string | null;
  corridor: string;
  action: string;
  affected_pop: number | null;
  n_block_groups: number | null;
  geoids: string[] | null;
  am_peak_trips: number | null;
  headway_min_current: number | null;
  wait_saving_min: number | null;
  est_access_gain_mean: number | null;
  est_access_gain_popweighted: number | null;
}

/* ------------------------------------------------------------------ */
/* Report cards & city summary                                         */
/* ------------------------------------------------------------------ */

export interface ReportCard {
  geoid: string;
  jobs_access: number | null;
  healthcare_access: number | null;
  schools_access: number | null;
  food_access: number | null;
  access_overall: number | null;
  need_index: number | null;
  gap: number | null;
  grade: Grade | string | null;
  jobs_grade: Grade | string | null;
  healthcare_grade: Grade | string | null;
  schools_grade: Grade | string | null;
  food_grade: Grade | string | null;
  pop_total: number | null;
  poverty_pct: number | null;
  zero_car_pct: number | null;
  median_income: number | null;
}

export interface GradeCounts {
  A: number;
  B: number;
  C: number;
  D: number;
  F: number;
}

export interface CitySummary {
  n_block_groups: number;
  n_with_grade: number;
  grade_counts: GradeCounts;
  mean_access_overall: number;
  mean_need: number;
  mean_gap: number;
  median_gap: number;
  n_recommendations: number;
  total_recommended_population: number;
}

export interface ReportCardsResponse {
  generated_at: string;
  summary: CitySummary;
  report_cards: Record<string, ReportCard>;
}

/* ------------------------------------------------------------------ */
/* Export                                                              */
/* ------------------------------------------------------------------ */

/** Column order shared by the report-card snapshot and top-underserved table. */
export const SNAPSHOT_COLUMNS = [
  "geoid",
  "grade",
  "jobs_grade",
  "healthcare_grade",
  "schools_grade",
  "food_grade",
  "jobs_access",
  "healthcare_access",
  "schools_access",
  "food_access",
  "access_overall",
  "need_index",
  "gap",
  "pop_total",
  "poverty_pct",
  "zero_car_pct",
  "median_income",
] as const;

export type SnapshotColumn = (typeof SNAPSHOT_COLUMNS)[number];
export type TopUnderservedRow = Record<SnapshotColumn, number | string | null>;

export interface MetadataResponse {
  generated_at?: string;
  summary?: CitySummary;
  methodology_note?: string;
}
