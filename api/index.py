"""
VERCEL TEST ONLY entrypoint.

Defines a top-level FastAPI `app` (required by Vercel static detection).
When backend.api is importable (full GitHub deploy), routes are merged at runtime.
Original backend/api.py is unchanged and remains the source of truth for containers.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("LUMORA_RUNTIME", "vercel")

from fastapi import FastAPI

# Vercel requires a top-level FastAPI() constructor assignment named `app`.
app = FastAPI(
    title="Lumora Dev API",
    description="Temporary Vercel test entry — full app lives in backend.api",
    version="4.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Lumora Dev", "version": "4.0.0", "runtime": "vercel"}


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Lumora Dev",
        "version": "4.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# VERCEL TEST ONLY: try to attach full Lumora app routes when backend is present.
# Does not delete backend.api; container deploys still use backend.api:app directly.
try:
    from backend.api import app as _lumora_app  # noqa: E402

    # Prefer full application object when the package is bundled (GitHub import).
    app = _lumora_app
except Exception:
    # Backend not in this serverless bundle — keep minimal /health above.
    pass

__all__ = ["app"]
