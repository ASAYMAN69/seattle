/** Formatting + sanitization helpers (civic, data-forward). */

/** Thousands separators, e.g. 8871 -> "8,871". */
export function fmtInt(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return Math.round(value).toLocaleString("en-US");
}

/** Percent, e.g. 0.2165 -> "21.7%". */
export function fmtPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return `${(value * 100).toFixed(1)}%`;
}

/** Currency, e.g. 49000 -> "$49,000". */
export function fmtCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

/** Percentage points with sign, e.g. 0.0345 -> "+3.45 pp". */
export function fmtPp(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  const sign = value >= 0 ? "+" : "−";
  return `${sign}${(Math.abs(value) * 100).toFixed(2)} pp`;
}

/** Minutes, e.g. 1.4516 -> "1.45 min". */
export function fmtMinutes(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  return `${value.toFixed(2)} min`;
}

/** Escape text for safe injection into innerHTML templates. */
export function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
