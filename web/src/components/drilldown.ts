/**
 * Drilldown panel — Equity Report Card for the selected block group.
 * Slide-over on desktop; bottom sheet on narrow screens.
 * Shows identity, ACS stat tiles, grade chips, and top recommendations.
 * Sketch theme: ink-soft tiles, golden-rule headings, count-up stats,
 * and the wobbly bus in empty states. Data semantics unchanged.
 */
import { gradeColor } from "../lib/colors";
import { countUpTo } from "../lib/countup";
import { escapeHtml, fmtCurrency, fmtInt, fmtPct } from "../lib/format";
import { busSvg } from "../lib/mascot";
import { buildNeedsCard } from "../lib/needs";
import { paintSketchBoxes } from "../lib/sketch";
import { pickStoryAnchor } from "../lib/story";
import { actions, getState, subscribe } from "../state";
import type {
  EquityFeature,
  RecommendationFeature,
  RecommendationProperties,
} from "../types";

/** High-need/low-access threshold for the header count (single constant). */
export const HIGH_NEED_MIN = 0.4;
export const LOW_ACCESS_MAX = 0;

interface DrilldownOptions {
  container: HTMLElement;
  equityById: Map<string, EquityFeature>;
  recommendations: RecommendationFeature[];
  gains?: Map<string, number>;
}

interface RecommendationView {
  corridor: string;
  action: string;
  affected_pop: number | null;
}

export class Drilldown {
  private container: HTMLElement;
  private equityById: Map<string, EquityFeature>;
  private recommendations: RecommendationFeature[];
  private gains: Map<string, number>;
  private unsub: () => void;
  private closeBtn: HTMLButtonElement;
  private anchorGeoid: string | null;
  private returnFocus: HTMLElement | null = null;

  constructor(options: DrilldownOptions) {
    this.container = options.container;
    this.equityById = options.equityById;
    this.recommendations = options.recommendations;
    this.gains = options.gains ?? new Map();
    const anchor = pickStoryAnchor({
      type: "FeatureCollection",
      features: [...this.equityById.values()],
    });
    this.anchorGeoid = anchor ? String(anchor.properties.geoid) : null;

    this.container.classList.add("dn-drawer");
    this.container.setAttribute("role", "dialog");
    this.container.setAttribute("aria-label", "Block group equity report card");

    this.closeBtn = document.createElement("button");
    this.closeBtn.type = "button";
    this.closeBtn.className = "dn-drawer-close";
    this.closeBtn.setAttribute("aria-label", "Close report card");
    this.closeBtn.innerHTML =
      '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true" focusable="false"><path d="M4.5 4.5 L15.5 15.5 M15.5 4.5 L4.5 15.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>';
    this.closeBtn.addEventListener("click", () => actions.selectGeoid(null));
    this.container.appendChild(this.closeBtn);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && getState().selectedGeoid) {
        actions.selectGeoid(null);
      }
    });

    this.unsub = subscribe(() => this.render());
    this.render();
  }

  private render(): void {
    const geoid = getState().selectedGeoid;
    const scrim = document.getElementById("scrim");
    if (scrim) {
      const show = !!geoid && getState().view === "map";
      scrim.classList.toggle("is-visible", show);
      scrim.setAttribute("aria-hidden", show ? "false" : "true");
    }
    if (!geoid) {
      const wasOpen = !this.container.hidden;
      this.container.hidden = true;
      if (wasOpen) this.returnFocus?.focus?.();
      return;
    }
    const feature = this.equityById.get(geoid);
    this.container.hidden = false;

    const body = document.createElement("div");
    body.className = "dn-drawer-body";

    if (!feature) {
      body.innerHTML = `
        <div class="dn-empty">
          <span class="dn-mascot" aria-hidden="true">${busSvg({ size: 56 })}</span>
          <strong>Block group ${escapeHtml(geoid)} not found</strong>
          <p>It is not present in the equity data. Try selecting another block group.</p>
        </div>`;
      this.setContent(body);
      return;
    }

    const p = feature.properties;

    // Identity.
    const identity = document.createElement("div");
    identity.className = "dn-id";
    let idLine = `Block Group ${escapeHtml(p.geoid)}`;
    if (p.TRACTCE) {
      idLine += ` · Tract ${escapeHtml(p.TRACTCE)}`;
      if (p.BLKGRPCE) idLine += ` / BG ${escapeHtml(p.BLKGRPCE)}`;
    }
    identity.innerHTML = `<div class="dn-id-title">${idLine}</div>`;
    if (this.anchorGeoid && geoid === this.anchorGeoid) {
      const note = document.createElement("div");
      note.className = "dn-anchor-note";
      note.innerHTML = `<span class="dn-anchor-mascot" aria-hidden="true">${busSvg({ size: 28 })}</span><span>This is the index’s human story anchor — the neighborhood that shaped this map. Every number above and below is real prepared data.</span>`;
      identity.appendChild(note);
    }

    // ACS stat tiles (count-up on open; instant under reduced motion).
    const stats = document.createElement("div");
    stats.className = "dn-stat-grid";
    const tiles: Array<{
      label: string;
      value: number | null;
      format: (v: number | null | undefined) => string;
    }> = [
      { label: "Population", value: p.pop_total, format: fmtInt },
      { label: "Poverty rate", value: p.poverty_pct, format: fmtPct },
      { label: "Zero-car households", value: p.zero_car_pct, format: fmtPct },
      { label: "Median income", value: p.median_income, format: fmtCurrency },
    ];
    const valueEls: Array<{ el: HTMLElement; value: number; format: (v: number) => string }> = [];
    for (const t of tiles) {
      const tile = document.createElement("div");
      tile.className = "dn-stat";
      const valueEl = document.createElement("div");
      valueEl.className = "dn-stat-value";
      valueEl.textContent = t.format(t.value);
      tile.innerHTML = `<div class="dn-stat-label">${t.label}</div>`;
      tile.appendChild(valueEl);
      stats.appendChild(tile);
      if (typeof t.value === "number" && Number.isFinite(t.value)) {
        valueEls.push({ el: valueEl, value: t.value, format: t.format as (v: number) => string });
      }
    }

    // Grade chips.
    const grades: Array<[string, string | null]> = [
      ["Jobs", p.jobs_grade],
      ["Healthcare", p.healthcare_grade],
      ["Schools", p.schools_grade],
      ["Food", p.food_grade],
      ["Overall", p.grade],
    ];
    const chips = document.createElement("div");
    chips.className = "dn-chips";
    chips.setAttribute("aria-label", "Equity grades");
    for (const [label, grade] of grades) {
      const g = grade ? String(grade).trim().toUpperCase() : null;
      const chip = document.createElement("span");
      chip.className = "dn-chip";
      const color = gradeColor(g ?? "");
      chip.style.setProperty("--dn-grade-bg", color);
      chip.textContent = `${label} ${g ?? "—"}`;
      chips.appendChild(chip);
    }

    // After-mode gain (estimated) — only when recommendations ship.
    const gain = this.gains.get(geoid);
    if (getState().beforeAfter === "after" && gain != null && gain > 0) {
      const gainLine = document.createElement("div");
      gainLine.className = "dn-gain-note";
      gainLine.textContent = `If recommendations ship: +${(gain * 100).toFixed(1)} pp access (estimated, no re-routing).`;
      body.appendChild(gainLine);
    }

    // Top recommendations — never a bare empty card (see Task 008).
    const recs = this.topRecommendations(p.geoid);
    const recSection = document.createElement("div");
    recSection.className = "dn-recs";
    const recTitle = document.createElement("div");
    recTitle.className = "dn-section-label";
    recSection.appendChild(recTitle);

    if (recs.length === 0) {
      recTitle.textContent = "What this area needs";
      const needs = buildNeedsCard(p, feature, this.recommendations);
      recSection.appendChild(needs);
    } else {
      recTitle.textContent = "Top recommendations";
      const list = document.createElement("ul");
      list.className = "dn-rec-list";
      for (const rec of recs) {
        const li = document.createElement("li");
        const pop = rec.affected_pop != null ? `≈ ${fmtInt(rec.affected_pop)} residents affected` : "residents affected n/a";
        li.innerHTML = `<div class="dn-rec-corridor">${escapeHtml(rec.corridor)}</div>
          <div class="dn-rec-action">${escapeHtml(rec.action)}</div>
          <div class="dn-rec-pop">${escapeHtml(pop)}</div>`;
        list.appendChild(li);
      }
      recSection.appendChild(list);
    }

    body.append(identity, stats, chips, recSection);
    this.setContent(body);

    // Count-up after the drawer is in the DOM so textContent is readable.
    for (const { el, value, format } of valueEls) {
      countUpTo(el, value, { format });
    }
  }

  /** Swap the feature map (time-of-day refetch) and re-render. */
  setEquityById(next: Map<string, EquityFeature>): void {
    this.equityById = next;
    const anchor = pickStoryAnchor({
      type: "FeatureCollection",
      features: [...this.equityById.values()],
    });
    this.anchorGeoid = anchor ? String(anchor.properties.geoid) : null;
    this.render();
  }

  private topRecommendations(geoid: string): RecommendationView[] {
    const matched: Array<RecommendationView & { pop: number }> = [];
    for (const f of this.recommendations) {
      const props = f.properties as RecommendationProperties;
      if (props.geoids?.includes(geoid)) {
        matched.push({
          corridor: props.corridor,
          action: props.action,
          affected_pop: props.affected_pop ?? null,
          pop: props.affected_pop ?? 0,
        });
      }
    }
    matched.sort((a, b) => b.pop - a.pop);
    return matched.slice(0, 3);
  }

  private setContent(body: HTMLElement): void {
    const firstOpen = this.container.querySelector(".dn-drawer-body") == null;
    this.container.querySelector(".dn-drawer-body")?.remove();
    this.container.appendChild(body);
    // Drawer is a Rough.js host (single hand-drawn outline). Empty states
    // inside are CSS-dashed only — never painted.
    paintSketchBoxes(this.container, ".dn-drawer");
    if (firstOpen) {
      this.returnFocus = document.activeElement as HTMLElement | null;
    }
    this.closeBtn.focus();
  }

  destroy(): void {
    this.unsub();
  }
}
