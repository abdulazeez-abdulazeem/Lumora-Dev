"""Browser automation tests (mocked Playwright when browsers unavailable)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_playwright():
    """Stub async Playwright stack so tests run without chromium download."""
    page = AsyncMock()
    page.title = AsyncMock(return_value="Example Domain")
    page.url = "https://example.com/"
    page.goto = AsyncMock()
    page.reload = AsyncMock()
    page.go_back = AsyncMock()
    page.go_forward = AsyncMock()
    page.click = AsyncMock()
    page.hover = AsyncMock()
    page.fill = AsyncMock()
    page.type = AsyncMock()
    page.press = AsyncMock()
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()
    page.select_option = AsyncMock()
    page.set_input_files = AsyncMock()
    page.drag_and_drop = AsyncMock()
    page.evaluate = AsyncMock(return_value=None)
    page.inner_text = AsyncMock(return_value="Hello visible text")
    page.inner_html = AsyncMock(return_value="<html><body>Hello</body></html>")
    page.get_attribute = AsyncMock(return_value="btn")
    page.screenshot = AsyncMock()
    page.close = AsyncMock()
    loc = MagicMock()
    loc.count = AsyncMock(return_value=1)
    loc.nth = MagicMock(return_value=MagicMock(
        evaluate=AsyncMock(side_effect=["button", {"id": "x"}]),
        inner_text=AsyncMock(return_value="OK"),
    ))
    loc.first = MagicMock(screenshot=AsyncMock())
    page.locator = MagicMock(return_value=loc)

    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    context.close = AsyncMock()

    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()

    pw = AsyncMock()
    pw.chromium = MagicMock()
    pw.chromium.launch = AsyncMock(return_value=browser)
    pw.stop = AsyncMock()

    cm = AsyncMock()
    cm.start = AsyncMock(return_value=pw)

    with patch("playwright.async_api.async_playwright", return_value=cm):
        yield {"page": page, "browser": browser, "pw": pw}


def test_launch_and_status(mock_playwright):
    from backend.browser.browser_manager import BrowserManager

    mgr = BrowserManager()
    st = mgr.launch(headless=True)
    assert st.get("running") is True
    assert st.get("tab_count", 0) >= 1
    st2 = mgr.status()
    assert st2.get("running") is True
    mgr.close()


def test_goto(mock_playwright):
    from backend.browser.browser_manager import BrowserManager

    mgr = BrowserManager()
    mgr.launch(headless=True)
    r = mgr.goto("https://example.com")
    assert r.get("ok") is True
    assert "example" in (r.get("url") or "")
    mgr.close()


def test_click_and_type(mock_playwright):
    from backend.browser.browser_manager import BrowserManager
    from backend.browser import actions

    mgr = BrowserManager()
    # share manager singleton
    import backend.browser.browser_manager as bm

    bm._manager = mgr
    mgr.launch(headless=True)
    assert actions.click("#btn").get("ok")
    assert actions.type_text("input", "hello").get("ok")
    mgr.close()
    bm._manager = None


def test_inspector(mock_playwright):
    from backend.browser.browser_manager import BrowserManager
    from backend.browser import inspector
    import backend.browser.browser_manager as bm

    mgr = BrowserManager()
    bm._manager = mgr
    mgr.launch(headless=True)
    info = inspector.page_info()
    assert "title" in info
    text = inspector.visible_text()
    assert "text" in text
    mgr.close()
    bm._manager = None


def test_screenshot(mock_playwright, tmp_path, monkeypatch):
    from backend.browser.browser_manager import BrowserManager
    from backend.browser import screenshots
    import backend.browser.browser_manager as bm

    monkeypatch.setattr(screenshots, "SCREENSHOT_DIR", tmp_path)
    mgr = BrowserManager()
    bm._manager = mgr
    mgr.launch(headless=True)

    # page.screenshot writes nothing — simulate file
    async def fake_shot(*a, **k):
        path = k.get("path") or (a[0] if a else None)
        if path:
            open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)

    mgr._tabs[mgr._active_tab_id].page.screenshot = fake_shot
    r = screenshots.take_screenshot(include_base64=False)
    assert r.get("ok") is True
    assert r.get("filename")
    mgr.close()
    bm._manager = None


def test_recorder_start_stop(tmp_path, monkeypatch):
    from backend.browser import recorder

    monkeypatch.setattr(recorder, "RECORD_DIR", tmp_path)
    r = recorder.start_recording("test")
    assert r.get("recording_id")
    recorder.record_action("goto", {"url": "https://example.com"})
    stopped = recorder.stop_recording()
    assert stopped.get("status") == "stopped"
    assert len(stopped.get("actions", [])) == 1


def test_browser_api_status(client):
    # Without real browser, status should still respond
    r = client.get("/browser/status")
    assert r.status_code == 200
    data = r.json()
    assert "running" in data or "tabs" in data
