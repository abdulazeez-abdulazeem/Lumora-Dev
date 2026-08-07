"""Browser interaction actions: click, type, keys, select, upload, drag, scroll, hover."""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.browser.browser_manager import get_manager

logger = logging.getLogger("lumora.browser.actions")


def _page():
    return get_manager()._active_page()


def _run(coro, timeout: float = 30.0):
    return get_manager()._run(coro, timeout=timeout)


async def _async_click(selector: str, button: str = "left", click_count: int = 1, timeout: float = 10000) -> dict:
    page = _page()
    await page.click(selector, button=button, click_count=click_count, timeout=timeout)
    return {"ok": True, "action": "click", "selector": selector}


def click(selector: str, button: str = "left", double: bool = False) -> dict:
    count = 2 if double else 1
    return _run(_async_click(selector, button=button, click_count=count))


async def _async_hover(selector: str, timeout: float = 10000) -> dict:
    page = _page()
    await page.hover(selector, timeout=timeout)
    return {"ok": True, "action": "hover", "selector": selector}


def hover(selector: str) -> dict:
    return _run(_async_hover(selector))


async def _async_type(selector: str, text: str, clear: bool = True, delay: float = 0) -> dict:
    page = _page()
    if clear:
        await page.fill(selector, text, timeout=10000)
    else:
        await page.type(selector, text, delay=delay, timeout=10000)
    return {"ok": True, "action": "type", "selector": selector, "length": len(text)}


def type_text(selector: str, text: str, clear: bool = True) -> dict:
    return _run(_async_type(selector, text, clear=clear))


async def _async_press(key: str, selector: str | None = None) -> dict:
    page = _page()
    if selector:
        await page.press(selector, key, timeout=10000)
    else:
        await page.keyboard.press(key)
    return {"ok": True, "action": "press", "key": key}


def press_key(key: str, selector: str | None = None) -> dict:
    return _run(_async_press(key, selector))


async def _async_select(selector: str, value: str | None = None, label: str | None = None, index: int | None = None) -> dict:
    page = _page()
    kwargs: dict[str, Any] = {}
    if value is not None:
        kwargs["value"] = value
    elif label is not None:
        kwargs["label"] = label
    elif index is not None:
        kwargs["index"] = index
    else:
        raise ValueError("Provide value, label, or index")
    await page.select_option(selector, **kwargs, timeout=10000)
    return {"ok": True, "action": "select", "selector": selector}


def select_option(selector: str, value: str | None = None, label: str | None = None, index: int | None = None) -> dict:
    return _run(_async_select(selector, value=value, label=label, index=index))


async def _async_upload(selector: str, files: list[str]) -> dict:
    page = _page()
    await page.set_input_files(selector, files, timeout=15000)
    return {"ok": True, "action": "upload", "selector": selector, "files": files}


def upload_files(selector: str, files: list[str]) -> dict:
    return _run(_async_upload(selector, files))


async def _async_drag(source: str, target: str) -> dict:
    page = _page()
    await page.drag_and_drop(source, target, timeout=15000)
    return {"ok": True, "action": "drag", "source": source, "target": target}


def drag_and_drop(source: str, target: str) -> dict:
    return _run(_async_drag(source, target))


async def _async_scroll(x: int = 0, y: int = 0, selector: str | None = None) -> dict:
    page = _page()
    if selector:
        await page.locator(selector).evaluate(
            "(el, dy) => { el.scrollBy(0, dy); }", y
        )
    else:
        await page.evaluate(f"window.scrollBy({int(x)}, {int(y)})")
    return {"ok": True, "action": "scroll", "x": x, "y": y}


def scroll(x: int = 0, y: int = 500, selector: str | None = None) -> dict:
    return _run(_async_scroll(x, y, selector))
