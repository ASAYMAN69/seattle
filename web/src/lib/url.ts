/**
 * Deep-links — `?geoid=<geoid>&layer=<layer>&view=<view>`.
 *
 * Parsing is tolerant: unknown/malformed params → graceful defaults
 * (map / need_index / no selection). Unknown geoids are kept as-is
 * (the drilldown's "not found" empty state handles them). Multi-value
 * params: first wins (URLSearchParams.get).
 */
import { LAYERS, type LayerKey } from "./colors";
import type { AppState, ViewKey } from "../state";

const VIEWS: ViewKey[] = ["map", "whatif", "export"];

export type DeepLinkState = Partial<Pick<AppState, "view" | "layer" | "selectedGeoid">>;

function parseView(raw: string | null): ViewKey | undefined {
  if (!raw) return undefined;
  const v = raw.trim().toLowerCase();
  return (VIEWS as string[]).includes(v) ? (v as ViewKey) : undefined;
}

function parseLayer(raw: string | null): LayerKey | undefined {
  if (!raw) return undefined;
  const keys = LAYERS.map((l) => l.key);
  return (keys as string[]).includes(raw) ? (raw as LayerKey) : undefined;
}

function parseGeoid(raw: string | null): string | undefined {
  if (!raw) return undefined;
  const g = raw.trim();
  return g ? g : undefined;
}

/** Parse a search string (with or without leading `?`) into deep-link state. */
export function parseDeepLink(search: string): DeepLinkState {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const out: DeepLinkState = {};
  const view = parseView(params.get("view"));
  if (view) out.view = view;
  const layer = parseLayer(params.get("layer"));
  if (layer) out.layer = layer;
  const geoid = parseGeoid(params.get("geoid"));
  if (geoid) out.selectedGeoid = geoid;
  return out;
}

/** Current location's deep-link state (for boot restoration). */
export function deepLinkFromLocation(): DeepLinkState {
  if (typeof window === "undefined") return {};
  return parseDeepLink(window.location.search);
}

/** Build `?geoid=…&layer=…&view=…` (defaults omitted for short links). */
export function buildDeepLink(state: AppState): string {
  const params = new URLSearchParams();
  if (state.selectedGeoid) params.set("geoid", state.selectedGeoid);
  if (state.layer !== "need_index") params.set("layer", state.layer);
  if (state.view !== "map") params.set("view", state.view);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

/** Sync the address bar (replaceState — no history spam). */
export function syncUrl(state: AppState): void {
  if (typeof window === "undefined") return;
  const next = `${window.location.pathname}${buildDeepLink(state)}${window.location.hash}`;
  const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (next !== current) {
    window.history.replaceState(window.history.state as unknown, "", next);
  }
}

/** Absolute share URL for the current state. */
export function shareUrl(state: AppState): string {
  if (typeof window === "undefined") return buildDeepLink(state);
  return `${window.location.origin}${window.location.pathname}${buildDeepLink(state)}${window.location.hash}`;
}
