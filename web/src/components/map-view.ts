/**
 * Map explorer — MapLibre GL view. Full-bleed map with:
 *  - boundary outline + light fill
 *  - analysis fill layer toggleable via layer pills (Need / Access / Gap / Grade)
 *  - click-to-select block groups (drilldown)
 *  - adaptive legend overlay (sequential/diverging/grade)
 * Color palettes preserved from the Streamlit app (colorblind-safe).
 */
import {
  LngLatBounds,
  Map as MapLibreMap,
  NavigationControl,
  type ExpressionSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  accessScoreForLayer,
  GRADE_COLORS,
  LAYERS,
  MAP_FILL_BASE,
  MAP_LINE,
  MISSING_FILL,
  layerByKey,
  type LayerConfig,
  type LayerKey,
} from "../lib/colors";
import { afterAccess } from "../lib/before-after";
import { paintSketchBoxes } from "../lib/sketch";
import rough from "roughjs";
import { actions, getState, subscribe } from "../state";
import type { EquityFeatureCollection } from "../types";

/* Paper-tinted map background; data layers (fills, selection) untouched. */
const BG = "#f2ece0";

interface MapViewOptions {
  container: HTMLElement;
  equity: EquityFeatureCollection;
  boundary: GeoJSON.FeatureCollection;
  /** Per-block-group after-access gains (Before/After model). */
  gains?: Map<string, number>;
  onReady?: () => void;
}

interface FillPaint {
  "fill-color": ExpressionSpecification;
  "fill-opacity": number;
}

export class MapView {
  private map: MapLibreMap;
  private equity: EquityFeatureCollection;
  private boundary: GeoJSON.FeatureCollection;
  private gains: Map<string, number>;
  private activeLayer: LayerKey;
  private activeMode: "today" | "after";
  private legendEl: HTMLElement;
  private pulseEl: HTMLElement | null = null;
  private pulseAnchor: { lng: number; lat: number } | null = null;
  private unsub: () => void;

  constructor(options: MapViewOptions) {
    this.equity = options.equity;
    this.boundary = options.boundary;
    this.gains = options.gains ?? new Map();
    this.activeLayer = getState().layer;
    this.activeMode = getState().beforeAfter;
    this.legendEl = document.createElement("div");
    this.legendEl.className = "dn-map-legend sketch-card";
    this.legendEl.setAttribute("role", "region");
    this.legendEl.setAttribute("aria-label", "Map legend");

    this.map = new MapLibreMap({
      container: options.container,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
            maxzoom: 19,
          },
        },
        layers: [
          { id: "background", type: "background", paint: { "background-color": BG } },
          {
            id: "osm",
            type: "raster",
            source: "osm",
            paint: { "raster-opacity": 0.6 },
          },
        ],
      },
      center: [-122.32, 47.6],
      zoom: 10.6,
      attributionControl: { compact: true },
    });

    this.map.addControl(new NavigationControl({ visualizePitch: false }), "top-right");

    this.map.on("load", () => {
      this.addSourcesAndLayers();
      void options.onReady?.();
    });

    this.map.on("click", (e) => {
      const features = this.map.queryRenderedFeatures(e.point, {
        layers: ["analysis-fill"],
      });
      const f = features[0];
      const geoid = f?.properties?.geoid != null ? String(f.properties.geoid) : null;
      if (geoid) {
        actions.selectGeoid(geoid);
        this.showPulse(geoid, f!.properties as never, { lng: e.lngLat.lng, lat: e.lngLat.lat });
      }
    });
    this.map.on("move", () => this.positionPulse());

    this.map.on("mousemove", (e) => {
      const features = this.map.queryRenderedFeatures(e.point, {
        layers: ["analysis-fill"],
      });
      this.map.getCanvas().style.cursor = features.length ? "pointer" : "";
    });

    options.container.after(this.legendEl);

    this.unsub = subscribe(() => {
      const s = getState();
      if (s.layer !== this.activeLayer) {
        this.setLayer(s.layer);
      }
      if (s.beforeAfter !== this.activeMode) {
        this.setMode(s.beforeAfter);
      }
      this.updateSelection(s.selectedGeoid);
    });
  }

  private addSourcesAndLayers(): void {
    this.map.addSource("boundary", {
      type: "geojson",
      data: this.boundary as unknown as GeoJSON.GeoJSON,
    });
    this.map.addSource("equity", {
      type: "geojson",
      data: this.equityWithAfter() as unknown as GeoJSON.GeoJSON,
    });

    this.map.addLayer({
      id: "boundary-fill",
      type: "fill",
      source: "boundary",
      paint: {
        "fill-color": MAP_FILL_BASE,
        "fill-opacity": 0.15,
      },
    });
    this.map.addLayer({
      id: "boundary-line",
      type: "line",
      source: "boundary",
      paint: {
        "line-color": MAP_LINE,
        "line-width": 2,
        "line-opacity": 0.9,
      },
    });
    this.map.addLayer({
      id: "analysis-fill",
      type: "fill",
      source: "equity",
      paint: this.fillPaint(this.activeLayer),
    });
    this.map.addLayer({
      id: "analysis-line",
      type: "line",
      source: "equity",
      paint: {
        "line-color": MAP_LINE,
        "line-width": 0.5,
        "line-opacity": 0.4,
      },
    });
    this.map.addLayer({
      id: "selection-line",
      type: "line",
      source: "equity",
      filter: ["==", ["get", "geoid"], ""],
      paint: {
        "line-color": "#0f172a",
        "line-width": 2.5,
        "line-opacity": 0.95,
      },
    });

    this.fitToData();
    this.renderLegend(this.activeLayer);
  }

  private fitToData(): void {
    const bounds = new LngLatBounds();
    for (const feature of this.equity.features) {
      const geom = feature.geometry;
      if (!geom) continue;
      if (geom.type === "Polygon") {
        for (const ring of geom.coordinates as number[][][]) {
          for (const pt of ring) bounds.extend([pt[0]!, pt[1]!]);
        }
      } else if (geom.type === "MultiPolygon") {
        for (const poly of geom.coordinates as number[][][][]) {
          for (const ring of poly) {
            for (const pt of ring) bounds.extend([pt[0]!, pt[1]!]);
          }
        }
      }
    }
    if (!bounds.isEmpty()) {
      this.map.fitBounds(bounds, { padding: 24, duration: 0 });
    }
  }

  setLayer(layer: LayerKey): void {
    this.activeLayer = layer;
    if (this.map.isStyleLoaded()) {
      const paint = this.fillPaint(layer, this.activeMode);
      this.map.setPaintProperty("analysis-fill", "fill-color", paint["fill-color"]);
      this.map.setPaintProperty("analysis-fill", "fill-opacity", paint["fill-opacity"]);
    }
    this.renderLegend(layer, this.activeMode);
  }

  /**
   * Before ("today") / After ("after") morph. After-data comes from the
   * precomputed gains (equity + sensitivity — no re-routing). Only gap and
   * overall-access recolor; need/grade/category layers are mode-invariant
   * (see legend note). A short opacity pulse bridges the expression
   * switch (MapLibre color expressions snap without a transition).
   */
  setMode(mode: "today" | "after"): void {
    this.activeMode = mode;
    // Legend is style-independent (always render — mirrors setLayer).
    this.renderLegend(this.activeLayer, mode);
    if (!this.map.isStyleLoaded()) return;
    const paint = this.fillPaint(this.activeLayer, mode);
    if (!prefersReducedMotion()) {
      this.map.setPaintProperty("analysis-fill", "fill-opacity", 0.35);
      window.setTimeout(() => {
        this.map.setPaintProperty("analysis-fill", "fill-color", paint["fill-color"]);
        this.map.setPaintProperty("analysis-fill", "fill-opacity", paint["fill-opacity"]);
      }, 180);
    } else {
      this.map.setPaintProperty("analysis-fill", "fill-color", paint["fill-color"]);
      this.map.setPaintProperty("analysis-fill", "fill-opacity", paint["fill-opacity"]);
    }
  }

  updateSelection(geoid: string | null): void {
    if (!this.map.isStyleLoaded()) return;
    this.map.setFilter("selection-line", ["==", ["get", "geoid"], geoid ?? ""]);
  }

  private fillPaint(layer: LayerKey, mode: "today" | "after" = this.activeMode): FillPaint {
    const cfg = this.effectiveConfig(layer, mode);
    return {
      "fill-color": buildColorExpression(cfg),
      "fill-opacity": cfg.kind === "grade" ? 0.7 : 0.65,
    };
  }

  /** Column swapped to its `*_after` twin in After mode (gap/access only). */
  private effectiveConfig(layer: LayerKey, mode: "today" | "after"): LayerConfig {
    const cfg = layerByKey(layer);
    if (mode !== "after") return cfg;
    if (cfg.column === "gap") return { ...cfg, column: "gap_after" };
    if (cfg.column === "access_overall") return { ...cfg, column: "access_after" };
    return cfg;
  }

  /** Equity features augmented with `gap_after` / `access_after` (clone). */
  private equityWithAfter(): EquityFeatureCollection {
    if (this.gains.size === 0) return this.equity;
    return {
      type: "FeatureCollection",
      features: this.equity.features.map((f) => {
        const p = f.properties;
        const accessAfter = afterAccess(p.access_overall, this.gains.get(String(p.geoid)));
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

  private renderLegend(key: LayerKey, mode: "today" | "after" = this.activeMode): void {
    const cfg = this.effectiveConfig(key, mode);
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
        ? `${cfg.legend}. After = estimated access + corridor gain (no re-routing).`
        : cfg.legend;
    inner.appendChild(note);

    this.legendEl.replaceChildren(inner);
    paintSketchBoxes(this.legendEl);
  }

  /**
   * Isochrone pulse — illustrative coverage metaphor (NOT GIS). Draws a
   * wobbly Rough.js circle at the clicked block group whose radius
   * scales with the active access-layer score. Caption always says
   * "not a true isochrone".
   */
  showPulse(geoid: string | null, props: {
    access_overall: number;
    jobs_access: number;
    healthcare_access: number;
    food_access: number;
    schools_access: number;
  } | null, lngLat: { lng: number; lat: number } | null): void {
    this.pulseEl?.remove();
    this.pulseEl = null;
    this.pulseAnchor = null;
    if (!geoid || !props || !lngLat) return;
    const score = Math.min(
      Math.max(accessScoreForLayer(this.activeLayer, props), 0),
      1,
    );
    this.pulseAnchor = lngLat;
    const host = this.map.getContainer();
    const el = document.createElement("div");
    el.className = "dn-pulse";
    el.setAttribute("role", "img");
    const radius = 60 + score * 160;
    const size = Math.round(radius * 2);
    el.style.width = `${size}px`;
    el.style.height = `${size}px`;
    el.innerHTML =
      `<span class="dn-pulse-caption">Illustrative coverage — sketch, not a true isochrone. Taller score, wider pulse.</span>` +
      `<svg class="dn-pulse-art" viewBox="0 0 100 100" aria-hidden="true" focusable="false"></svg>`;
    host.appendChild(el);
    // Paint the wobbly circle.
    paintPulseCircle(el.querySelector("svg") as unknown as SVGSVGElement, geoid);
    this.pulseEl = el;
    this.positionPulse();
    // Re-trigger the one-shot scale-in.
    el.classList.remove("dn-pulse-enter");
    void el.offsetWidth;
    el.classList.add("dn-pulse-enter");
  }

  private positionPulse(): void {
    if (!this.pulseEl || !this.pulseAnchor) return;
    const pt = this.map.project([this.pulseAnchor.lng, this.pulseAnchor.lat]);
    this.pulseEl.style.left = `${pt.x - this.pulseEl.offsetWidth / 2}px`;
    this.pulseEl.style.top = `${pt.y - this.pulseEl.offsetHeight / 2}px`;
  }

  destroy(): void {
    this.unsub();
    this.legendEl.remove();
    this.map.remove();
  }

  getMap(): MapLibreMap {
    return this.map;
  }
}

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

function paintPulseCircle(svg: SVGSVGElement, geoid: string): void {
  try {
    const rc = rough.svg(svg);
    let seed = 1;
    for (let i = 0; i < geoid.length; i++) seed = (seed * 31 + geoid.charCodeAt(i)) >>> 0;
    const g = rc.circle(50, 50, 92, {
      stroke: "#c4622d",
      strokeWidth: 1.8,
      roughness: 1.6,
      bowing: 2.2,
      seed: (seed % 90000) + 1000,
      fill: "rgba(196, 98, 45, 0.12)",
      fillStyle: "solid",
    });
    svg.appendChild(g as unknown as SVGElement);
  } catch {
    /* decorative only — never break the map */
  }
}

function gradientCss(ramp: string[]): string {
  const step = 100 / (ramp.length - 1);
  const stops = ramp.map((c, i) => `${c} ${Math.round(i * step)}%`);
  return `linear-gradient(to right, ${stops.join(", ")})`;
}

function buildColorExpression(cfg: LayerConfig): ExpressionSpecification {
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
