/**
 * Color system — preserved unchanged from the Streamlit app (colorblind-safe).
 *
 * - Sequential single-hue: Need = YlOrBr, Access = Blues.
 * - Diverging RdBu for the equity gap (red = underserved, blue = better served).
 * - A–F categorical grade palette (single source of truth, mirrors
 *   `app/views/_ui.py`).
 */
import { UNKNOWN_GRADE } from "../types";

/* YlOrBr (ColorBrewer 9-class, sequential) for Need Index. */
export const NEED_RAMP = [
  "#ffffd4",
  "#fee391",
  "#fec44f",
  "#fe9929",
  "#ec7014",
  "#cc4c02",
  "#8c2d04",
];

/* Blues (ColorBrewer 9-class, sequential) for Access. */
export const ACCESS_RAMP = [
  "#eff3ff",
  "#c6dbef",
  "#9ecae1",
  "#6baed6",
  "#4292c6",
  "#2171b5",
  "#084594",
];

/* RdBu (ColorBrewer 11-class, diverging) for Equity Gap.
 * Left (red) = underserved (negative gap); right (blue) = better served. */
export const GAP_RAMP = [
  "#b2182b",
  "#d6604d",
  "#f4a582",
  "#fddbc7",
  "#f7f7f7",
  "#d1e5f0",
  "#92c5de",
  "#4393c3",
  "#2166ac",
];

/** Grade palette — exactly as established in app/views/_ui.py. */
export const GRADE_COLORS: Record<string, string> = {
  A: "#1a7f37",
  B: "#2d9d4f",
  C: "#e3b341",
  D: "#e0762a",
  F: "#c62828",
};

export function gradeColor(grade: string | null | undefined): string {
  if (!grade) return UNKNOWN_GRADE;
  const g = String(grade).trim().toUpperCase();
  return GRADE_COLORS[g] ?? UNKNOWN_GRADE;
}

/** Map-boundary / map chrome color (navy, from the legacy folium maps). */
export const MAP_LINE = "#1f3a5f";
export const MAP_FILL_BASE = "#d9e2ec"; // boundary fill
export const MISSING_FILL = "#eef0f2"; // null/NaN features (was nan_fill_color)

/** What-if highlight colors (from app/views/whatif.py). */
export const SERVED_OUTLINE = "#b45309";
export const SERVED_FILL = "#f59e0b";
export const CORRIDOR_COLOR = "#b91c1c";

export type LayerKey = "need_index" | "access_overall" | "gap" | "grade";

export interface LayerConfig {
  key: LayerKey;
  label: string;
  legend: string;
  kind: "sequential" | "diverging" | "grade";
  /** Property used for coloring. */
  column: string;
  /** Ramp (sequential/diverging) or grade map. */
  ramp?: string[];
  /** Numeric domain used for the color interpolation + legend. */
  domain?: [number, number];
}

export const LAYERS: LayerConfig[] = [
  {
    key: "need_index",
    label: "Need Index",
    legend: "Need index (higher = more need)",
    kind: "sequential",
    column: "need_index",
    ramp: NEED_RAMP,
    domain: [0, 0.63],
  },
  {
    key: "access_overall",
    label: "Access (overall)",
    legend: "Overall access score (higher = better)",
    kind: "sequential",
    column: "access_overall",
    ramp: ACCESS_RAMP,
    domain: [0, 1],
  },
  {
    key: "gap",
    label: "Equity Gap",
    legend: "Equity gap (access − need): red = underserved, blue = better served",
    kind: "diverging",
    column: "gap",
    ramp: GAP_RAMP,
    domain: [-0.39, 0.79],
  },
  {
    key: "grade",
    label: "Grade (A–F)",
    legend: "Equity grade by dimension (A best → F worst)",
    kind: "grade",
    column: "grade",
  },
];

export function layerByKey(key: LayerKey): LayerConfig {
  return LAYERS.find((l) => l.key === key) ?? LAYERS[0]!;
}
