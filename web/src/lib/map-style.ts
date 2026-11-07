/**
 * Map style helpers — shared by the MapView class (and any future map
 * surface). Pure paint/expression/legend builders: no MapLibre instance
 * state, no DOM owned here apart from the legend widget.
 *
 * Split out of components/map-view.ts during Task 010 modularization.
 * Color palettes preserved unchanged (colorblind-safe data layers).
 */
import type { ExpressionSpecification } from "maplibre-gl";
import { afterAccess } from "./before-after";
import {
  GRADE_COLORS,
  MISSING_FILL,
  layerByKey,
  type LayerConfig,
  type LayerKey,
} from "./colors";
import { paintSketchBoxes } from "./sketch";
import type { EquityFeatureCollection } from "../types";

/* Paper-tinted map background; data layers (fills, selection) untouched. */
export const BG = "#f2ece0";

export interface FillPaint {
  "fill-color": ExpressionSpecification;
  "fill-opacity": number;
}

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function gradientCss(ramp: string[]): string {
  const step = 100 / (ramp.length - 1);
  const stops = ramp.map((c, i) => `${c} ${Math.round(i * step)}%`);
  return `linear-gradient(to right, ${stops.join(", ")})`;
}

export function buildColorExpression(cfg: LayerConfig): ExpressionSpecification {
  const get = ["get", cfg.column] as ExpressionSpecification;

  if (cfg.kind === "grade") {
    const match: unknown[] = ["match", get];
    for (const [grade, color] of Object.entries(GRADE_COLORS)) {
      match.push(grade, color);
    }
    match.push(MISSING_FILL); // default (unknown / missing)
    return match as ExpressionSpecification;
  }

  // Sequential: equal-spaced stops across the domain.
  // Diverging: explicit stops anchored at 0 (red — underserved ↔ blue — served).
  const stops: Array<[number, string]> = [];
  if (cfg.kind === "diverging") {
    const gapStops: Array<[number, string]> = [
      [-0.39, "#b2182b"],
      [-0.25, "#d6604d"],
      [-0.12, "#f4a582"],
      [-0.04, "#fddbc7"],
      [0, "#f7f7f7"],
      [0.15, "#d1e5f0"],
      [0.35, "#92c5de"],
      [0.55, "#4393c3"],
      [0.79, "#2166ac"],
    ];
    stops.push(...gapStops);
  } else {
    const [lo, hi] = cfg.domain!;
    const n = cfg.ramp!.length;
    for (let i = 0; i < n; i++) {
      const v = lo + ((hi - lo) * i) / (n - 1);
      stops.push([Number(v.toFixed(4)), cfg.ramp![i]!]);
    }
  }

  const interpolate = [
    "interpolate",
    ["linear"],
    get,
    ...stops.flat(),
  ] as unknown as ExpressionSpecification;

  // Missing/null value → neutral fill (was nan_fill_color).
  return [
    "case",
    ["all", ["has", cfg.column], ["!=", get, null]],
    interpolate,
    MISSING_FILL,
  ] as unknown as ExpressionSpecification;
}

/** Paint spec for an analysis fill layer at a given config. */
export function buildFillPaint(cfg: LayerConfig): FillPaint {
  return {
    "fill-color": buildColorExpression(cfg),
    "fill-opacity": cfg.kind === "grade" ? 0.7 : 0.65,
  };
}

/**
 * Column swapped to its `*_after` twin in After mode (gap/access only).
 * Gap in After rescales the diverging domain to the changed range so
 * the small shift reads (honestly labelled "estimated"; the full
 * today domain is [-0.39, 0.79]).
 */
export function effectiveConfig(
  layer: LayerKey,
  mode: "today" | "after",
  gains: Map<string, number>,
  equity: EquityFeatureCollection,
): LayerConfig {
  const cfg = layerByKey(layer);
  if (mode !== "after") return cfg;
  if (cfg.column === "gap") {
    const range = changedGapAfterRange(equity, gains);
    return { ...cfg, column: "gap_after", domain: range ?? cfg.domain };
  }
  if (cfg.column === "access_overall") return { ...cfg, column: "access_after" };
  return cfg;
}

export function changedGapAfterRange(
  equity: EquityFeatureCollection,
  gains: Map<string, number>,
): [number, number] | null {
  if (gains.size === 0) return null;
  let lo = Number.POSITIVE_INFINITY;
  let hi = Number.NEGATIVE_INFINITY;
  for (const f of equity.features) {
    const g = gains.get(String(f.properties.geoid));
    if (g == null) continue;
    const v = afterAccess(f.properties.access_overall, g) - f.properties.need_index;
    lo = Math.min(lo, v);
    hi = Math.max(hi, v);
  }
  if (!Number.isFinite(lo) || !Number.isFinite(hi) || hi - lo < 0.05) return null;
  return [Number(lo.toFixed(2)), Number(hi.toFixed(2))];
}

/** Filter expression for changed-only / unchanged-only layers. */
export function changedFilterExpression(
  gains: Map<string, number>,
  changed: boolean,
): ExpressionSpecification {
  const ids = [...gains.keys()];
  if (changed) {
    return ["in", ["get", "geoid"], ["literal", ids]] as unknown as ExpressionSpecification;
  }
  return ["all", ["has", "geoid"], ["!", ["in", ["get", "geoid"], ["literal", ids]]]] as unknown as ExpressionSpecification;
}

/** Equity features augmented with `gap_after` / `access_after` (clone). */
export function equityWithAfter(
  equity: EquityFeatureCollection,
  gains: Map<string, number>,
): EquityFeatureCollection {
  if (gains.size === 0) return equity;
  return {
    type: "FeatureCollection",
    features: equity.features.map((f) => {
      const p = f.properties;
      const accessAfter = afterAccess(p.access_overall, gains.get(String(p.geoid)));
      return {
        ...f,
        properties: {
          ...p,
          access_after: accessAfter,
          gap_after: accessAfter - p.need_index,
        },
      };
    }),
  };
}

/** Render the adaptive legend (sequential/diverging/grade) into `legendEl`. */
export function renderLegendInto(
  legendEl: HTMLElement,
  key: LayerKey,
  mode: "today" | "after",
  opts: { gains: Map<string, number>; equity: EquityFeatureCollection },
): void {
  const cfg = effectiveConfig(key, mode, opts.gains, opts.equity);
  const inner = document.createElement("div");
  inner.className = "dn-map-legend-inner";

  const title = document.createElement("div");
  title.className = "dn-map-legend-title";
  title.textContent = cfg.label;
  inner.appendChild(title);

  if (cfg.kind === "grade") {
    const grid = document.createElement("div");
    grid.className = "dn-legend-grade-grid";
    for (const [grade, color] of Object.entries(GRADE_COLORS)) {
      const row = document.createElement("div");
      row.className = "dn-legend-grade-row";
      row.innerHTML = `<span class="dn-legend-swatch" style="background:${color}"></span><span>${grade}</span>`;
      grid.appendChild(row);
    }
    inner.appendChild(grid);
  } else {
    const [lo, hi] = cfg.domain!;
    const labels =
      cfg.kind === "diverging"
        ? `<span>${lo.toFixed(2)} · underserved</span><span>0</span><span>${hi.toFixed(2)} · better served</span>`
        : `<span>${lo.toFixed(2)}</span><span>${hi.toFixed(2)}</span>`;
    inner.innerHTML += `
      <div class="dn-legend-gradient" style="background:${gradientCss(cfg.ramp!)}" aria-hidden="true"></div>
      <div class="dn-legend-labels">${labels}</div>`;
  }

  const note = document.createElement("div");
  note.className = "dn-map-legend-note";
  note.textContent =
    mode === "after"
      ? `${cfg.legend}. After (estimated): access + corridor gain, no re-routing. Scale fits the moving block groups.`
      : cfg.legend;
  inner.appendChild(note);

  legendEl.replaceChildren(inner);
  paintSketchBoxes(legendEl);
}
