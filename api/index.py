"""
VERCEL TEST ONLY entrypoint.

Re-exports backend.api:app when available.
Falls back to a minimal FastAPI app so /health works during partial deploys.
Does not delete or replace the original Lumora architecture.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("LUMORA_RUNTIME", "vercel")

try:
    from backend.api import app  # full Lumora
except Exception as _import_err:  # VERCEL TEST ONLY fallback
    # VERCEL TEST ONLY:
    # Temporarily use a minimal app if backend package is missing from the
    # serverless bundle. Original backend.api remains the real application.
    from fastapi import FastAPI

    app = FastAPI(title="Lumora Dev (Vercel fallback)", version="4.0.0")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "Lumora Dev",
            "version": "4.0.0",
            "runtime": "vercel-fallback",
            "import_error": str(_import_err)[:500],
        }

    @app.get("/")
    def root():
        return health()

__all__ = ["app"]
