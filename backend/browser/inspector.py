"""Page inspection: title, URL, text, HTML, DOM queries, forms, buttons."""
from __future__ import annotations

import logging
from typing import Any

from backend.browser.browser_manager import get_manager

logger = logging.getLogger("lumora.browser.inspector")


def _run(coro, timeout: float = 30.0):
    return get_manager()._run(coro, timeout=timeout)


async def _async_info() -> dict:
    page = get_manager()._active_page()
    title = await page.title()
    url = page.url
    return {"title": title, "url": url}


def page_info() -> dict:
    return _run(_async_info())


async def _async_visible_text(max_chars: int = 8000) -> dict:
    page = get_manager()._active_page()
    text = await page.inner_text("body")
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]
    return {"text": text, "truncated": truncated, "length": len(text)}


def visible_text(max_chars: int = 8000) -> dict:
    return _run(_async_visible_text(max_chars))


async def _async_html(selector: str = "html", max_chars: int = 50000) -> dict:
    page = get_manager()._active_page()
    html = await page.inner_html(selector)
    truncated = len(html) > max_chars
    if truncated:
        html = html[:max_chars]
    return {"html": html, "truncated": truncated, "selector": selector}


def page_html(selector: str = "html", max_chars: int = 50000) -> dict:
    return _run(_async_html(selector, max_chars))


async def _async_query(selector: str, limit: int = 20) -> dict:
    page = get_manager()._active_page()
    loc = page.locator(selector)
    count = await loc.count()
    elements = []
    for i in range(min(count, limit)):
        el = loc.nth(i)
        try:
            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            text = (await el.inner_text())[:200]
            attrs = await el.evaluate(
                """e => {
                    const o = {};
                    for (const a of e.attributes) o[a.name] = a.value;
                    return o;
                }"""
            )
            elements.append({"index": i, "tag": tag, "text": text, "attributes": attrs})
        except Exception as e:
            elements.append({"index": i, "error": str(e)})
    return {"selector": selector, "count": count, "elements": elements}


def find_elements(selector: str, limit: int = 20) -> dict:
    return _run(_async_query(selector, limit))


async def _async_attribute(selector: str, name: str) -> dict:
    page = get_manager()._active_page()
    value = await page.get_attribute(selector, name, timeout=10000)
    return {"selector": selector, "attribute": name, "value": value}


def get_attribute(selector: str, name: str) -> dict:
    return _run(_async_attribute(selector, name))


async def _async_forms() -> dict:
    page = get_manager()._active_page()
    forms = await page.evaluate(
        """() => Array.from(document.forms).map((f, i) => ({
            index: i,
            id: f.id || null,
            name: f.name || null,
            action: f.action || null,
            method: f.method || null,
            fields: Array.from(f.elements).map(el => ({
                tag: el.tagName.toLowerCase(),
                type: el.type || null,
                name: el.name || null,
                id: el.id || null,
                placeholder: el.placeholder || null,
            }))
        }))"""
    )
    return {"forms": forms, "count": len(forms)}


def list_forms() -> dict:
    return _run(_async_forms())


async def _async_buttons() -> dict:
    page = get_manager()._active_page()
    buttons = await page.evaluate(
        """() => Array.from(document.querySelectorAll('button, input[type=button], input[type=submit], a[role=button]'))
            .slice(0, 50)
            .map((el, i) => ({
                index: i,
                tag: el.tagName.toLowerCase(),
                type: el.type || null,
                id: el.id || null,
                name: el.name || null,
                text: (el.innerText || el.value || '').trim().slice(0, 120),
                href: el.href || null,
            }))"""
    )
    return {"buttons": buttons, "count": len(buttons)}


def list_buttons() -> dict:
    return _run(_async_buttons())
