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
      <div class="dn-export-top">
        <div class="dn-export-title-row">
          <h3 id="top-n-title">City-wide underserved block groups</h3>
          <button class="dn-btn" id="download-top" type="button">Download city-wide table (CSV)</button>
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
          <button class="dn-btn" id="download-snapshot" type="button" hidden>Download report card snapshot (CSV)</button>
        </div>
        <div id="snapshot-body"></div>
      </div>`;

    document.getElementById("download-top")!.addEventListener("click", () => this.downloadTop());

    this.unsub = subscribe(() => this.renderSnapshot());
    void this.loadTop();
    this.renderSnapshot();
    paintSketchBoxes(this.container);
  }

  private async loadTop(): Promise<void> {
    // Prefer the API endpoint; fall back to the identical client-side ranking
    // if the endpoint is unavailable (e.g. backend not running).
    try {
      this.topRows = await api.topUnderserved(25);
    } catch {
      this.topRows = rankTopUnderserved(this.equity, 25);
    }
    this.renderTable();
  }

  private renderTable(): void {
    const thead = this.container.querySelector("thead")!;
    const tbody = this.container.querySelector("tbody")!;

    thead.innerHTML = `<tr>${TABLE_COLUMNS.map((c) => `<th scope="col">${c}</th>`).join("")}</tr>`;
    tbody.innerHTML = "";
    for (const row of this.topRows) {
      const tr = document.createElement("tr");
      tr.innerHTML = TABLE_COLUMNS.map((c) => {
        const v = row[c];
        const text = formatCell(c, v);
        return `<td>${escapeHtml(text)}</td>`;
      }).join("");
      tr.addEventListener("click", () => {
        actions.selectGeoid(String(row.geoid ?? ""));
      });
      tbody.appendChild(tr);
    }
    paintSketchBoxes(this.container, ".dn-table-wrap");
  }

  private renderSnapshot(): void {
    const geoid = getState().selectedGeoid;
    const snapshotEl = this.container.querySelector(".dn-export-snapshot") as HTMLElement;
    const btn = document.getElementById("download-snapshot") as HTMLButtonElement;
    const body = document.getElementById("snapshot-body")!;

    if (!geoid) {
      btn.hidden = true;
      body.innerHTML = `<div class="dn-empty"><span class="dn-mascot" aria-hidden="true">${busSvg({ size: 56 })}</span><p class="dn-muted" style="margin:0">Select a block group on the map (or click a row above) to download its Equity Report Card snapshot.</p></div>`;
      paintSketchBoxes(snapshotEl);
      return;
    }
    const feature = this.equityById.get(geoid);
    if (!feature) {
      btn.hidden = true;
      body.innerHTML = `<p class="dn-muted">Block group ${escapeHtml(geoid)} was not found in the equity data.</p>`;
      paintSketchBoxes(snapshotEl);
      return;
    }

    btn.hidden = false;
    btn.onclick = () => this.downloadSnapshot(feature);
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

  private downloadSnapshot(feature: EquityFeature): void {
    const p = feature.properties;
    const row = {} as Record<string, unknown>;
    for (const col of SNAPSHOT_COLUMNS) {
      row[col] = (p as unknown as Record<string, unknown>)[col] ?? null;
    }
    const csv = toCsv([row], SNAPSHOT_COLUMNS as readonly string[]);
    downloadCsv(`seattle_report_card_${p.geoid}.csv`, csv);
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
