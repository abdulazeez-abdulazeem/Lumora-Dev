"""
VERCEL TEST ONLY root entrypoint.

- Defines top-level FastAPI `app` (required by Vercel detector).
- Serves the existing frontend/ UI at GET / and static asset paths.
- Loads backend.api:app when available (full Lumora API + same UI routes).

Does NOT replace backend/api.py. Container/Docker still use backend.api:app
or uvicorn/Procfile/server.py unchanged.
"""
from __future__ import annotations

import logging
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("LUMORA_RUNTIME", "vercel")

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger("lumora.vercel")
_FRONTEND = os.path.join(_ROOT, "frontend")

# Vercel static detector requires a top-level FastAPI() assignment named `app`.
app = FastAPI(title="Lumora Dev API", version="4.0.0")


def _frontend_path(name: str) -> str:
    candidate = os.path.normpath(os.path.join(_FRONTEND, name))
    if not candidate.startswith(os.path.abspath(_FRONTEND)):
        raise HTTPException(status_code=404, detail="Not found")
    if not os.path.isfile(candidate):
        raise HTTPException(status_code=404, detail="Not found")
    return candidate


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Lumora Dev",
        "version": "4.0.0",
        "runtime": "vercel",
    }


@app.get("/")
def root():
    """Serve existing Lumora frontend/index.html (not a placeholder page)."""
    index = os.path.join(_FRONTEND, "index.html")
    if os.path.isfile(index):
        return FileResponse(index, media_type="text/html; charset=utf-8")
    return {
        "status": "ok",
        "service": "Lumora Dev",
        "version": "4.0.0",
        "health": "/health",
        "docs": "/docs",
        "detail": "frontend/index.html not found in deployment bundle",
    }


@app.get("/styles.css")
def styles_css():
    return FileResponse(_frontend_path("styles.css"), media_type="text/css")


@app.get("/script.js")
def script_js():
    return FileResponse(_frontend_path("script.js"), media_type="application/javascript")


@app.get("/darkveil.js")
def darkveil_js():
    return FileResponse(_frontend_path("darkveil.js"), media_type="application/javascript")


@app.get("/favicon.ico")
def favicon():
    return FileResponse(_frontend_path("favicon.ico"), media_type="image/x-icon")


try:
    from backend.api import app as _lumora_app  # noqa: E402

    app = _lumora_app
    logger.info("Loaded backend.api:app for Vercel")
except Exception as e:
    # VERCEL TEST ONLY: keep entrypoint UI + /health if backend fails to import.
    logger.warning("backend.api not loaded (%s); serving frontend from entrypoint", e)

__all__ = ["app"]
