/**
 * Sketch outlines — Rough.js wobble painted as SVG overlays on LARGE
 * chrome surfaces only. Deterministic (fixed seed per element) so the
 * wobble is stable across repaints and does not jump on every resize.
 *
 * SINGLE-TREATMENT RULE (Task 004): these hosts get exactly one outline
 * — this hand-drawn stroke — and must carry NO CSS border. Small
 * tiles/dense UI (stats/metrics, pills, nav, chips, empty states) use
 * CSS borders only and are never painted here.
 *
 * Large hosts: layer tabs group, legend, what-if controls, callout,
 * what-if minimap, table shell, export snapshot, drawer.
 * (Boot progress/stamp are small CSS-bordered UI + hand-drawn SVG route,
 * not Rough hosts.)
 *
 * Data layers (choropleth fills, legend ramps/swatches) are never sketched.
 */
import rough from "roughjs";

const INK = "#3a342c";
const INSET = 2;

type ElementWithObserver = HTMLElement & {
  __sketchResizeObserver?: ResizeObserver;
  __sketchSeed?: number;
};

/** Stable pseudo-random seed from class + index hint (no Math.random). */
function seedFor(el: HTMLElement): number {
  const key = `${el.className}|${el.id}|${el.textContent?.length ?? 0}`;
  let seed = 1;
  for (let i = 0; i < key.length; i++) {
    seed = (seed * 31 + key.charCodeAt(i)) >>> 0;
  }
  return (seed % 90000) + 1000;
}

/**
 * Paint a hand-drawn rectangle over `el` (inset `INSET`px). Toggle is a
 * no-op when the element has no size (hidden). Replaces any previous
 * sketch overlay on the same element.
 */
export function paintSketch(el: HTMLElement, seed?: number): void {
  // Anchor the absolute SVG overlay to this element (static hosts would
  // otherwise anchor to a distant positioned ancestor and misplace the
  // rectangle).
  const cs = getComputedStyle(el);
  if (cs.position === "static") el.style.position = "relative";

  const rect = el.getBoundingClientRect();
  const w = Math.round(rect.width);
  const h = Math.round(rect.height);
  if (w < 8 || h < 8) return;

  el.querySelectorAll(":scope > svg.dn-sketch").forEach((n) => n.remove());

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("dn-sketch");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");

  const rc = rough.svg(svg as unknown as SVGSVGElement);
  const s = seed ?? seedFor(el);

  try {
    const g = rc.rectangle(INSET, INSET, w - INSET * 2, h - INSET * 2, {
      stroke: INK,
      strokeWidth: 1.5,
      roughness: 1.4,
      bowing: 1.6,
      seed: s,
    });
    svg.appendChild(g as unknown as SVGElement);
  } catch {
    return;
  }

  // Position so the overlay sits inside the element without intercepting
  // pointer events (class .dn-sketch already disables pointer events).
  svg.style.position = "absolute";
  svg.style.inset = "0";
  el.insertBefore(svg, el.firstChild);

  // Sketch layers sit above plain backgrounds but below content is
  // handled in CSS (.dn-sketch has z-index 0, siblings z-index 1).
  const host = el as ElementWithObserver;
  if (host.__sketchResizeObserver) {
    host.__sketchResizeObserver.disconnect();
  }
  if (host.__sketchSeed === undefined) host.__sketchSeed = s;
  const activeSeed = host.__sketchSeed ?? s;
  const observer = new ResizeObserver(() => {
    // Cheap repaint guard: only repaint when size actually changed
    // (ResizeObserver already gives us that, but skip during the
    // drawer slide transition where getBoundingClientRect wobbles).
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) return;
    paintSketch(el, activeSeed);
  });
  host.__sketchResizeObserver = observer;
  observer.observe(el);
}

const DEFAULT_TARGETS =
  ".dn-layer-tabs, .dn-map-legend, .dn-whatif-controls, .dn-callout, " +
  ".dn-table-wrap, .dn-export-snapshot, .dn-drawer, .dn-minimap, " +
  ".dn-story, .dn-tour";

/** Paint every sketch target under `root`. Safe to call repeatedly. */
export function paintSketchBoxes(
  root: ParentNode = document,
  selector: string = DEFAULT_TARGETS,
): void {
  // Skip hidden (display:none) elements; they'll be painted when shown.
  const els = root.querySelectorAll<HTMLElement>(selector);
  requestAnimationFrame(() => {
    for (const el of els) {
      if (el.offsetParent === null && !el.classList.contains("dn-drawer")) {
        // Still paint drawers even when hidden via visibility/transform;
        // ResizeObserver will repaint on open.
        const style = getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden") continue;
      }
      paintSketch(el);
    }
  });
}
