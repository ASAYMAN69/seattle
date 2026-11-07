/**
 * Export view snapshot — Equity Report Card preview + CSV/PNG downloads.
 * Split out of components/export-view.ts during Task 010 modularization.
 * The SVG report-card layout and CSV bytes are unchanged.
 */
import { downloadCsv, toCsv } from "../lib/csv";
import { escapeHtml, fmtCurrency, fmtInt, fmtPct } from "../lib/format";
import { busSvg } from "../lib/mascot";
import { paintSketchBoxes } from "../lib/sketch";
import { getState } from "../state";
import { SNAPSHOT_COLUMNS, type EquityFeature } from "../types";

/** Render the snapshot panel for the currently selected block group. */
export function renderSnapshotInto(
  container: HTMLElement,
  equityById: Map<string, EquityFeature>,
): void {
  const geoid = getState().selectedGeoid;
  const snapshotEl = container.querySelector(".dn-export-snapshot") as HTMLElement;
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
  const feature = equityById.get(geoid);
  if (!feature) {
    btn.hidden = true;
    csvBtn.hidden = true;
    body.innerHTML = `<p class="dn-muted">Block group ${escapeHtml(geoid)} was not found in the equity data.</p>`;
    paintSketchBoxes(snapshotEl);
    return;
  }

  btn.hidden = false;
  csvBtn.hidden = false;
  btn.onclick = () => downloadSnapshotPng(feature);
  csvBtn.onclick = () => downloadSnapshotCsv(feature);
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

export function downloadSnapshotCsv(feature: EquityFeature): void {
  const p = feature.properties;
  const row = {} as Record<string, unknown>;
  for (const col of SNAPSHOT_COLUMNS) {
    row[col] = (p as unknown as Record<string, unknown>)[col] ?? null;
  }
  const csv = toCsv([row], SNAPSHOT_COLUMNS as readonly string[]);
  downloadCsv(`seattle_report_card_${p.geoid}.csv`, csv);
}

/** Download the Equity Report Card as a shareable PNG (charts + stats). */
export function downloadSnapshotPng(feature: EquityFeature): void {
  const svg = buildReportCardSvg(feature);
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

export function buildReportCardSvg(feature: EquityFeature): string {
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
