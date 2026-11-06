/**
 * Seattle Transit Equity Index — SPA entry.
 * Bootstraps the shell (header/nav), loads the API data, and mounts the
 * four functional areas: Map explorer (+ drilldown), What-if, and Export.
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
import { LAYERS, type LayerKey } from "./lib/colors";
import { busMark, busSvg } from "./lib/mascot";
import { paintSketchBoxes } from "./lib/sketch";
import { pickStoryAnchor } from "./lib/story";
import { deepLinkFromLocation, shareUrl, syncUrl } from "./lib/url";
import { actions, getState, subscribe, type ViewKey } from "./state";
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

app.innerHTML = `
  <header class="dn-header">
    <div class="dn-header-inner">
      <div class="dn-brand">
        <span class="dn-brand-mark" aria-hidden="true">${busMark({ size: 32 })}</span>
        <div>
          <h1 class="dn-title">Seattle Transit Equity Index</h1>
          <p class="dn-tagline">Who in Seattle is disconnected from opportunity?</p>
        </div>
      </div>
      <div class="dn-header-actions">
        <div class="dn-meta dn-muted" id="city-summary"></div>
        <button class="dn-copy" id="copy-link" type="button" aria-live="polite">Copy link</button>
      </div>
    </div>
  </header>

  <nav class="dn-nav" aria-label="Views">
    <button class="dn-navbtn" data-view="map" type="button" aria-current="page">Map explorer</button>
    <button class="dn-navbtn" data-view="whatif" type="button">What-if</button>
    <button class="dn-navbtn" data-view="export" type="button">Export</button>
  </nav>

  <main class="dn-main">
    <section class="dn-view dn-view-map is-active" data-view="map">
      <div id="map" class="dn-map" role="application" aria-label="Seattle transit equity map"></div>
      <div class="dn-layer-tabs sketch-card" role="group" aria-label="Analysis layer"></div>
      <div id="story"></div>
      <div id="scrim" class="dn-scrim" aria-hidden="true"></div>
      <div id="drilldown"></div>
    </section>
    <section class="dn-view" data-view="whatif">
      <div id="whatif" class="dn-view-inner"></div>
    </section>
    <section class="dn-view" data-view="export">
      <div id="export" class="dn-view-inner"></div>
    </section>
    <div id="boot-state" class="dn-boot" role="status"></div>
  </main>`;

const bootState = document.getElementById("boot-state")!;
const nav = document.querySelector(".dn-nav")!;
const layerTabs = document.querySelector(".dn-layer-tabs") as HTMLElement;
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
  updateNav();
  updateLayerTabs();
  scrim.addEventListener("click", () => actions.selectGeoid(null));
  wireCopyLink();

  // Stagger view content on switch; keep the shareable URL in sync.
  subscribe((next, prev) => {
    updateNav();
    updateLayerTabs();
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

function wireCopyLink(): void {
  const btn = document.getElementById("copy-link") as HTMLButtonElement | null;
  if (!btn) return;
  btn.addEventListener("click", () => {
    const url = shareUrl(getState());
    const done = (): void => {
      btn.textContent = "Copied!";
      btn.classList.add("is-copied");
      window.setTimeout(() => {
        btn.textContent = "Copy link";
        btn.classList.remove("is-copied");
      }, 1400);
    };
    const fallback = (): void => {
      // execCommand fallback for non-secure contexts.
      const ta = document.createElement("textarea");
      ta.value = url;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand("copy");
      } catch {
        /* clipboard unavailable — URL is still in the address bar */
      }
      ta.remove();
      done();
    };
    if (navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(url).then(done).catch(fallback);
    } else {
      fallback();
    }
  });
}

function buildLayerTabs(): void {
  for (const layer of LAYERS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dn-layer-pill";
    btn.dataset.layer = layer.key;
    btn.textContent = layer.label;
    btn.addEventListener("click", () => actions.setLayer(layer.key));
    layerTabs.appendChild(btn);
  }
  layerTabs.addEventListener("click", () => updateLayerTabs());
}

function updateLayerTabs(): void {
  const current = getState().layer;
  for (const btn of layerTabs.querySelectorAll<HTMLButtonElement>(".dn-layer-pill")) {
    const active = btn.dataset.layer === current;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", String(active));
  }
}

function buildNav(): void {
  for (const btn of nav.querySelectorAll<HTMLButtonElement>(".dn-navbtn")) {
    btn.addEventListener("click", () => {
      actions.setView(btn.dataset.view as ViewKey);
    });
  }
  nav.addEventListener("click", () => updateNav());
}

function updateNav(): void {
  const view = getState().view;
  for (const btn of nav.querySelectorAll<HTMLButtonElement>(".dn-navbtn")) {
    const active = btn.dataset.view === view;
    btn.classList.toggle("is-active", active);
    if (active) btn.setAttribute("aria-current", "page");
    else btn.removeAttribute("aria-current");
  }
  for (const section of document.querySelectorAll<HTMLElement>(".dn-view")) {
    const active = section.dataset.view === view;
    section.classList.toggle("is-active", active);
  }
  // Sketch chrome inside the newly visible view needs painting
  // (elements that were display:none had no size at first paint).
  paintSketchBoxes();
  updateScrim();
}

function updateScrim(): void {
  const hasSelection = getState().selectedGeoid !== null && getState().view === "map";
  scrim.classList.toggle("is-visible", hasSelection);
  scrim.setAttribute("aria-hidden", hasSelection ? "false" : "true");
}

function staggerView(view: ViewKey): void {
  const section = document.querySelector<HTMLElement>(`.dn-view[data-view="${view}"]`);
  if (!section) return;
  const inner = section.querySelector<HTMLElement>(".dn-view-inner");
  const targets = inner ? Array.from(inner.children) : Array.from(section.children);
  targets.forEach((el, i) => {
    (el as HTMLElement).style.setProperty("--i", String(i));
    el.classList.remove("dn-stagger");
    // Force reflow so re-adding the class re-triggers the animation.
    void (el as HTMLElement).offsetWidth;
    el.classList.add("dn-stagger");
  });
}

async function loadData(): Promise<DataBundle> {
  setBootLabel(BOOT_LABELS[0]!);
  const [equity, boundary, recommendations, sensitivity] = await Promise.all([
    api.equity(),
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

function renderCitySummary(): void {
  void api
    .reportCards()
    .then((rc) => {
      const s = rc.summary;
      const el = document.getElementById("city-summary");
      if (el && s) {
        el.textContent = `${s.n_block_groups.toLocaleString("en-US")} block groups · ` +
          `${s.total_recommended_population.toLocaleString("en-US")} residents in recommended corridors`;
      }
    })
    .catch(() => { /* non-critical */ });
}

function mount(bundle: DataBundle): void {
  setBootLabel(BOOT_LABELS[2]!);
  const equityById = new Map<string, EquityFeature>();
  for (const f of bundle.equity.features) equityById.set(f.properties.geoid, f);

  bootState.innerHTML = "";
  bootState.classList.remove("dn-boot-error");
  bootState.hidden = true;

  const mapView = new MapView({
    container: document.getElementById("map")!,
    equity: bundle.equity,
    boundary: bundle.boundary,
  });

  const drilldown = new Drilldown({
    container: document.getElementById("drilldown")!,
    equityById,
    recommendations: bundle.recommendations.features,
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

  let storyPanel: StoryPanel | null = null;
  const anchorFeature = pickStoryAnchor(bundle.equity);
  if (anchorFeature) {
    storyPanel = new StoryPanel({
      container: document.getElementById("story")!,
      feature: anchorFeature,
      recommendations: bundle.recommendations.features,
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

  renderCitySummary();
  paintSketchBoxes();
  updateScrim();
  syncUrl(getState());

  // First-visit guided tour (dismissible, persisted, keyboard-operable).
  if (shouldShowTour()) {
    new Onboarding().show();
  }
}

boot();
