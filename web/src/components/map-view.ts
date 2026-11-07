/**
 * Map explorer — MapLibre GL view. Full-bleed map with:
 *  - boundary outline + light fill
 *  - analysis fill layer toggleable via layer pills (Need / Access / Gap / Grade)
 *  - click-to-select block groups (drilldown)
 *  - adaptive legend overlay (sequential/diverging/grade)
 * Color palettes preserved from the Streamlit app (colorblind-safe).
 *
 * Paint/expression/legend helpers live in lib/map-style.ts (Task 010 split).
 */
import {
  LngLatBounds,
  Map as MapLibreMap,
  NavigationControl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  accessScoreForLayer,
  MAP_FILL_BASE,
  MAP_LINE,
  layerByKey,
  type LayerKey,
} from "../lib/colors";
import {
  BG,
  buildFillPaint,
  changedFilterExpression,
  effectiveConfig,
  equityWithAfter,
  prefersReducedMotion,
  renderLegendInto,
} from "../lib/map-style";
import { paintSketchBoxes } from "../lib/sketch";
import { actions, getState, subscribe } from "../state";
import type { EquityFeatureCollection } from "../types";

interface MapViewOptions {
  container: HTMLElement;
  equity: EquityFeatureCollection;
  boundary: GeoJSON.FeatureCollection;
  /** Per-block-group after-access gains (Before/After model). */
  gains?: Map<string, number>;
  onReady?: () => void;
}

export class MapView {
  private map: MapLibreMap;
  private equity: EquityFeatureCollection;
  private boundary: GeoJSON.FeatureCollection;
  private gains: Map<string, number>;
  private activeLayer: LayerKey;
  private activeMode: "today" | "after";
  private legendEl: HTMLElement;
  private tooltipEl: HTMLElement | null = null;
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
        this.showTooltip(geoid, f!.properties as never, e.point);
      }
    });

    this.map.on("mousemove", (e) => {
      const features = this.map.queryRenderedFeatures(e.point, {
        layers: ["analysis-fill"],
      });
      this.map.getCanvas().style.cursor = features.length ? "pointer" : "";
      const f = features[0];
      if (f?.properties?.geoid != null) {
        this.showTooltip(String(f.properties.geoid), f.properties as never, e.point, true);
      } else {
        this.hideTooltip();
      }
    });
    this.map.on("mouseout", () => this.hideTooltip());

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
      data: equityWithAfter(this.equity, this.gains) as unknown as GeoJSON.GeoJSON,
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
      paint: buildFillPaint(effectiveConfig(this.activeLayer, this.activeMode, this.gains, this.equity)),
    });
    // After-mode dimmer: non-changed polygons fade so the shift reads.
    this.map.addLayer({
      id: "after-dimmer",
      type: "fill",
      source: "equity",
      filter: changedFilterExpression(this.gains, false),
      paint: { "fill-color": "#f6f0e4", "fill-opacity": 0 },
    });
    // After-mode halo: strong outline on the changed polygons only.
    this.map.addLayer({
      id: "after-halo",
      type: "line",
      source: "equity",
      filter: changedFilterExpression(this.gains, true),
      paint: { "line-color": "#f0f7ff", "line-opacity": 0, "line-width": 3 },
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
    renderLegendInto(this.legendEl, this.activeLayer, this.activeMode, {
      gains: this.gains,
      equity: this.equity,
    });
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
      const paint = buildFillPaint(effectiveConfig(layer, this.activeMode, this.gains, this.equity));
      this.map.setPaintProperty("analysis-fill", "fill-color", paint["fill-color"]);
      this.map.setPaintProperty("analysis-fill", "fill-opacity", paint["fill-opacity"]);
    }
    renderLegendInto(this.legendEl, layer, this.activeMode, {
      gains: this.gains,
      equity: this.equity,
    });
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
    renderLegendInto(this.legendEl, this.activeLayer, mode, {
      gains: this.gains,
      equity: this.equity,
    });
    if (!this.map.isStyleLoaded()) return;
    // Halo + dimmer visibility (transition 150 ms, reduced-motion safe).
    const haloOp = mode === "after" ? 0.95 : 0;
    const dimOp = mode === "after" ? 0.52 : 0;
    try {
      this.map.setLayoutProperty("after-halo", "visibility", "visible");
      this.map.setLayoutProperty("after-dimmer", "visibility", "visible");
      this.map.setPaintProperty("after-halo", "line-opacity", haloOp);
      this.map.setPaintProperty("after-dimmer", "fill-opacity", dimOp);
    } catch {
      /* best-effort — legend/paint already applied */
    }
    const paint = buildFillPaint(effectiveConfig(this.activeLayer, mode, this.gains, this.equity));
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

  /**
   * Swap equity source (time-of-day refetch). Re-augments After fields
   * (gains are scenario-independent), refreshes paint + legend, keeps
   * the current viewport (no refit).
   */
  setEquity(next: EquityFeatureCollection): void {
    this.equity = next;
    if (!this.map.isStyleLoaded()) return;
    const src = this.map.getSource("equity") as unknown as {
      setData: (d: unknown) => void;
    };
    src.setData(equityWithAfter(this.equity, this.gains));
    const paint = buildFillPaint(effectiveConfig(this.activeLayer, this.activeMode, this.gains, this.equity));
    this.map.setPaintProperty("analysis-fill", "fill-color", paint["fill-color"]);
    renderLegendInto(this.legendEl, this.activeLayer, this.activeMode, {
      gains: this.gains,
      equity: this.equity,
    });
  }

  /**
   * Score tooltip (replaces the decorative isochrone circle). Plain-words
   * explanation of the active layer's score for the hovered/clicked block
   * group. No fake geography, no invented travel times.
   */
  showTooltip(geoid: string, props: {
    access_overall: number;
    jobs_access: number;
    healthcare_access: number;
    food_access: number;
    schools_access: number;
  }, point: { x: number; y: number }, hover = false): void {
    const layerLabel = layerByKey(this.activeLayer).label;
    const score = Math.min(
      Math.max(accessScoreForLayer(this.activeLayer, props), 0),
      1,
    );
    const verdict =
      score <= 0.05
        ? "the model finds almost nothing reachable by transit"
        : score >= 0.9
          ? "almost everything in the model is reachable by transit"
          : "about " +
            Math.round(score * 100) +
            "% of the model's reach";
    const text = `${layerLabel} ${score.toFixed(2)} — ${verdict}. Score is a 0–1 model value, not a travel time.`;
    const host = this.map.getContainer();
    if (!this.tooltipEl) {
      const el = document.createElement("div");
      el.className = "dn-tip";
      el.setAttribute("role", "status");
      host.appendChild(el);
      this.tooltipEl = el;
    }
    const el = this.tooltipEl;
    el.textContent = text;
    el.setAttribute("aria-label", `Block group ${geoid}: ${text}`);
    el.classList.toggle("is-hover", hover);
    el.style.left = `${point.x + 14}px`;
    el.style.top = `${point.y - 10}px`;
    el.hidden = false;
  }

  hideTooltip(): void {
    if (this.tooltipEl) this.tooltipEl.hidden = true;
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
