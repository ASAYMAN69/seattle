/**
 * Header chrome — brand ribbon, city summary meta, count-up animation, and
 * copy-link wiring. Split out of main.ts during Task 010 modularization.
 */
import { api } from "./api/client";
import { shareUrl } from "./lib/url";
import { getState } from "./state";
import type { EquityFeatureCollection } from "./types";

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

export { renderCitySummary, wireCopyLink };
