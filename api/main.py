"""FastAPI application entrypoint for the Seattle Transit Equity Index API.

Wiring order matters:
1. CORS middleware (Vite dev origins).
2. The ``/api`` router — registered before any catch-all mount so API routes
   always win.
3. Static SPA serving from ``web/dist`` when present, with an ``index.html``
   fallback for client-side routes; otherwise a clean HTML fallback page.

The module-level ``app`` is the ASGI target for ``uvicorn api.main:app``.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.data import WEB_DIST
from api.endpoints import router

# Vite dev server origins (development CORS). Static serving handles production.
DEV_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

FALLBACK_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Seattle Transit Equity Index — API</title>
<style>
  body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:640px;margin:80px auto;padding:0 24px;color:#0f172a;line-height:1.6}
  code{background:#f1f5f9;padding:2px 6px;border-radius:4px}
  a{color:#1a7f37}
</style>
</head>
<body>
<h1>Seattle Transit Equity Index</h1>
<p>The API is live. The frontend build (<code>web/dist</code>) is not present yet, so the SPA is unavailable.</p>
<p>Try <a href="/api/health">/api/health</a>, <a href="/api/equity">/api/equity</a>, or <a href="/docs">/docs</a> (interactive API docs).</p>
</body>
</html>
"""


class SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to ``index.html`` for unknown paths (SPA routing)."""

    async def get_response(self, path: str, scope):
        # Starlette's StaticFiles signals a missing file either by raising
        # HTTPException(404) (current) or returning a 404 response (older) —
        # handle both. API paths must never be swallowed by the SPA fallback:
        # an unknown /api/* path returns JSON 404 from the API router, so we
        # let StaticFiles' 404 stand for those.
        if path.startswith("api/"):
            return await super().get_response(path, scope)
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and path != "index.html":
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404 and path != "index.html":
            return await super().get_response("index.html", scope)
        return response


def create_app() -> FastAPI:
    app = FastAPI(
        title="Seattle Transit Equity Index API",
        description=(
            "Read-only API over the precomputed prepared data for the "
            "Seattle Transit Equity Index web app."
        ),
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
        max_age=600,
    )
    app.include_router(router)

    if WEB_DIST.is_dir():
        app.mount(
            "/",
            SPAStaticFiles(directory=str(WEB_DIST), html=True),
            name="spa",
        )
    else:
        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        async def _fallback_root() -> str:
            return FALLBACK_HTML

        @app.get(
            "/{full_path:path}", response_class=HTMLResponse, include_in_schema=False
        )
        async def _fallback_spa(full_path: str) -> str:
            if full_path.startswith("api/"):
                raise StarletteHTTPException(status_code=404, detail="Not found")
            return FALLBACK_HTML

    return app


app = create_app()
