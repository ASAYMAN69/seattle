/**
 * Typed API client for the FastAPI contract (GET endpoints):
 *
 *   /api/health · /api/boundary · /api/equity · /api/recommendations
 *   /api/sensitivity · /api/report-cards · /api/top-underserved?n=
 *   /api/block-group/{geoid} · /api/metadata
 *
 * In development, Vite proxies `/api` → http://localhost:8000 (see
 * vite.config.ts). Each getter caches its promise, so the SPA loads each
 * dataset once.
 */
import {
  SNAPSHOT_COLUMNS,
  type CitySummary,
  type EquityFeature,
  type EquityFeatureCollection,
  type GeoJsonFeatureCollection,
  type MetadataResponse,
  type RecommendationFeatureCollection,
  type ReportCardsResponse,
  type SensitivityRecord,
  type SnapshotColumn,
  type TopUnderservedRow,
} from "../types";

export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const cache = new Map<string, Promise<unknown>>();

function getJson<T>(path: string): Promise<T> {
  const key = path;
  if (!cache.has(key)) {
    const promise = (async () => {
      let res: Response;
      try {
        res = await fetch(path, { headers: { Accept: "application/json" } });
      } catch {
        throw new ApiError(`Network error fetching ${path}`, 0);
      }
      if (!res.ok) {
        throw new ApiError(`GET ${path} failed (${res.status})`, res.status);
      }
      return (await res.json()) as T;
    })();
    cache.set(key, promise);
  }
  return cache.get(key) as Promise<T>;
}

export const api = {
  health: () => getJson<{ status: string }>("/api/health"),

  boundary: () => getJson<GeoJsonFeatureCollection>("/api/boundary"),

  equity: () => getJson<EquityFeatureCollection>("/api/equity"),

  recommendations: () => getJson<RecommendationFeatureCollection>("/api/recommendations"),

  sensitivity: () => getJson<{ sensitivity: SensitivityRecord[] } | SensitivityRecord[]>("/api/sensitivity")
    .then((d) => (Array.isArray(d) ? d : d.sensitivity)),

  reportCards: () => getJson<ReportCardsResponse>("/api/report-cards"),

  topUnderserved: (n = 25) =>
    getJson<{ rows: TopUnderservedRow[] } | TopUnderservedRow[]>(`/api/top-underserved?n=${n}`)
      .then((d) => (Array.isArray(d) ? d : d.rows)),

  blockGroup: (geoid: string) =>
    getJson<Partial<Record<SnapshotColumn, number | string | null>>>(
      `/api/block-group/${encodeURIComponent(geoid)}`,
    ).then((row) => (row && Object.keys(row).length ? row : null)),

  metadata: () => getJson<MetadataResponse>("/api/metadata"),
};

/* ------------------------------------------------------------------ */
/* Client-side fallbacks (used only if an endpoint is unavailable)     */
/* ------------------------------------------------------------------ */

/** Letter-grade rank used to break ties (F first) — mirrors export.py. */
const GRADE_RANK: Record<string, number> = { A: 0, B: 1, C: 2, D: 3, F: 4 };

export function rankTopUnderserved(
  features: EquityFeature[],
  n: number,
): TopUnderservedRow[] {
  const cols = SNAPSHOT_COLUMNS as readonly string[];
  const ranked = [...features]
    .map((f) => f.properties)
    .sort((a, b) => {
      const needDiff = (b.need_index ?? 0) - (a.need_index ?? 0);
      if (needDiff !== 0) return needDiff;
      const gapDiff = (a.gap ?? 0) - (b.gap ?? 0);
      if (gapDiff !== 0) return gapDiff;
      const rankA = GRADE_RANK[String(a.grade ?? "").trim().toUpperCase()] ?? 5;
      const rankB = GRADE_RANK[String(b.grade ?? "").trim().toUpperCase()] ?? 5;
      return rankB - rankA;
    })
    .slice(0, n)
    .map((p) => {
      const row = {} as Record<string, number | string | null>;
      for (const col of cols) {
        row[col] = (p as unknown as Record<string, unknown>)[col] as number | string | null;
      }
      return row as TopUnderservedRow;
    });
  return ranked;
}
