/**
 * What-if frequency explorer — corridor dropdown + frequency-multiplier slider
 * with interpolated/extrapolated projections (port of app/views/whatif.py),
 * plus a highlight map (corridor + served block groups).
 * Sketch theme: ink-soft controls, amber callout, count-up metrics on
 * corridor change (instant on slider drag). Interpolation model untouched.
 */
import {
  LngLatBounds,
  Map as MapLibreMap,
  type GeoJSONSource,
} from "maplibre-gl";
import {
  CORRIDOR_COLOR,
  MAP_FILL_BASE,
  MAP_LINE,
  SERVED_FILL,
  SERVED_OUTLINE,
} from "../lib/colors";
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

interface WhatIfOptions {
  container: HTMLElement;
  sensitivity: SensitivityRecord[];
  recommendations: RecommendationFeatureCollection;
  equity: EquityFeatureCollection;
  boundary: GeoJSON.FeatureCollection;
}

/* Paper-tinted map background to sit inside the sketch theme.
 * Data layers (served/corridor paints) are untouched. */
const BG = "#f2ece0";

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
  private mapEl: HTMLElement;
  private map: MapLibreMap | null = null;

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
    this.mapEl = this.container.querySelector(".dn-minimap") as HTMLElement;

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
    this.renderMap(proj);
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

  private renderMap(proj: WhatIfProjection): void {
    if (this.map) {
      this.updateMapSources(proj);
      return;
    }

    this.map = new MapLibreMap({
      container: this.mapEl,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          { id: "background", type: "background", paint: { "background-color": BG } },
          { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.6 } },
        ],
      },
      center: [-122.32, 47.6],
      zoom: 10.6,
      attributionControl: { compact: true },
    });

    this.map.on("load", () => {
      this.map!.addSource("boundary", {
        type: "geojson",
        data: this.boundary as unknown as GeoJSON.GeoJSON,
      });
      this.map!.addLayer({
        id: "boundary-fill",
        type: "fill",
        source: "boundary",
        paint: { "fill-color": MAP_FILL_BASE, "fill-opacity": 0.15 },
      });
      this.map!.addLayer({
        id: "boundary-line",
        type: "line",
        source: "boundary",
        paint: { "line-color": MAP_LINE, "line-width": 2, "line-opacity": 0.9 },
      });
      this.map!.addSource("served", { type: "geojson", data: emptyFC() });
      this.map!.addLayer({
        id: "served-fill",
        type: "fill",
        source: "served",
        paint: { "fill-color": SERVED_FILL, "fill-opacity": 0.28 },
      });
      this.map!.addLayer({
        id: "served-line",
        type: "line",
        source: "served",
        paint: { "line-color": SERVED_OUTLINE, "line-width": 2 },
      });
      this.map!.addSource("corridor", { type: "geojson", data: emptyFC() });
      this.map!.addLayer({
        id: "corridor-line",
        type: "line",
        source: "corridor",
        paint: { "line-color": CORRIDOR_COLOR, "line-width": 4, "line-opacity": 0.95 },
      });

      this.fitBoundary();
      this.updateMapSources(proj);
    });
  }

  private updateMapSources(proj: WhatIfProjection): void {
    if (!this.map) return;

    // Served block groups for this recommendation.
    const rec = this.recommendations.features.find(
      (f) => routeKey(f.properties.route_id) === routeKey(proj.route_id),
    );
    const geoids = rec ? rec.properties.geoids ?? [] : [];
    const geoidSet = new Set(geoids);
    const servedFeatures = this.equity.features.filter((f) => geoidSet.has(f.properties.geoid));
    const servedFC: GeoJSON.FeatureCollection = {
      type: "FeatureCollection",
      features: servedFeatures as unknown as GeoJSON.Feature[],
    };
    (this.map.getSource("served") as GeoJSONSource).setData(servedFC);

    // Corridor geometry (LineString) — coverage-gap row has none.
    if (rec?.geometry) {
      (this.map.getSource("corridor") as GeoJSONSource).setData({
        type: "FeatureCollection",
        features: [rec as unknown as GeoJSON.Feature],
      });
    } else {
      (this.map.getSource("corridor") as GeoJSONSource).setData(emptyFC());
    }
  }

  private fitBoundary(): void {
    const bounds = new LngLatBounds();
    const fc = this.boundary;
    for (const feature of fc.features) {
      const geom = feature.geometry;
      if (!geom) continue;
      if (geom.type === "Polygon") {
        for (const ring of geom.coordinates as number[][][]) {
          for (const pt of ring) bounds.extend([pt[0]!, pt[1]!]);
        }
      } else if (geom.type === "MultiPolygon") {
        for (const poly of geom.coordinates as number[][][][]) {
          for (const ring of poly) for (const pt of ring) bounds.extend([pt[0]!, pt[1]!]);
        }
      }
    }
    if (!bounds.isEmpty()) {
      this.map!.fitBounds(bounds, { padding: 16, duration: 0 });
    }
  }
}

function emptyFC(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

export { REFERENCE_MULTIPLIER };
