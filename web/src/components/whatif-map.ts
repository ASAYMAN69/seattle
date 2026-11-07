/**
 * What-if highlight map — minimap widget showing the selected corridor and
 * the block groups it serves. Split out of components/whatif.ts during
 * Task 010 modularization. Rendering semantics unchanged.
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
import { routeKey, type WhatIfProjection } from "../lib/interpolation";
import type {
  EquityFeatureCollection,
  RecommendationFeatureCollection,
} from "../types";

/* Paper-tinted map background to sit inside the sketch theme.
 * Data layers (served/corridor paints) are untouched. */
const BG = "#f2ece0";

export class WhatIfMapView {
  private container: HTMLElement;
  private boundary: GeoJSON.FeatureCollection;
  private equity: EquityFeatureCollection;
  private recommendations: RecommendationFeatureCollection;
  private map: MapLibreMap | null = null;
  private latestProj: WhatIfProjection | null = null;

  constructor(options: {
    container: HTMLElement;
    boundary: GeoJSON.FeatureCollection;
    equity: EquityFeatureCollection;
    recommendations: RecommendationFeatureCollection;
  }) {
    this.container = options.container;
    this.boundary = options.boundary;
    this.equity = options.equity;
    this.recommendations = options.recommendations;
  }

  /** Render the projection on the minimap (creates the map on first call). */
  update(proj: WhatIfProjection): void {
    if (this.map) {
      this.updateMapSources(proj);
      return;
    }

    this.latestProj = proj;
    this.map = new MapLibreMap({
      container: this.container,
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
      this.updateMapSources(this.latestProj!);
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
