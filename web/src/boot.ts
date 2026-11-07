/**
 * Boot flow — app shell markup, animated loading UI, data loading/
 * validation, and mounting of the four functional areas. Split out of
 * main.ts during Task 010 modularization; main.ts now only calls boot().
 *
 * Sketch theme: header mark is the wobbly bus; the boot/loading state is
 * an animated bus-driving scene; view switches stagger in; chrome
 * surfaces get Rough.js sketch outlines.
 */
import { setWorkerUrl } from "maplibre-gl";
import { api } from "./api/client";
import { Drilldown } from "./components/drilldown";
import { ExportView } from "./components/export-view";
import { MapView } from "./components/map-view";
import { Onboarding, shouldShowTour } from "./components/onboarding";
import { StoryPanel } from "./components/story-panel";
import { WhatIfView } from "./components/whatif";
import { renderCitySummary, wireCopyLink } from "./header";
import { computeGainsByGeoid } from "./lib/before-after";
import { busMark, busSvg } from "./lib/mascot";
import { paintSketchBoxes } from "./lib/sketch";
import { pickStoryAnchor } from "./lib/story";
import { deepLinkFromLocation, syncUrl } from "./lib/url";
import { buildLayerTabs, updateLayerTabs } from "./layers";
import { SHELL_HTML } from "./shell";
import { buildNav, staggerView, updateNav, updateScrim } from "./nav";
import {
  buildBeforeAfter,
  buildTimeOfDay,
  refreshEquity,
  renderDeltaReadout,
  renderScenarioBanner,
  updateBeforeAfter,
  updateTimeOfDay,
} from "./scenario";
import { actions, getState, subscribe, type BeforeAfter } from "./state";
import { setDrilldown, setExportView, setMapView } from "./view-refs";
import type {
  EquityFeature,
  EquityFeatureCollection,
  RecommendationFeatureCollection,
  SensitivityRecord,
} from "./types";

interface DataBundle {
  equity: EquityFeatureCollection;
  boundary: GeoJSON.FeatureCollection;
  recommendations: RecommendationFeatureCollection;
  sensitivity: SensitivityRecord[];
}

const app = document.getElementById("app")!;

app.innerHTML = SHELL_HTML.replace("__BUS_MARK__", busMark({ size: 32 }));

const bootState = document.getElementById("boot-state")!;
const scrim = document.getElementById("scrim") as HTMLElement;

const BOOT_LABELS = [
  "Warming up the bus…",
  "Loading real equity data…",
  "Sketching the map…",
];

function driveDistance(): number {
  const scene = bootState.querySelector<HTMLElement>(".dn-boot-scene");
  if (!scene) return 260;
  return Math.max(scene.clientWidth - 64, 120);
}

/**
 * Render the animated boot scene: bus driving along a dashed route with
 * a progress bar. Extra `steps` append playful microcopy lines the app
 * used to show as plain text (same meaning, friendlier voice).
 */
function renderBootScene(label: string, opts: { isError?: boolean; stamp?: string } = {}): void {
  const isError = opts.isError ?? false;
  bootState.classList.toggle("dn-boot-error", isError);
  bootState.hidden = false;
  bootState.innerHTML = `
    <div class="dn-boot-scene" aria-hidden="true">
      <div class="dn-boot-track">
        <svg class="dn-boot-route" viewBox="0 0 300 24" preserveAspectRatio="none" focusable="false">
          <path d="M4 12 Q 25 5 52 12 T 104 12 T 156 12 T 208 12 T 260 12 T 296 12" />
        </svg>
        <span class="dn-boot-bus">${busSvg({ size: 60 })}</span>
      </div>
    </div>
    ${isError ? "" : '<div class="dn-boot-progress" aria-hidden="true"><span class="dn-boot-progress-bar"></span></div>'}
    <div class="dn-boot-stamp" role="note">${opts.stamp ?? "Wobbly but accurate."}</div>
    <div class="dn-boot-label">${label}</div>`;
  requestAnimationFrame(() => {
    const bus = bootState.querySelector<HTMLElement>(".dn-boot-bus");
    if (bus) bus.style.setProperty("--drive-distance", `${driveDistance()}px`);
  });
}

function setBoot(message: string, isError = false): void {
  renderBootScene(message, {
    isError,
    stamp: isError ? "Roadblock. Retry to roll again." : "Wobbly but accurate.",
    // stamp prop intentionally overrides default in error state
  });
  // Keep the original message semantics for the retry flow.
  void isError;
}

function setBootLabel(message: string): void {
  const label = bootState.querySelector(".dn-boot-label");
  if (label) label.textContent = message;
}

function boot(): void {
  // MapLibre's worker script lives in web/public/ (copied from the package).
  setWorkerUrl("/maplibre-gl-worker.mjs");
  // Deep-link restore (tolerant): unknown/malformed params keep defaults.
  actions.restore(deepLinkFromLocation());
  buildNav();
  buildLayerTabs();
  buildBeforeAfter();
  buildTimeOfDay();
  updateNav();
  updateLayerTabs();
  updateBeforeAfter();
  updateTimeOfDay();
  scrim.addEventListener("click", () => actions.selectGeoid(null));
  wireCopyLink();
  wireControlsToggle();

  // Stagger view content on switch; keep the shareable URL in sync.
  subscribe((next, prev) => {
    updateNav();
    updateLayerTabs();
    updateBeforeAfter();
    updateTimeOfDay();
    if (next.timeOfDay !== prev.timeOfDay) {
      void refreshEquity(next.timeOfDay);
    }
    if (next.view !== prev.view) staggerView(next.view);
    updateScrim();
    syncUrl(next);
  });

  // Show the branded animated boot immediately (before the first fetch).
  setBoot(BOOT_LABELS[1]!);

  const run = (): void => {
    loadData()
      .then(mount)
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : String(err);
        setBoot(`Could not load application data: ${msg}`, true);
        bootState.hidden = false;
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "dn-btn";
        retry.textContent = "Retry";
        retry.addEventListener("click", () => {
          bootState.hidden = true;
          run();
        });
        bootState.appendChild(retry);
        retry.focus();
      });
  };
  run();

  // Paint sketch outlines for the always-visible chrome.
  paintSketchBoxes();
  window.addEventListener("resize", () => paintSketchBoxes());
}

function wireControlsToggle(): void {
  const controls = document.getElementById("map-controls");
  const toggle = document.getElementById("ctl-toggle");
  if (!controls || !toggle) return;
  toggle.addEventListener("click", () => {
    const open = controls.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
  });
}

async function loadData(): Promise<DataBundle> {
  setBootLabel(BOOT_LABELS[0]!);
  const [equity, boundary, recommendations, sensitivity] = await Promise.all([
    api.equity(getState().timeOfDay),
    api.boundary(),
    api.recommendations(),
    api.sensitivity(),
  ]);
  const bundle: DataBundle = {
    equity,
    boundary: boundary as unknown as GeoJSON.FeatureCollection,
    recommendations,
    sensitivity,
  };
  validateBundle(bundle);
  return bundle;
}

function validateBundle(b: DataBundle): void {
  if (!b.equity.features.length) throw new Error("Equity dataset is empty");
  if (!b.boundary.features.length) throw new Error("Boundary dataset is empty");
  if (!b.sensitivity.length) throw new Error("Sensitivity dataset is empty");
}

function mount(bundle: DataBundle): void {
  setBootLabel(BOOT_LABELS[2]!);
  const equityById = new Map<string, EquityFeature>();
  for (const f of bundle.equity.features) equityById.set(f.properties.geoid, f);

  bootState.innerHTML = "";
  bootState.classList.remove("dn-boot-error");
  bootState.hidden = true;

  const gains = computeGainsByGeoid(
    bundle.recommendations.features.map((f) => f.properties),
    bundle.sensitivity,
  );

  const mapView = new MapView({
    container: document.getElementById("map")!,
    equity: bundle.equity,
    boundary: bundle.boundary,
    gains,
  });

  const drilldown = new Drilldown({
    container: document.getElementById("drilldown")!,
    equityById,
    recommendations: bundle.recommendations.features,
    gains,
  });

  const whatIf = new WhatIfView({
    container: document.getElementById("whatif")!,
    sensitivity: bundle.sensitivity,
    recommendations: bundle.recommendations,
    equity: bundle.equity,
    boundary: bundle.boundary,
  });

  const exportView = new ExportView({
    container: document.getElementById("export")!,
    equity: bundle.equity.features,
    equityById,
  });

  setMapView(mapView);
  setDrilldown(drilldown);
  setExportView(exportView);
  void renderScenarioBanner(getState().timeOfDay);
  renderDeltaReadout(bundle.equity, gains);

  let storyPanel: StoryPanel | null = null;
  const anchorFeature = pickStoryAnchor(bundle.equity);
  if (anchorFeature) {
    storyPanel = new StoryPanel({
      container: document.getElementById("story")!,
      feature: anchorFeature,
      recommendations: bundle.recommendations.features,
      sensitivity: bundle.sensitivity,
    });
  }

  // Keep instances referenced (hinted GC safety for map GL contexts).
  (app as unknown as { views?: unknown[] }).views = [
    mapView,
    drilldown,
    whatIf,
    exportView,
    storyPanel,
  ];

  renderCitySummary(bundle.equity);
  paintSketchBoxes();
  updateScrim();
  syncUrl(getState());

  // First-visit guided tour (dismissible, persisted, keyboard-operable).
  if (shouldShowTour()) {
    new Onboarding().show();
  }
}

export { boot };
