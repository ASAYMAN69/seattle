#!/usr/bin/env bash
# Start all: one backend (:8000) serving dev (:5173) and prod (:4173).
# If data/prepared/ is empty on a fresh machine, run the data pipeline first.
set -u
cd "$(dirname "$0")"

PREPARED_DIR="data/prepared"
PY=".venv/bin/python"

count_files() {
  find "$1" -type f 2>/dev/null | wc -l
}

# ---- 1. Data pipeline (only if prepared data is empty) --------------------
missing=0
if [ ! -d "$PREPARED_DIR" ] || [ "$(count_files "$PREPARED_DIR")" -eq 0 ]; then
  missing=1
fi
if [ "$missing" -eq 1 ]; then
  echo "[pipeline] data/prepared/ is empty — running the full pipeline…"
  for s in fetch_geometry.py fetch_gtfs.py parse_gtfs.py fetch_census.py fetch_opportunities.py run_analysis.py; do
    echo "[pipeline] python scripts/$s"
    "$PY" "scripts/$s" || { echo "[pipeline] FAILED at scripts/$s"; exit 1; }
  done
  echo "[pipeline] done."
else
  echo "[data] data/prepared/ present ($(du -sh "$PREPARED_DIR" | cut -f1)) — skipping pipeline."
fi

# ---- 2. Prod build (vite preview needs web/dist) ---------------------------
if [ ! -f "web/dist/index.html" ]; then
  echo "[build] web/dist missing — running npm run build…"
  (cd web && npm run build) || { echo "[build] FAILED"; exit 1; }
fi

# ---- 3. Start backend once (:8000) ----------------------------------------
start_backend() {
  echo "[backend] starting uvicorn api.main:app on :8000…"
  setsid nohup .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 < /dev/null > /tmp/opencode/backend.log 2>&1 &
  for i in $(seq 1 30); do
    if curl -sf -o /dev/null http://localhost:8000/api/health 2>/dev/null; then
      echo "[backend] healthy."
      return 0
    fi
    sleep 1
  done
  echo "[backend] FAILED to start — see /tmp/opencode/backend.log"; tail -20 /tmp/opencode/backend.log; exit 1
}

if curl -sf -o /dev/null http://localhost:8000/api/health 2>/dev/null; then
  echo "[backend] already running on :8000."
else
  start_backend
fi

# ---- 4. Start both frontends ----------------------------------------------
if curl -sf -o /dev/null http://localhost:5173/ 2>/dev/null; then
  echo "[dev] already running on :5173."
else
  echo "[dev] starting npm run dev on :5173…"
  (cd web && setsid nohup npm run dev < /dev/null > /tmp/opencode/dev.log 2>&1 &)
fi

if curl -sf -o /dev/null http://localhost:4173/ 2>/dev/null; then
  echo "[prod] already running on :4173."
else
  echo "[prod] starting npm start (vite preview) on :4173…"
  (cd web && setsid nohup npm start -- --port 4173 --host 127.0.0.1 < /dev/null > /tmp/opencode/prod.log 2>&1 &)
fi

sleep 3
echo "---"
curl -s -o /dev/null -w "backend :8000  %{http_code}\n" http://localhost:8000/api/health 2>/dev/null || echo "backend :8000  DOWN"
curl -s -o /dev/null -w "dev     :5173  %{http_code}\n" http://localhost:5173/ 2>/dev/null || echo "dev     :5173  DOWN"
curl -s -o /dev/null -w "prod    :4173  %{http_code}\n" http://localhost:4173/ 2>/dev/null || echo "prod    :4173  DOWN"
echo "logs: /tmp/opencode/backend.log /tmp/opencode/dev.log /tmp/opencode/prod.log"
