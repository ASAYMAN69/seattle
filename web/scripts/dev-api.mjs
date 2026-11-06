#!/usr/bin/env node
/**
 * DEV-ONLY mock API server for the SPA (not for production).
 *
 * Serves the same contract as the FastAPI service (`api/`, built by the
 * Wizard agent) using the REAL prepared data under `data/prepared/`. This lets
 * the frontend be verified before the backend is ready. Nothing here is
 * fabricated — values are read straight from the real prepared files.
 *
 * Run:  npm run dev:mock:gen   (one-time: parquet → JSON under web/dev-mock/)
 *        npm run dev            (vite proxy → http://localhost:8000)
 * ...or simply: npm run dev:mock  (generates mocks, starts this server at
 *                                   http://localhost:8000, then starts Vite)
 */
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const PREPARED = path.join(REPO_ROOT, "data", "prepared");
const DEV_MOCK = path.resolve(__dirname, "..", "dev-mock");
const PORT = Number(process.env.PORT || 8000);

const readJson = (rel) => JSON.parse(fs.readFileSync(path.join(PREPARED, rel), "utf8"));
const readMock = (name) => JSON.parse(fs.readFileSync(path.join(DEV_MOCK, name), "utf8"));

let boundary;
let equity; // FC with ACS joined
let recommendations;
let sensitivity;
let reportCards;
let acsByGeoid = null;
let acsWarning = "";

function cleanValue(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === "number" && !Number.isFinite(v)) return null;
  if (v === -666666666) return null;
  if (Array.isArray(v)) return v.map(cleanValue);
  if (typeof v === "object") {
    const out = {};
    for (const [k, val] of Object.entries(v)) out[k] = cleanValue(val);
    return out;
  }
  return v;
}

function tryLoad() {
  try {
    boundary = readJson("seattle_boundary.geojson");
  } catch {
    throw new Error("Seattle boundary missing: data/prepared/seattle_boundary.geojson");
  }
  try {
    equity = readJson("equity/equity_scores.geojson");
  } catch {
    throw new Error("Equity scores missing: data/prepared/equity/equity_scores.geojson");
  }
  try {
    recommendations = readJson("equity/recommendations.geojson");
  } catch {
    throw new Error("Recommendations missing: data/prepared/equity/recommendations.geojson");
  }
  try {
    reportCards = readJson("equity/report_cards.json");
  } catch {
    throw new Error("Report cards missing: data/prepared/equity/report_cards.json");
  }
  try {
    sensitivity = readMock("sensitivity.json");
  } catch {
    sensitivity = null;
    acsWarning = "sensitivity mock missing — run `npm run dev:mock:gen`";
  }
  try {
    const acs = readMock("acs-demographics.json");
    acsByGeoid = new Map(acs.map((r) => [String(r.geoid), r]));
  } catch {
    acsByGeoid = null;
  }

  for (const f of equity.features) {
    const p = f.properties;
    if (acsByGeoid?.has(String(p.geoid))) {
      const a = acsByGeoid.get(String(p.geoid));
      p.poverty_pct = cleanValue(a.poverty_pct);
      p.zero_car_pct = cleanValue(a.zero_car_pct);
      p.median_income = cleanValue(a.median_income);
    } else {
      p.poverty_pct = null;
      p.zero_car_pct = null;
      p.median_income = null;
    }
  }
}

const GRADE_RANK = { A: 0, B: 1, C: 2, D: 3, F: 4 };
const SNAPSHOT_COLUMNS = [
  "geoid", "grade", "jobs_grade", "healthcare_grade", "schools_grade",
  "food_grade", "jobs_access", "healthcare_access", "schools_access",
  "food_access", "access_overall", "need_index", "gap", "pop_total",
  "poverty_pct", "zero_car_pct", "median_income",
];

function topUnderserved(n) {
  const rows = equity.features
    .map((f) => f.properties)
    .sort((a, b) => {
      const dNeed = (b.need_index ?? 0) - (a.need_index ?? 0);
      if (dNeed !== 0) return dNeed;
      const dGap = (a.gap ?? 0) - (b.gap ?? 0);
      if (dGap !== 0) return dGap;
      const ra = GRADE_RANK[String(a.grade ?? "").trim().toUpperCase()] ?? 5;
      const rb = GRADE_RANK[String(b.grade ?? "").trim().toUpperCase()] ?? 5;
      return rb - ra;
    })
    .slice(0, n)
    .map((p) => {
      const row = {};
      for (const c of SNAPSHOT_COLUMNS) row[c] = cleanValue(p[c] ?? null);
      return row;
    });
  return rows;
}

function blockGroup(geoid) {
  const key = String(geoid);
  const f = equity.features.find((x) => String(x.properties.geoid) === key);
  if (!f) return null;
  const row = {};
  for (const c of SNAPSHOT_COLUMNS) row[c] = cleanValue(f.properties[c] ?? null);
  return row;
}

const METHODOLOGY_NOTE =
  "Methodology: equity scores, letter grades, and ACS statistics are from the prepared DataNova 2026 transit-equity analysis. The equity gap = access − need (positive = better served). No live routing or API keys.";

function send(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(payload),
  });
  res.end(payload);
}

const json = (res, body) => send(res, 200, body);

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const p = url.pathname;
  const q = url.searchParams;

  // GET /api/health
  if (p === "/api/health") return json(res, { status: "ok" });

  // GET /api/boundary
  if (p === "/api/boundary") return json(res, boundary);

  // GET /api/equity (ACS-joined)
  if (p === "/api/equity") return json(res, equity);

  // GET /api/recommendations
  if (p === "/api/recommendations") return json(res, recommendations);

  // GET /api/sensitivity
  if (p === "/api/sensitivity") {
    if (!sensitivity) return send(res, 503, { detail: acsWarning });
    return json(res, sensitivity);
  }

  // GET /api/report-cards
  if (p === "/api/report-cards") return json(res, reportCards);

  // GET /api/top-underserved?n=
  if (p === "/api/top-underserved") {
    const n = Math.min(Math.max(Number(q.get("n")) || 25, 1), 1545);
    return json(res, topUnderserved(n));
  }

  // GET /api/block-group/{geoid}
  const bgMatch = p.match(/^\/api\/block-group\/([^/]+)$/);
  if (bgMatch) {
    const row = blockGroup(decodeURIComponent(bgMatch[1]));
    if (!row) return send(res, 404, { detail: "block group not found" });
    return json(res, row);
  }

  // GET /api/metadata
  if (p === "/api/metadata") {
    return json(res, {
      generated_at: reportCards.generated_at,
      summary: reportCards.summary,
      methodology_note: METHODOLOGY_NOTE,
    });
  }

  send(res, 404, { detail: `no mock route for ${p}` });
});

try {
  tryLoad();
} catch (err) {
  console.error("[dev-api] Failed to load real prepared data:", err.message);
  console.error("[dev-api] Make sure the analysis pipeline has run (scripts/run_analysis.py).");
  process.exit(1);
}

server.listen(PORT, () => {
  console.log(`[dev-api] Mock API serving real prepared data on http://localhost:${PORT}`);
  if (acsWarning) console.warn(`[dev-api] warning: ${acsWarning}`);
});
