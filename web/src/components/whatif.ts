/**
 * What-if frequency explorer — corridor dropdown + frequency-multiplier slider
 * with interpolated/extrapolated projections (port of app/views/whatif.py),
 * plus a highlight map (corridor + served block groups).
 * Sketch theme: ink-soft controls, amber callout, count-up metrics on
 * corridor change (instant on slider drag). Interpolation model untouched.
 *
 * The highlight map lives in whatif-map.ts (Task 010 modularization).
 */
import { countUpTo } from "../lib/countup";
import { escapeHtml, fmtInt, fmtMinutes, fmtPp } from "../lib/format";
import {
  FREQ_DEFAULT,
  FREQ_MAX,
  FREQ_MIN,
  REFERENCE_MULTIPLIER,
  routeKey,
  sensitivityCorridors,
  whatIfProjection,
  type WhatIfProjection,
} from "../lib/interpolation";
import { busSvg } from "../lib/mascot";
import { paintSketchBoxes } from "../lib/sketch";
import type {
  EquityFeatureCollection,
  RecommendationFeatureCollection,
  SensitivityRecord,
} from "../types";
import { WhatIfMapView } from "./whatif-map";

interface WhatIfOptions {
  container: HTMLElement;
  sensitivity: SensitivityRecord[];
  recommendations: RecommendationFeatureCollection;
  equity: EquityFeatureCollection;
  boundary: GeoJSON.FeatureCollection;
}

export class WhatIfView {
  private container: HTMLElement;
  private sensitivity: SensitivityRecord[];
  private recommendations: RecommendationFeatureCollection;
  private equity: EquityFeatureCollection;
  private boundary: GeoJSON.FeatureCollection;

  private corridorSelect: HTMLSelectElement;
  private slider: HTMLInputElement;
  private sliderValue: HTMLElement;
  private callout: HTMLElement;
  private metrics: HTMLElement;
  private minimap: WhatIfMapView;

  private selectedRouteId: string | null = null;
  private selectedMultiplier = FREQ_DEFAULT;
  private lastRouteKey: string | null | undefined = undefined;

  constructor(options: WhatIfOptions) {
    this.container = options.container;
    this.sensitivity = options.sensitivity;
    this.recommendations = options.recommendations;
    this.equity = options.equity;
    this.boundary = options.boundary;

    this.container.innerHTML = `
      <div class="dn-whatif-controls sketch-card">
        <label class="dn-field">
          <span class="dn-field-label">Recommended corridor</span>
          <select class="dn-select"></select>
        </label>
        <label class="dn-field dn-field-slider">
          <span class="dn-field-label">Frequency multiplier
            <output class="dn-slider-output"></output>
          </span>
          <input class="dn-range" type="range" min="${FREQ_MIN}" max="${FREQ_MAX}"
            step="0.1" value="${FREQ_DEFAULT}" />
          <span class="dn-range-hint">× current weekday AM-peak frequency · all estimates interpolated from the precomputed sensitivity table (no live routing)</span>
        </label>
      </div>
      <div class="dn-callout sketch-card" hidden></div>
      <div class="dn-metric-grid"></div>
      <div class="dn-minimap sketch-card"></div>`;

    this.corridorSelect = this.container.querySelector(".dn-select") as HTMLSelectElement;
    this.slider = this.container.querySelector(".dn-range") as HTMLInputElement;
    this.sliderValue = this.container.querySelector(".dn-slider-output") as HTMLElement;
    this.callout = this.container.querySelector(".dn-callout") as HTMLElement;
    this.metrics = this.container.querySelector(".dn-metric-grid") as HTMLElement;
    this.minimap = new WhatIfMapView({
      container: this.container.querySelector(".dn-minimap") as HTMLElement,
      boundary: this.boundary,
      equity: this.equity,
      recommendations: this.recommendations,
    });

    this.populateCorridors();
    this.bindEvents();
    this.render();
    paintSketchBoxes(this.container);
  }

  private populateCorridors(): void {
    const corridors = sensitivityCorridors(this.sensitivity);
    for (const c of corridors) {
      const opt = document.createElement("option");
      opt.value = c.route_id ?? "__coverage__";
      const pop = c.affected_pop != null ? ` · ~${fmtInt(c.affected_pop)} residents` : "";
      opt.textContent = `${c.corridor}${pop}`;
      this.corridorSelect.appendChild(opt);
    }
    this.selectedRouteId = corridors[0]?.route_id ?? null;
  }

  private bindEvents(): void {
    this.corridorSelect.addEventListener("change", () => {
      const raw = this.corridorSelect.value;
      this.selectedRouteId = raw === "__coverage__" ? null : raw;
      this.render();
    });

    this.slider.addEventListener("input", () => {
      this.selectedMultiplier = Number(this.slider.value);
      this.render();
    });
  }

  private render(): void {
    this.sliderValue.textContent = `${this.selectedMultiplier.toFixed(1)}×`;

    const proj = whatIfProjection(this.selectedRouteId, this.selectedMultiplier, this.sensitivity);
    if (!proj) {
      this.callout.hidden = true;
      this.metrics.innerHTML = `<div class="dn-empty"><span class="dn-mascot" aria-hidden="true">${busSvg({ size: 56 })}</span><p>This corridor was not found in the sensitivity data.</p></div>`;
      this.lastRouteKey = routeKey(this.selectedRouteId);
      paintSketchBoxes(this.container);
      return;
    }

    const key = routeKey(proj.route_id);
    const shouldAnimate = key !== this.lastRouteKey;
    this.lastRouteKey = key;

    this.callout.hidden = false;
    this.callout.textContent = proj.action;
    this.renderMetrics(proj, shouldAnimate);
    this.minimap.update(proj);
    paintSketchBoxes(this.container);
  }

  private renderMetrics(proj: WhatIfProjection, animate: boolean): void {
    const tiles: Array<{
      label: string;
      value: number;
      hint: string;
      format: (v: number) => string;
    }> = [
      { label: "Affected residents (recommended area)", value: proj.affected_pop, hint: "", format: (v) => fmtInt(v) },
      { label: "Newly benefiting residents", value: proj.benefited_pop, hint: `of ${fmtInt(proj.affected_pop)} catchment`, format: (v) => fmtInt(v) },
      { label: "Est. wait saving", value: proj.wait_saving_min, hint: `reference (2.0×): ≈ ${fmtMinutes(proj.reference_wait_saving_min)}`, format: (v) => fmtMinutes(v) },
      { label: "Access improvement (mean)", value: proj.gain_mean, hint: `pop-weighted ${fmtPp(proj.gain_popweighted)}`, format: (v) => fmtPp(v) },
    ];
    this.metrics.innerHTML = "";
    for (const t of tiles) {
      const tile = document.createElement("div");
      tile.className = "dn-metric";
      tile.innerHTML = `<div class="dn-metric-label">${escapeHtml(t.label)}</div>
        <div class="dn-metric-value">${escapeHtml(t.format(t.value))}</div>
        ${t.hint ? `<div class="dn-metric-hint">${escapeHtml(t.hint)}</div>` : ""}`;
      const valueEl = tile.querySelector(".dn-metric-value") as HTMLElement;
      this.metrics.appendChild(tile);
      if (animate) {
        countUpTo(valueEl, t.value, { format: t.format });
      } else {
        valueEl.textContent = t.format(t.value);
      }
    }
  }
}

export { REFERENCE_MULTIPLIER };
