/**
 * View navigation — nav buttons, active-view switching, scrim, and the
 * stagger-in animation on view change. Split out of main.ts during
 * Task 010 modularization.
 *
 * Element lookups are lazy: the shell markup is injected by boot() after
 * module evaluation, so the nav/scrim exist only once boot runs.
 */
import { paintSketchBoxes } from "./lib/sketch";
import { actions, getState, type ViewKey } from "./state";

let navEl: HTMLElement | null = null;
let scrimEl: HTMLElement | null = null;

function nav(): HTMLElement {
  if (!navEl) navEl = document.querySelector(".dn-nav");
  return navEl!;
}

function scrim(): HTMLElement {
  if (!scrimEl) scrimEl = document.getElementById("scrim");
  return scrimEl!;
}

export function buildNav(): void {
  for (const btn of nav().querySelectorAll<HTMLButtonElement>(".dn-navbtn")) {
    btn.addEventListener("click", () => {
      actions.setView(btn.dataset.view as ViewKey);
    });
  }
  nav().addEventListener("click", () => updateNav());
}

export function updateNav(): void {
  const view = getState().view;
  for (const btn of nav().querySelectorAll<HTMLButtonElement>(".dn-navbtn")) {
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

export function updateScrim(): void {
  const hasSelection = getState().selectedGeoid !== null && getState().view === "map";
  scrim().classList.toggle("is-visible", hasSelection);
  scrim().setAttribute("aria-hidden", hasSelection ? "false" : "true");
}

export function staggerView(view: ViewKey): void {
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
