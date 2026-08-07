"""
VERCEL TEST ONLY root FastAPI entry.

Recognized by Vercel zero-config FastAPI detection.
Does not replace backend/api.py (container source of truth).
"""
from fastapi import FastAPI

app = FastAPI(title="Lumora Dev API", version="4.0.0")


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
    return {
        "status": "ok",
        "service": "Lumora Dev",
        "version": "4.0.0",
        "health": "/health",
        "docs": "/docs",
    }


# When full backend is present (GitHub import), prefer it at runtime.
try:
    import os
    import sys

    _ROOT = os.path.dirname(os.path.abspath(__file__))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from backend.api import app as _lumora_app

    app = _lumora_app
except Exception:
    pass
