/**
 * Export & summary view — city-wide top-N underserved table (CSV download)
 * and a per-block-group Equity Report Card snapshot download when one is
 * selected. Ranking replicates `app/views/export.py` exactly:
 * need_index desc, then gap asc, then grade rank (F first).
 * Sketch theme: ink-soft table shell, wobbly bus in the empty snapshot
 * state. Ranking and CSV bytes are unchanged.
 */
import { api, rankTopUnderserved } from "../api/client";
import { downloadCsv, toCsv } from "../lib/csv";
import { GRADE_COLORS, gradeColor } from "../lib/colors";
import {
  escapeHtml,
  fmtCurrency,
  fmtInt,
  fmtPct,
} from "../lib/format";
import { busSvg } from "../lib/mascot";
import { paintSketchBoxes } from "../lib/sketch";
import { actions, getState, subscribe } from "../state";
import {
  SNAPSHOT_COLUMNS,
  type EquityFeature,
  type TopUnderservedRow,
} from "../types";

interface ExportOptions {
  container: HTMLElement;
  equity: EquityFeature[];
  equityById: Map<string, EquityFeature>;
}

const TABLE_COLUMNS = [
  "geoid",
  "grade",
  "need_index",
  "access_overall",
  "gap",
  "pop_total",
  "poverty_pct",
  "zero_car_pct",
  "median_income",
] as const;

export class ExportView {
  private container: HTMLElement;
  private equity: EquityFeature[];
  private equityById: Map<string, EquityFeature>;
  private topRows: TopUnderservedRow[] = [];
  private checkedGeoids = new Set<string>();
  private unsub: () => void;

  constructor(options: ExportOptions) {
    this.container = options.container;
    this.equity = options.equity;
    this.equityById = options.equityById;

    this.container.innerHTML = `
      <div class="dn-panel-head">
        <h2>Export &amp; summary</h2>
        <p class="dn-muted">Methodology: equity scores, letter grades, and ACS statistics are from the prepared DataNova 2026 transit-equity analysis. The equity gap = access − need (positive = better served). No live routing or API keys.</p>
      </div>
      <div class="dn-charts">
        <section class="dn-chart-card sketch-card" aria-labelledby="grade-chart-title">
          <h3 id="grade-chart-title">City-wide grade distribution</h3>
          <p class="dn-chart-sub">All 1,545 block groups, weighted by count</p>
          <div id="grade-chart"></div>
        </section>
        <section class="dn-chart-card sketch-card" aria-labelledby="scatter-chart-title">
          <h3 id="scatter-chart-title">Top 25: need vs access</h3>
          <p class="dn-chart-sub">Each dot is a table row · dashed line = parity (gap 0)</p>
          <div id="scatter-chart"></div>
        </section>
      </div>
      <div class="dn-export-top">
        <div class="dn-export-title-row">
          <h3 id="top-n-title">City-wide underserved block groups</h3>
          <div class="dn-export-actions">
            <span class="dn-export-count" id="selected-count" role="status"></span>
            <button class="dn-btn is-secondary" id="download-selected" type="button" disabled>Download selected (CSV)</button>
            <button class="dn-btn" id="download-top" type="button">Download city-wide table (CSV)</button>
          </div>
        </div>
        <div class="dn-table-wrap sketch-card" role="region" aria-labelledby="top-n-title" tabindex="0">
          <table class="dn-table">
            <thead></thead><tbody></tbody>
          </table>
        </div>
      </div>
      <div class="dn-export-snapshot sketch-card">
        <div class="dn-export-title-row">
          <h3>Equity report card snapshot</h3>
          <div class="dn-export-actions">
            <button class="dn-btn is-secondary" id="download-snapshot-csv" type="button" hidden>CSV</button>
            <button class="dn-btn" id="download-snapshot" type="button" hidden>Download report card (PNG)</button>
          </div>
        </div>
        <div id="snapshot-body"></div>
      </div>`;

    document.getElementById("download-top")!.addEventListener("click", () => this.downloadTop());
    document.getElementById("download-selected")!.addEventListener("click", () => this.downloadSelected());

    this.unsub = subscribe(() => this.renderSnapshot());
    void this.loadTop();
    this.renderSnapshot();
    this.renderCharts();
    paintSketchBoxes(this.container);
  }

  private async loadTop(timeOfDay?: string): Promise<void> {
    // Prefer the API endpoint; fall back to the identical client-side ranking
    // if the endpoint is unavailable (e.g. backend not running).
    try {
      this.topRows = await api.topUnderserved(25, timeOfDay);
    } catch {
      this.topRows = rankTopUnderserved(this.equity, 25);
    }
    this.renderTable();
    this.renderCharts();
  }

  /** Re-fetch the table for a time-of-day scenario (no rebuild). */
  async refreshTop(timeOfDay?: string): Promise<void> {
    await this.loadTop(timeOfDay);
  }

  private renderTable(): void {
    const thead = this.container.querySelector("thead")!;
    const tbody = this.container.querySelector("tbody")!;

    thead.innerHTML = `<tr><th scope="col"><span class="dn-visually-hidden">Select rows</span></th>${TABLE_COLUMNS.map((c) => `<th scope="col">${c}</th>`).join("")}</tr>`;
    tbody.innerHTML = "";
    for (const row of this.topRows) {
      const geoid = String(row.geoid ?? "");
      const tr = document.createElement("tr");
      const check = document.createElement("input");
      check.type = "checkbox";
      check.className = "dn-row-check";
      check.checked = this.checkedGeoids.has(geoid);
      check.setAttribute("aria-label", `Select block group ${geoid}`);
      check.addEventListener("change", () => {
        if (check.checked) this.checkedGeoids.add(geoid);
        else this.checkedGeoids.delete(geoid);
        this.updateSelectedUi();
      });
      check.addEventListener("click", (e) => e.stopPropagation());
      const checkTd = document.createElement("td");
      checkTd.appendChild(check);
      tr.appendChild(checkTd);
      for (const c of TABLE_COLUMNS) {
        const td = document.createElement("td");
        td.textContent = formatCell(c, row[c]);
        tr.appendChild(td);
      }
      tr.addEventListener("click", () => {
        actions.selectGeoid(geoid);
      });
      tbody.appendChild(tr);
    }
    this.updateSelectedUi();
    paintSketchBoxes(this.container, ".dn-table-wrap");
  }

  private updateSelectedUi(): void {
    const btn = document.getElementById("download-selected") as HTMLButtonElement | null;
    const label = document.getElementById("selected-count");
    const n = this.checkedGeoids.size;
    if (btn) btn.disabled = n === 0;
    if (label) label.textContent = n > 0 ? `${n} selected` : "";
  }

  private renderCharts(): void {
    this.renderGradeChart();
    this.renderScatterChart();
  }

  private renderGradeChart(): void {
    const el = document.getElementById("grade-chart");
    if (!el) return;
    const grades = ["A", "B", "C", "D", "F"];
    const counts = new Map<string, number>();
    for (const f of this.equity) {
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

  private renderScatterChart(): void {
    const el = document.getElementById("scatter-chart");
    if (!el) return;
    const W = 320, H = 150, pad = 26;
    const px = (v: number) => pad + Math.min(1, Math.max(0, v)) * (W - pad * 2);
    const py = (v: number) => H - pad - Math.min(1, Math.max(0, v)) * (H - pad * 2);
    const dots = this.topRows.map((r) => {
      const need = Number(r.need_index), acc = Number(r.access_overall);
      if (!Number.isFinite(need) || !Number.isFinite(acc)) return "";
      return `<circle cx="${px(need).toFixed(1)}" cy="${py(acc).toFixed(1)}" r="3.5" fill="${gradeColor(String(r.grade ?? ""))}" opacity="0.8"><title>${String(r.geoid ?? "")} · need ${need.toFixed(2)} · access ${acc.toFixed(2)} · gap ${(acc - need).toFixed(2)}</title></circle>`;
    }).join("");
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Scatter plot of need versus access for the top 25 block groups"><line x1="${px(0)}" y1="${py(1)}" x2="${px(1)}" y2="${py(0)}" stroke="var(--muted)" stroke-dasharray="4 3" stroke-width="1" opacity="0.5"/><text x="${W / 2}" y="${H - 4}" text-anchor="middle" class="dn-chart-axis">need →</text><text x="11" y="${H / 2}" text-anchor="middle" class="dn-chart-axis" transform="rotate(-90 11 ${H / 2})">access →</text>${dots}</svg>`;
  }

  private renderSnapshot(): void {
    const geoid = getState().selectedGeoid;
    const snapshotEl = this.container.querySelector(".dn-export-snapshot") as HTMLElement;
    const btn = document.getElementById("download-snapshot") as HTMLButtonElement;
    const csvBtn = document.getElementById("download-snapshot-csv") as HTMLButtonElement;
    const body = document.getElementById("snapshot-body")!;

    if (!geoid) {
      btn.hidden = true;
      csvBtn.hidden = true;
      body.innerHTML = `<div class="dn-empty"><span class="dn-mascot" aria-hidden="true">${busSvg({ size: 56 })}</span><p class="dn-muted" style="margin:0">Select a block group on the map (or click a row above) to download its Equity Report Card snapshot.</p></div>`;
      paintSketchBoxes(snapshotEl);
      return;
    }
    const feature = this.equityById.get(geoid);
    if (!feature) {
      btn.hidden = true;
      csvBtn.hidden = true;
      body.innerHTML = `<p class="dn-muted">Block group ${escapeHtml(geoid)} was not found in the equity data.</p>`;
      paintSketchBoxes(snapshotEl);
      return;
    }

    btn.hidden = false;
    csvBtn.hidden = false;
    btn.onclick = () => this.downloadSnapshotPng(feature);
    csvBtn.onclick = () => this.downloadSnapshot(feature);
    const p = feature.properties;
    body.innerHTML = `
      <div class="dn-stat-grid">
        <div class="dn-stat"><div class="dn-stat-label">Block group</div><div class="dn-stat-value">${escapeHtml(p.geoid)}</div></div>
        <div class="dn-stat"><div class="dn-stat-label">Grade</div><div class="dn-stat-value">${escapeHtml(String(p.grade ?? "—"))}</div></div>
        <div class="dn-stat"><div class="dn-stat-label">Population</div><div class="dn-stat-value">${escapeHtml(fmtInt(p.pop_total))}</div></div>
        <div class="dn-stat"><div class="dn-stat-label">Poverty rate</div><div class="dn-stat-value">${escapeHtml(fmtPct(p.poverty_pct))}</div></div>
        <div class="dn-stat"><div class="dn-stat-label">Zero-car households</div><div class="dn-stat-value">${escapeHtml(fmtPct(p.zero_car_pct))}</div></div>
        <div class="dn-stat"><div class="dn-stat-label">Median income</div><div class="dn-stat-value">${escapeHtml(fmtCurrency(p.median_income))}</div></div>
      </div>`;
    paintSketchBoxes(snapshotEl);
  }

  private downloadTop(): void {
    const csv = toCsv(this.topRows, SNAPSHOT_COLUMNS as readonly string[]);
    downloadCsv("seattle_top_underserved.csv", csv);
  }

  private downloadSelected(): void {
    if (this.checkedGeoids.size === 0) return;
    const rows = this.topRows
      .filter((r) => this.checkedGeoids.has(String(r.geoid ?? "")))
      .map((r) => {
        const feature = this.equityById.get(String(r.geoid ?? ""));
        const p = (feature?.properties ?? r) as unknown as Record<string, unknown>;
        const row = {} as Record<string, unknown>;
        for (const col of SNAPSHOT_COLUMNS) {
          row[col] = p[col] ?? (r as unknown as Record<string, unknown>)[col] ?? null;
        }
        return row;
      });
    if (rows.length === 0) return;
    const csv = toCsv(rows, SNAPSHOT_COLUMNS as readonly string[]);
    downloadCsv(`seattle_selected_${rows.length}.csv`, csv);
  }

  private downloadSnapshot(feature: EquityFeature): void {
    const p = feature.properties;
    const row = {} as Record<string, unknown>;
    for (const col of SNAPSHOT_COLUMNS) {
      row[col] = (p as unknown as Record<string, unknown>)[col] ?? null;
    }
    const csv = toCsv([row], SNAPSHOT_COLUMNS as readonly string[]);
    downloadCsv(`seattle_report_card_${p.geoid}.csv`, csv);
  }

  /** Download the Equity Report Card as a shareable PNG (charts + stats). */
  private downloadSnapshotPng(feature: EquityFeature): void {
    const svg = this.buildReportCardSvg(feature);
    const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      const scale = 2;
      const canvas = document.createElement("canvas");
      canvas.width = 1200 * scale;
      canvas.height = 1000 * scale;
      const ctx = canvas.getContext("2d")!;
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0, 1200, 1000);
      URL.revokeObjectURL(url);
      canvas.toBlob((b) => {
        if (!b) return;
        const dl = document.createElement("a");
        dl.href = URL.createObjectURL(b);
        dl.download = `seattle_report_card_${feature.properties.geoid}.png`;
        document.body.appendChild(dl);
        dl.click();
        dl.remove();
      }, "image/png");
    };
    img.onerror = () => URL.revokeObjectURL(url);
    img.src = url;
  }

  private buildReportCardSvg(feature: EquityFeature): string {
    const p = feature.properties;
    const W = 1200, H = 1000;
    const bar = (label: string, v: number, y: number, color: string) => {
      const pct = Math.min(1, Math.max(0, v));
      const w = Math.round(pct * 760);
      return `<text x="60" y="${y + 16}" font-size="16" fill="#5a5548">${label}</text><rect x="240" y="${y}" width="760" height="18" rx="4" fill="#e8e2d4"/><rect x="240" y="${y}" width="${w}" height="18" rx="4" fill="${color}"/><text x="1015" y="${y + 15}" font-size="15" font-family="monospace" fill="#29281f">${pct.toFixed(2)}</text>`;
    };
    const gap = Number(p.gap ?? 0);
    const gapPct = Math.min(1, Math.max(0, (gap + 1) / 2)); // gap in [-1, 1]
    const dim = (label: string, v: number, y: number) => bar(label, v, y, "#4a86c5");
    const statRows: Array<[string, string]> = [
      ["Population", fmtInt(p.pop_total)],
      ["Poverty rate", fmtPct(p.poverty_pct)],
      ["Zero-car households", fmtPct(p.zero_car_pct)],
      ["Median income", fmtCurrency(p.median_income)],
    ];
    const stats = statRows.map(([k, v], i) => {
      const x = 60 + (i % 2) * 560;
      const y = 620 + Math.floor(i / 2) * 84;
      return `<rect x="${x}" y="${y - 28}" width="520" height="52" rx="6" fill="#f5f1e6" stroke="#d9d2c0"/><text x="${x + 16}" y="${y - 6}" font-size="13" letter-spacing="1" fill="#8a8474">${k.toUpperCase()}</text><text x="${x + 16}" y="${y + 16}" font-size="22" font-weight="700" fill="#29281f">${escapeHtml(v)}</text>`;
    }).join("");
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<rect width="${W}" height="${H}" fill="#fbf7ee"/>
<rect x="0" y="0" width="${W}" height="118" fill="#f5f1e6"/>
<text x="60" y="52" font-size="14" letter-spacing="2" fill="#8a8474">SEATTLE TRANSIT EQUITY INDEX</text>
<text x="60" y="88" font-size="34" font-weight="700" fill="#29281f">Equity Report Card — Block group ${escapeHtml(p.geoid)}</text>
<text x="60" y="165" font-size="19" font-weight="700" fill="#29281f">Access vs need</text>
${bar("Overall access", Number(p.access_overall ?? 0), 185, "#4a86c5")}
${bar("Need index", Number(p.need_index ?? 0), 225, "#d94f4f")}
<text x="60" y="280" font-size="19" font-weight="700" fill="#29281f">Equity gap (access − need)</text>
<rect x="240" y="294" width="760" height="18" rx="4" fill="#e8e2d4"/>
<rect x="240" y="294" width="${Math.round(gapPct * 760)}" height="18" rx="4" fill="${gap < 0 ? "#c62828" : "#1a7f37"}"/>
<text x="1015" y="309" font-size="15" font-family="monospace" fill="#29281f">${gap >= 0 ? "+" : ""}${gap.toFixed(2)}</text>
<text x="60" y="360" font-size="19" font-weight="700" fill="#29281f">Access by dimension</text>
${dim("Jobs", Number(p.jobs_access ?? 0), 380)}
${dim("Food", Number(p.food_access ?? 0), 420)}
${dim("Healthcare", Number(p.healthcare_access ?? 0), 460)}
${dim("Schools", Number(p.schools_access ?? 0), 500)}
<text x="60" y="570" font-size="19" font-weight="700" fill="#29281f">Household snapshot</text>
${stats}
<text x="60" y="932" font-size="14" fill="#8a8474">DataNova 2026 transit-equity analysis (prepared ACS + equity scores).</text>
<text x="60" y="952" font-size="14" fill="#8a8474">Access scores are 0–1 composites — higher is better. Gap = access − need;</text>
<text x="60" y="972" font-size="14" fill="#8a8474">negative = underserved. Grade: ${escapeHtml(String(p.grade ?? "—"))} (A best → F worst). No live routing.</text>
</svg>`;
  }

  destroy(): void {
    this.unsub();
  }
}

function formatCell(column: string, value: number | string | null): string {
  if (value === null || value === undefined) return "n/a";
  if (column === "pop_total") return fmtInt(value as number);
  if (column === "poverty_pct" || column === "zero_car_pct") return fmtPct(value as number);
  if (column === "median_income") return fmtCurrency(value as number);
  if (column === "need_index" || column === "access_overall" || column === "gap") {
    return (value as number).toFixed(3);
  }
  return String(value);
}
