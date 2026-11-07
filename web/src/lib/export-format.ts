/**
 * Export-specific table columns and cell formatting. Split out of
 * components/export-view.ts during Task 010 modularization.
 */
import { fmtCurrency, fmtInt, fmtPct } from "./format";

export const TABLE_COLUMNS = [
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

export function formatCell(column: string, value: number | string | null): string {
  if (value === null || value === undefined) return "n/a";
  if (column === "pop_total") return fmtInt(value as number);
  if (column === "poverty_pct" || column === "zero_car_pct") return fmtPct(value as number);
  if (column === "median_income") return fmtCurrency(value as number);
  if (column === "need_index" || column === "access_overall" || column === "gap") {
    return (value as number).toFixed(3);
  }
  return String(value);
}
