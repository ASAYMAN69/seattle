/**
 * Shared live references to the mounted view instances (map / drilldown /
 * export). Owned by boot/mount; consumed by the scenario refresh path.
 * Split out of main.ts during Task 010 modularization so boot and scenario
 * don't tangle (no circular import).
 */
import type { Drilldown } from "./components/drilldown";
import type { ExportView } from "./components/export-view";
import type { MapView } from "./components/map-view";

let mapViewRef: MapView | null = null;
let drilldownRef: Drilldown | null = null;
let exportRef: ExportView | null = null;

export function setMapView(v: MapView | null): void {
  mapViewRef = v;
}

export function getMapView(): MapView | null {
  return mapViewRef;
}

export function setDrilldown(v: Drilldown | null): void {
  drilldownRef = v;
}

export function getDrilldown(): Drilldown | null {
  return drilldownRef;
}

export function setExportView(v: ExportView | null): void {
  exportRef = v;
}

export function getExportView(): ExportView | null {
  return exportRef;
}
