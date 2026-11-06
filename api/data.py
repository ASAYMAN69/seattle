"""Data loading and app-level constants for the FastAPI service.

The prepared data is loaded exactly once at import time by wrapping the
existing project loader (``app.data_io.load_prepared``). This keeps the API a
thin data-serving layer (no live computation) and avoids re-reading raw files
per request. Loading is eager so a missing/corrupt prepared input fails fast at
boot with a clear error rather than surfacing on the first request.

Trade-off: the loaded GeoDataFrames stay resident in memory for the life of the
process (the equity scores GeoDataFrame is ~6 MB on disk; negligible for a
local demo server).
"""

from __future__ import annotations

from pathlib import Path

from app.data_io import load_prepared

# Repo root: ``data/`` sits next to the ``app/`` and ``api/`` packages.
REPO_ROOT = Path(__file__).resolve().parents[1]

# Built SPA directory (owned by the frontend agent). Served as static files
# when present; a clean fallback page is used otherwise.
WEB_DIST = REPO_ROOT / "web" / "dist"

# Single load, shared by every endpoint (read-only).
PREPARED = load_prepared()
