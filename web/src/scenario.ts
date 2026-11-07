/**
 * Scenario controls — time-of-day toggle, Before/After mode buttons, the
 * scenario banner, the equity refetch on scenario change, and the Before/
 * After delta readout. Split out of main.ts during Task 010 modularization.
 */
import { api } from "./api/client";
import { paintSketchBoxes } from "./lib/sketch";
import { actions, getState, type BeforeAfter } from "./state";
import type { EquityFeature, EquityFeatureCollection } from "./types";
import { getDrilldown, getExportView, getMapView } from "./view-refs";

export function updateBeforeAfter(): void {
  const current = getState().beforeAfter;
  for (const btn of document.querySelectorAll<HTMLButtonElement>(".dn-ba-btn")) {
    const active = btn.dataset.mode === current;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", String(active));
  }
}

export function buildBeforeAfter(): void {
  for (const btn of document.querySelectorAll<HTMLButtonElement>(".dn-ba-btn")) {
    btn.addEventListener("click", () => {
      actions.setBeforeAfter(btn.dataset.mode as BeforeAfter);
    });
  }
}

export function updateTimeOfDay(): void {
  const current = getState().timeOfDay;
  for (const btn of document.querySelectorAll<HTMLButtonElement>(".tod-btn")) {
    const active = btn.dataset.tod === current;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", String(active));
  }
}

export function buildTimeOfDay(): void {
  for (const btn of document.querySelectorAll<HTMLButtonElement>(".tod-btn")) {
    btn.addEventListener("click", () => {
      actions.setTimeOfDay(
        btn.dataset.tod === "off_peak" ? "off_peak" : "am_peak",
      );
    });
  }
}

/** Refetch equity for a scenario; swap map/drilldown/export data in place. */
export async function refreshEquity(timeOfDay: string): Promise<void> {
  try {
    const equity = await api.equity(timeOfDay);
    const equityById = new Map<string, EquityFeature>();
    for (const f of equity.features) equityById.set(f.properties.geoid, f);
    getMapView()?.setEquity(equity);
    getDrilldown()?.setEquityById(equityById);
    await getExportView()?.refreshTop(timeOfDay);
    await renderScenarioBanner(timeOfDay);
    paintSketchBoxes();
  } catch {
    /* keep current data; banner stays as-is */
  }
}

export async function renderScenarioBanner(timeOfDay: string): Promise<void> {
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

/**
 * Before/After delta readout (real numbers from the gains join):
 * "25 block groups shift · max +8.3 pp · most see no change".
 */
export function renderDeltaReadout(
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
