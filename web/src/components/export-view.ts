/**
 * Export & summary view — city-wide top-N underserved table (CSV download)
 * and a per-block-group Equity Report Card snapshot download when one is
 * selected. Ranking replicates `app/views/export.py` exactly:
 * need_index desc, then gap asc, then grade rank (F first).
 * Sketch theme: ink-soft table shell, wobbly bus in the empty snapshot
 * state. Ranking and CSV bytes are unchanged.
 *
 * Charts and snapshot renderers live in export-charts.ts / export-snapshot.ts
 * (Task 010 modularization).
 */
import { api, rankTopUnderserved } from "../api/client";
import { downloadCsv, toCsv } from "../lib/csv";
import { TABLE_COLUMNS, formatCell } from "../lib/export-format";
import { paintSketchBoxes } from "../lib/sketch";
import { actions, getState, subscribe } from "../state";
import { SNAPSHOT_COLUMNS } from "../types";
import type { EquityFeature, TopUnderservedRow } from "../types";
import { renderGradeChart, renderScatterChart } from "./export-charts";
import { renderSnapshotInto } from "./export-snapshot";

interface ExportOptions {
  container: HTMLElement;
  equity: EquityFeature[];
  equityById: Map<string, EquityFeature>;
}

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

    this.unsub = subscribe(() => renderSnapshotInto(this.container, this.equityById));
    void this.loadTop();
    renderSnapshotInto(this.container, this.equityById);
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
    const gradeEl = document.getElementById("grade-chart");
    if (gradeEl) renderGradeChart(gradeEl, this.equity);
    const scatterEl = document.getElementById("scatter-chart");
    if (scatterEl) renderScatterChart(scatterEl, this.topRows);
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

  destroy(): void {
    this.unsub();
  }
}
