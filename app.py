"""
VERCEL TEST ONLY root entrypoint (recognized by Vercel Python runtime).

Re-exports FastAPI `app` from backend.api.
Does not redesign or replace the Lumora Dev architecture.
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend.api import app  # noqa: E402

os.environ.setdefault("LUMORA_RUNTIME", "vercel")

__all__ = ["app"]
