"""
VERCEL TEST ONLY entrypoint.

Does NOT replace backend/api.py.
Imports the existing FastAPI `app` so Vercel can run Lumora as a serverless
ASGI function without Docker or a permanent uvicorn process.

Original architecture preserved for Docker / Northflank / Pxxl / Railway / etc.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.api import app  # noqa: E402

os.environ.setdefault("LUMORA_RUNTIME", "vercel")

__all__ = ["app"]
