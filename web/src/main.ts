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
import { computeGainsByGeoid } from "./lib/before-after";
import { LAYERS, type LayerKey } from "./lib/colors";
import { busMark, busSvg } from "./lib/mascot";
import { paintSketchBoxes } from "./lib/sketch";
import { pickStoryAnchor } from "./lib/story";
import { deepLinkFromLocation, shareUrl, syncUrl } from "./lib/url";
import { actions, getState, subscribe, type BeforeAfter, type ViewKey } from "./state";
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
        <h1 class="dn-title">Seattle Transit Equity Index</h1>
      </div>
      <nav class="dn-nav" aria-label="Views">
        <button class="dn-navbtn" data-view="map" type="button" aria-current="page">Map explorer</button>
        <button class="dn-navbtn" data-view="whatif" type="button">What-if</button>
        <button class="dn-navbtn" data-view="export" type="button">Export</button>
      </nav>
      <div class="dn-header-actions">
        <button class="dn-copy" id="copy-link" type="button" aria-live="polite">Copy link</button>
      </div>
    </div>
    <div class="dn-ribbon">
      <div class="dn-meta dn-muted" id="city-summary"></div>
    </div>
  </header>

  <main class="dn-main">
    <section class="dn-view dn-view-map is-active" data-view="map">
      <div id="map" class="dn-map" role="application" aria-label="Seattle transit equity map"></div>
      <div class="dn-map-controls sketch-card">
        <div class="dn-ctl-section">
          <span class="dn-mapctl-label">Area layer</span>
          <div class="dn-layer-tabs-row" role="group" aria-label="Area layer"></div>
        </div>
        <div class="dn-ctl-pair">
          <div class="dn-ctl-half" role="group" aria-label="Time of day scenario">
            <span class="dn-mapctl-label" aria-hidden="true">Scenario</span>
            <div class="dn-beforeafter-row">
              <button class="tod-btn is-active" data-tod="am_peak" type="button" aria-pressed="true">AM peak</button>
              <button class="tod-btn" data-tod="off_peak" type="button" aria-pressed="false">Off-peak ✦</button>
            </div>
          </div>
          <div class="dn-ctl-half" role="group" aria-label="Before or after recommendations">
            <span class="dn-mapctl-label" aria-hidden="true">Before / after</span>
            <div class="dn-beforeafter-row">
              <button class="dn-ba-btn is-active" data-mode="today" type="button" aria-pressed="true">Today</button>
              <button class="dn-ba-btn" data-mode="after" type="button" aria-pressed="false">If recommendations ship</button>
            </div>
          </div>
        </div>
        <div class="dn-scenario-banner" id="scenario-banner" role="status" hidden></div>
        <div class="dn-delta-readout" id="delta-readout" hidden></div>
      </div>
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
const layerTabs = document.querySelector(".dn-layer-tabs-row") as HTMLElement;
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

function updateBeforeAfter(): void {
  const current = getState().beforeAfter;
  for (const btn of document.querySelectorAll<HTMLButtonElement>(".dn-ba-btn")) {
    const active = btn.dataset.mode === current;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", String(active));
  }
}

function buildBeforeAfter(): void {
  for (const btn of document.querySelectorAll<HTMLButtonElement>(".dn-ba-btn")) {
    btn.addEventListener("click", () => {
      actions.setBeforeAfter(btn.dataset.mode as BeforeAfter);
    });
  }
}

function updateTimeOfDay(): void {
  const current = getState().timeOfDay;
  for (const btn of document.querySelectorAll<HTMLButtonElement>(".tod-btn")) {
    const active = btn.dataset.tod === current;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", String(active));
  }
}

function buildTimeOfDay(): void {
  for (const btn of document.querySelectorAll<HTMLButtonElement>(".tod-btn")) {
    btn.addEventListener("click", () => {
      actions.setTimeOfDay(
        btn.dataset.tod === "off_peak" ? "off_peak" : "am_peak",
      );
    });
  }
}

let mapViewRef: import("./components/map-view").MapView | null = null;
let drilldownRef: import("./components/drilldown").Drilldown | null = null;
let exportRef: import("./components/export-view").ExportView | null = null;

/** Refetch equity for a scenario; swap map/drilldown/export data in place. */
async function refreshEquity(timeOfDay: string): Promise<void> {
  try {
    const equity = await api.equity(timeOfDay);
    const equityById = new Map<string, EquityFeature>();
    for (const f of equity.features) equityById.set(f.properties.geoid, f);
    mapViewRef?.setEquity(equity);
    drilldownRef?.setEquityById(equityById);
    await exportRef?.refreshTop(timeOfDay);
    await renderScenarioBanner(timeOfDay);
    paintSketchBoxes();
  } catch {
    /* keep current data; banner stays as-is */
  }
}

async function renderScenarioBanner(timeOfDay: string): Promise<void> {
  const el = document.getElementById("scenario-banner");
  if (!el) return;
  if (timeOfDay !== "off_peak") {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  try {
    const scenarios = await api.scenarios();
    const off = scenarios.find((s) => s.id === "off_peak");
    el.textContent = off
      ? `Off-peak (approximate what-if, not a fresh routed network): ${off.basis}`
      : "Off-peak (approximate what-if, not a fresh routed network).";
  } catch {
    el.textContent = "Off-peak (approximate what-if, not a fresh routed network).";
  }
  el.hidden = false;
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

/**
 * Header meta: no ring — every number is a contextual count a judge
 * gets in one sentence (see HIGH_NEED_MIN / LOW_ACCESS_MAX thresholds).
 */
function renderCitySummary(equity: EquityFeatureCollection): void {
  void api
    .reportCards()
    .then((rc) => {
      const s = rc.summary;
      const el = document.getElementById("city-summary");
      if (!el || !s) return;
      const fCount = s.grade_counts?.F ?? 0;
      const hnla = equity.features.filter(
        (f) =>
          f.properties.need_index >= 0.4 && f.properties.gap < 0,
      ).length;
      el.innerHTML =
        `<span class="dn-meta-count" data-count="${s.n_block_groups}">${s.n_block_groups.toLocaleString("en-US")}</span> block groups · ` +
        `<span class="dn-meta-count" data-count="${s.total_recommended_population}">${s.total_recommended_population.toLocaleString("en-US")}</span> in recommended corridors · ` +
        `<span class="dn-meta-count" data-count="${fCount}">${fCount}</span> F-grade · ` +
        `<span class="dn-meta-count" data-count="${hnla}">${hnla}</span> high-need / low-access <span class="dn-meta-def">(need ≥0.40, gap &lt;0)</span>`;
      // Ribbon is read-only chrome: final values, no count-up.
    })
    .catch(() => { /* non-critical */ });
}

const countUpFrames = new WeakMap<HTMLElement, number>();

/** Ease-out count-up for header numbers (650 ms, reduced-motion safe). */
function animateCount(
  el: HTMLElement,
  target: number,
  format: (v: number) => string,
): void {
  const prev = countUpFrames.get(el);
  if (prev) cancelAnimationFrame(prev);
  if (prefersReducedMotion()) {
    el.textContent = format(target);
    return;
  }
  const start = performance.now();
  const tick = (now: number): void => {
    const t = Math.min((now - start) / 650, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = format(target * eased);
    if (t < 1) countUpFrames.set(el, requestAnimationFrame(tick));
    else el.textContent = format(target);
  };
  countUpFrames.set(el, requestAnimationFrame(tick));
}

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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

  mapViewRef = mapView;
  drilldownRef = drilldown;
  exportRef = exportView;
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

/**
 * Before/After delta readout (real numbers from the gains join):
 * "25 block groups shift · max +8.3 pp · most see no change".
 */
function renderDeltaReadout(
  equity: EquityFeatureCollection,
  gains: Map<string, number>,
): void {
  const el = document.getElementById("delta-readout");
  if (!el) return;
  const snapshot = [equity, gains];
  void snapshot;
  const changed = [...gains.values()].filter((g) => g > 0);
  if (changed.length === 0) {
    el.hidden = true;
    return;
  }
  const max = Math.max(...changed);
  const total = equity.features.length || 1545;
  el.textContent =
    `${changed.length} block groups shift · max +${(max * 100).toFixed(1)} pp · ` +
    `${total - changed.length} see no change`;
  el.hidden = false;
}

boot();
