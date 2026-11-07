/**
 * Export view charts — pure SVG builders (city-wide grade distribution and
 * top-25 need-vs-access scatter). Split out of components/export-view.ts
 * during Task 010 modularization. Rendering semantics unchanged.
 */
import { GRADE_COLORS, gradeColor } from "../lib/colors";
import type { EquityFeature, TopUnderservedRow } from "../types";

/** City-wide grade distribution (bar chart), weighted by block-group count. */
export function renderGradeChart(el: HTMLElement, equity: EquityFeature[]): void {
  const grades = ["A", "B", "C", "D", "F"];
  const counts = new Map<string, number>();
  for (const f of equity) {
    const g = String(f.properties.grade ?? "").trim().toUpperCase() || "—";
    counts.set(g, (counts.get(g) ?? 0) + 1);
  }
  const max = Math.max(1, ...grades.map((g) => counts.get(g) ?? 0));
  const W = 320, H = 150, base = 118, bw = 40, gap = (W - bw * grades.length) / (grades.length + 1);
  const bars = grades.map((g, i) => {
    const n = counts.get(g) ?? 0;
    const h = Math.round(((n / max) * 96));
    const x = Math.round(gap + i * (bw + gap));
    const y = base - h;
    return `<rect x="${x}" y="${y}" width="${bw}" height="${h}" rx="3" fill="${GRADE_COLORS[g]}" opacity="0.85"><title>Grade ${g}: ${n.toLocaleString("en-US")} block groups</title></rect><text x="${x + bw / 2}" y="${base + 14}" text-anchor="middle" class="dn-chart-axis">${g}</text><text x="${x + bw / 2}" y="${y - 5}" text-anchor="middle" class="dn-chart-val">${n.toLocaleString("en-US")}</text>`;
  }).join("");
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Bar chart of block groups per equity grade">${bars}<line x1="0" y1="${base}" x2="${W}" y2="${base}" stroke="var(--line-soft)" stroke-width="1.5"/></svg>`;
}

/** Top-25 need vs access scatter (parity line = gap 0). */
export function renderScatterChart(el: HTMLElement, rows: TopUnderservedRow[]): void {
  const W = 320, H = 150, pad = 26;
  const px = (v: number) => pad + Math.min(1, Math.max(0, v)) * (W - pad * 2);
  const py = (v: number) => H - pad - Math.min(1, Math.max(0, v)) * (H - pad * 2);
  const dots = rows.map((r) => {
    const need = Number(r.need_index), acc = Number(r.access_overall);
    if (!Number.isFinite(need) || !Number.isFinite(acc)) return "";
    return `<circle cx="${px(need).toFixed(1)}" cy="${py(acc).toFixed(1)}" r="3.5" fill="${gradeColor(String(r.grade ?? ""))}" opacity="0.8"><title>${String(r.geoid ?? "")} · need ${need.toFixed(2)} · access ${acc.toFixed(2)} · gap ${(acc - need).toFixed(2)}</title></circle>`;
  }).join("");
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Scatter plot of need versus access for the top 25 block groups"><line x1="${px(0)}" y1="${py(1)}" x2="${px(1)}" y2="${py(0)}" stroke="var(--muted)" stroke-dasharray="4 3" stroke-width="1" opacity="0.5"/><text x="${W / 2}" y="${H - 4}" text-anchor="middle" class="dn-chart-axis">need →</text><text x="11" y="${H / 2}" text-anchor="middle" class="dn-chart-axis" transform="rotate(-90 11 ${H / 2})">access →</text>${dots}</svg>`;
}
