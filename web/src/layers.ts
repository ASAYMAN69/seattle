/**
 * Layer pill tabs (Need / Access / Gap / Grade) in the map controls.
 * Split out of main.ts during Task 010 modularization.
 *
 * Element lookups are lazy: the shell markup is injected by boot() after
 * module evaluation, so the tabs row exists only once boot runs.
 */
import { LAYERS, type LayerKey } from "./lib/colors";
import { actions, getState } from "./state";

let layerTabsEl: HTMLElement | null = null;

function layerTabs(): HTMLElement {
  if (!layerTabsEl) {
    layerTabsEl = document.querySelector(".dn-layer-tabs-row");
  }
  return layerTabsEl!;
}

export function buildLayerTabs(): void {
  const host = layerTabs();
  for (const layer of LAYERS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dn-layer-pill";
    btn.dataset.layer = layer.key;
    btn.textContent = layer.label;
    btn.addEventListener("click", () => actions.setLayer(layer.key));
    host.appendChild(btn);
  }
  host.addEventListener("click", () => updateLayerTabs());
}

export function updateLayerTabs(): void {
  const current = getState().layer;
  for (const btn of layerTabs().querySelectorAll<HTMLButtonElement>(".dn-layer-pill")) {
    const active = btn.dataset.layer === current;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", String(active));
  }
}
