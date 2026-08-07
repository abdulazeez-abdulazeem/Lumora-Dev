"""
Playwright browser lifecycle: launch, tabs, navigation.
Singleton manager shared across API requests (local single-user).
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("lumora.browser")


@dataclass
class TabInfo:
    id: str
    page: Any  # playwright Page
    title: str = ""
    url: str = "about:blank"


class BrowserManager:
    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._context = None
        self._tabs: dict[str, TabInfo] = {}
        self._active_tab_id: Optional[str] = None
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self.headless: bool = True
        self._started = False

    # ── background event loop (Playwright async API) ─────────────────────
    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop and self._loop.is_running():
            return self._loop

        ready = threading.Event()

        def run_loop() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            ready.set()
            loop.run_forever()

        self._thread = threading.Thread(target=run_loop, name="lumora-browser-loop", daemon=True)
        self._thread.start()
        ready.wait(timeout=10)
        if not self._loop:
            raise RuntimeError("Failed to start browser event loop")
        return self._loop

    def _run(self, coro, timeout: float = 60.0):
        loop = self._ensure_loop()
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        return fut.result(timeout=timeout)

    # ── lifecycle ────────────────────────────────────────────────────────
    async def _async_launch(self, headless: bool = True) -> dict:
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            ) from e

        if self._browser:
            return await self._async_status()

        self.headless = headless
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
        )
        page = await self._context.new_page()
        tab_id = uuid.uuid4().hex[:8]
        self._tabs[tab_id] = TabInfo(id=tab_id, page=page, url="about:blank")
        self._active_tab_id = tab_id
        self._started = True
        logger.info("Browser launched (headless=%s)", headless)
        return await self._async_status()

    def launch(self, headless: bool = True) -> dict:
        with self._lock:
            return self._run(self._async_launch(headless=headless), timeout=90)

    async def _async_close(self) -> dict:
        for tab in list(self._tabs.values()):
            try:
                await tab.page.close()
            except Exception:
                pass
        self._tabs.clear()
        self._active_tab_id = None
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        self._started = False
        logger.info("Browser closed")
        return {"ok": True, "status": "closed"}

    def close(self) -> dict:
        with self._lock:
            if not self._started:
                return {"ok": True, "status": "already_closed"}
            return self._run(self._async_close())

    async def _async_status(self) -> dict:
        tabs = []
        for tid, tab in self._tabs.items():
            try:
                title = await tab.page.title()
                url = tab.page.url
                tab.title = title
                tab.url = url
            except Exception:
                title, url = tab.title, tab.url
            tabs.append({
                "id": tid,
                "title": title,
                "url": url,
                "active": tid == self._active_tab_id,
            })
        return {
            "running": self._started and self._browser is not None,
            "headless": self.headless,
            "active_tab": self._active_tab_id,
            "tabs": tabs,
            "tab_count": len(tabs),
        }

    def status(self) -> dict:
        with self._lock:
            if not self._started:
                return {"running": False, "headless": self.headless, "active_tab": None, "tabs": [], "tab_count": 0}
            try:
                return self._run(self._async_status())
            except Exception as e:
                logger.exception("status failed")
                return {"running": False, "error": str(e), "tabs": [], "tab_count": 0}

    def _active_page(self):
        if not self._active_tab_id or self._active_tab_id not in self._tabs:
            raise RuntimeError("No active browser tab. Call launch first.")
        return self._tabs[self._active_tab_id].page

    # ── navigation ───────────────────────────────────────────────────────
    async def _async_goto(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        page = self._active_page()
        try:
            await page.goto(url, wait_until=wait_until, timeout=30000)
        except Exception as e:
            logger.warning("Navigation issue: %s", e)
            # still return current state
        title = await page.title()
        return {"ok": True, "url": page.url, "title": title}

    def goto(self, url: str, wait_until: str = "domcontentloaded") -> dict:
        with self._lock:
            return self._run(self._async_goto(url, wait_until))

    def refresh(self) -> dict:
        with self._lock:
            return self._run(self._async_refresh())

    async def _async_refresh(self) -> dict:
        page = self._active_page()
        await page.reload(wait_until="domcontentloaded", timeout=30000)
        return {"ok": True, "url": page.url, "title": await page.title()}

    def back(self) -> dict:
        with self._lock:
            return self._run(self._async_back())

    async def _async_back(self) -> dict:
        page = self._active_page()
        await page.go_back(wait_until="domcontentloaded", timeout=15000)
        return {"ok": True, "url": page.url, "title": await page.title()}

    def forward(self) -> dict:
        with self._lock:
            return self._run(self._async_forward())

    async def _async_forward(self) -> dict:
        page = self._active_page()
        await page.go_forward(wait_until="domcontentloaded", timeout=15000)
        return {"ok": True, "url": page.url, "title": await page.title()}

    # ── tabs ─────────────────────────────────────────────────────────────
    def new_tab(self, url: str = "about:blank") -> dict:
        with self._lock:
            return self._run(self._async_new_tab(url))

    async def _async_new_tab(self, url: str) -> dict:
        if not self._context:
            raise RuntimeError("Browser not launched")
        page = await self._context.new_page()
        tab_id = uuid.uuid4().hex[:8]
        self._tabs[tab_id] = TabInfo(id=tab_id, page=page)
        self._active_tab_id = tab_id
        if url and url != "about:blank":
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return await self._async_status()

    def select_tab(self, tab_id: str) -> dict:
        with self._lock:
            if tab_id not in self._tabs:
                raise ValueError(f"Unknown tab: {tab_id}")
            self._active_tab_id = tab_id
            return self._run(self._async_status())

    def close_tab(self, tab_id: str | None = None) -> dict:
        with self._lock:
            return self._run(self._async_close_tab(tab_id))

    async def _async_close_tab(self, tab_id: str | None) -> dict:
        tid = tab_id or self._active_tab_id
        if not tid or tid not in self._tabs:
            raise ValueError("No tab to close")
        tab = self._tabs.pop(tid)
        try:
            await tab.page.close()
        except Exception:
            pass
        if self._active_tab_id == tid:
            self._active_tab_id = next(iter(self._tabs), None)
        if not self._tabs:
            # keep browser open but no pages — create blank
            page = await self._context.new_page()
            new_id = uuid.uuid4().hex[:8]
            self._tabs[new_id] = TabInfo(id=new_id, page=page)
            self._active_tab_id = new_id
        return await self._async_status()


_manager: Optional[BrowserManager] = None


def get_manager() -> BrowserManager:
    global _manager
    if _manager is None:
        _manager = BrowserManager()
    return _manager
