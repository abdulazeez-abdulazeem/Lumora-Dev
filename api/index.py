"""
VERCEL TEST ONLY api/ entry — mirrors root app.py.
Serves existing frontend/ and prefers backend.api when importable.
"""
from __future__ import annotations

import logging
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("LUMORA_RUNTIME", "vercel")

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

logger = logging.getLogger("lumora.vercel")
_FRONTEND = os.path.join(_ROOT, "frontend")

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
    # When backend.api loads successfully, this handler is replaced by that app.
    return {
        "status": "ok",
        "service": "Lumora Dev",
        "version": "4.0.0",
        "runtime": "vercel",
        "backend_api_loaded": False,
        "backend_api_error": _BACKEND_LOAD_ERROR,
        "chat": "/chat",
    }


@app.get("/")
def root():
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


_BACKEND_LOADED = False
_BACKEND_LOAD_ERROR = None
try:
    from backend.api import app as _lumora_app  # noqa: E402

    app = _lumora_app
    _BACKEND_LOADED = True
    logger.info("Loaded backend.api:app for Vercel")
except Exception as e:
    _BACKEND_LOAD_ERROR = f"{type(e).__name__}: {e}"
    logger.warning("backend.api not loaded (%s); serving frontend from entrypoint", e)


# Fallback chat only if backend.api failed to import (avoids opaque 404).
# When backend loads, this app object is replaced entirely — do not re-register.
if not _BACKEND_LOADED:
    @app.post("/chat")
    async def chat_fallback(payload: dict):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "detail": "backend.api failed to load on this runtime",
                "backend_api_error": _BACKEND_LOAD_ERROR,
                "hint": "Check Vercel function logs and ensure backend/** + agent.py are bundled",
            },
        )


__all__ = ["app"]
