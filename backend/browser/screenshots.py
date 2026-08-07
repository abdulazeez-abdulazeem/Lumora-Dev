"""Screenshot capture: viewport, full page, element."""
from __future__ import annotations

import base64
import logging
import time
from pathlib import Path

from backend.browser.browser_manager import get_manager

logger = logging.getLogger("lumora.browser.screenshots")

SCREENSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "screenshots"
try:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # VERCEL read-only FS: original path kept above; fall back to /tmp
    SCREENSHOT_DIR = Path("/tmp") / SCREENSHOT_DIR.name
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _run(coro, timeout: float = 30.0):
    return get_manager()._run(coro, timeout=timeout)


async def _async_screenshot(
    full_page: bool = False,
    selector: str | None = None,
    name: str | None = None,
) -> dict:
    page = get_manager()._active_page()
    ts = time.strftime("%Y%m%d-%H%M%S")
    fname = name or f"shot-{ts}.png"
    if not fname.endswith(".png"):
        fname += ".png"
    path = SCREENSHOT_DIR / fname

    if selector:
        loc = page.locator(selector).first
        await loc.screenshot(path=str(path), timeout=15000)
        kind = "element"
    else:
        await page.screenshot(path=str(path), full_page=full_page, timeout=15000)
        kind = "full_page" if full_page else "viewport"

    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return {
        "ok": True,
        "kind": kind,
        "path": str(path.relative_to(path.parents[1])) if path.exists() else str(path),
        "filename": fname,
        "size": len(data),
        "base64_preview": b64[:200] + "…",
        "base64": b64,
    }


def take_screenshot(
    full_page: bool = False,
    selector: str | None = None,
    name: str | None = None,
    include_base64: bool = True,
) -> dict:
    result = _run(_async_screenshot(full_page=full_page, selector=selector, name=name))
    if not include_base64:
        result.pop("base64", None)
        result.pop("base64_preview", None)
    return result
