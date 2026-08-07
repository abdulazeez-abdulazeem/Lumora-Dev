"""
REST API for Lumora Browser Automation.
Prefix: /browser
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.browser.browser_manager import get_manager
from backend.browser import actions, screenshots, inspector, recorder

logger = logging.getLogger("lumora.browser.router")
router = APIRouter(prefix="/browser", tags=["browser"])


def _ok(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("browser action failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── lifecycle ──────────────────────────────────────────────────────────────
class LaunchRequest(BaseModel):
    headless: bool = True


@router.post("/launch")
def browser_launch(req: LaunchRequest = LaunchRequest()):
    return _ok(get_manager().launch, headless=req.headless)


@router.post("/close")
def browser_close():
    return _ok(get_manager().close)


@router.get("/status")
def browser_status():
    return _ok(get_manager().status)


# ── navigation ─────────────────────────────────────────────────────────────
class GotoRequest(BaseModel):
    url: str
    wait_until: str = "domcontentloaded"


@router.post("/goto")
def browser_goto(req: GotoRequest):
    mgr = get_manager()
    if not mgr.status().get("running"):
        mgr.launch(headless=True)
    result = _ok(mgr.goto, req.url, req.wait_until)
    recorder.record_action("goto", {"url": req.url})
    return result


@router.post("/refresh")
def browser_refresh():
    return _ok(get_manager().refresh)


@router.post("/back")
def browser_back():
    return _ok(get_manager().back)


@router.post("/forward")
def browser_forward():
    return _ok(get_manager().forward)


# ── tabs ───────────────────────────────────────────────────────────────────
class NewTabRequest(BaseModel):
    url: str = "about:blank"


@router.post("/tab/new")
def browser_new_tab(req: NewTabRequest = NewTabRequest()):
    return _ok(get_manager().new_tab, req.url)


class SelectTabRequest(BaseModel):
    tab_id: str


@router.post("/tab/select")
def browser_select_tab(req: SelectTabRequest):
    return _ok(get_manager().select_tab, req.tab_id)


@router.post("/tab/close")
def browser_close_tab(tab_id: str | None = None):
    return _ok(get_manager().close_tab, tab_id)


# ── interactions ───────────────────────────────────────────────────────────
class ClickRequest(BaseModel):
    selector: str
    double: bool = False
    button: str = "left"


@router.post("/click")
def browser_click(req: ClickRequest):
    result = _ok(actions.click, req.selector, button=req.button, double=req.double)
    recorder.record_action("click", {"selector": req.selector, "double": req.double})
    return result


class HoverRequest(BaseModel):
    selector: str


@router.post("/hover")
def browser_hover(req: HoverRequest):
    result = _ok(actions.hover, req.selector)
    recorder.record_action("hover", {"selector": req.selector})
    return result


class TypeRequest(BaseModel):
    selector: str
    text: str
    clear: bool = True


@router.post("/type")
def browser_type(req: TypeRequest):
    result = _ok(actions.type_text, req.selector, req.text, clear=req.clear)
    recorder.record_action("type", {"selector": req.selector, "text": req.text})
    return result


class PressRequest(BaseModel):
    key: str
    selector: str | None = None


@router.post("/press")
def browser_press(req: PressRequest):
    result = _ok(actions.press_key, req.key, req.selector)
    recorder.record_action("press", {"key": req.key, "selector": req.selector})
    return result


class SelectRequest(BaseModel):
    selector: str
    value: str | None = None
    label: str | None = None
    index: int | None = None


@router.post("/select")
def browser_select(req: SelectRequest):
    result = _ok(actions.select_option, req.selector, value=req.value, label=req.label, index=req.index)
    recorder.record_action("select", req.model_dump())
    return result


class UploadRequest(BaseModel):
    selector: str
    files: list[str]


@router.post("/upload")
def browser_upload(req: UploadRequest):
    return _ok(actions.upload_files, req.selector, req.files)


class DragRequest(BaseModel):
    source: str
    target: str


@router.post("/drag")
def browser_drag(req: DragRequest):
    return _ok(actions.drag_and_drop, req.source, req.target)


class ScrollRequest(BaseModel):
    x: int = 0
    y: int = 500
    selector: str | None = None


@router.post("/scroll")
def browser_scroll(req: ScrollRequest):
    result = _ok(actions.scroll, req.x, req.y, req.selector)
    recorder.record_action("scroll", {"x": req.x, "y": req.y})
    return result


# ── inspection ─────────────────────────────────────────────────────────────
@router.get("/info")
def browser_info():
    return _ok(inspector.page_info)


@router.get("/text")
def browser_text(max_chars: int = 8000):
    return _ok(inspector.visible_text, max_chars)


@router.get("/html")
def browser_html(selector: str = "html", max_chars: int = 50000):
    return _ok(inspector.page_html, selector, max_chars)


@router.get("/find")
def browser_find(selector: str, limit: int = 20):
    return _ok(inspector.find_elements, selector, limit)


@router.get("/attribute")
def browser_attribute(selector: str, name: str):
    return _ok(inspector.get_attribute, selector, name)


@router.get("/forms")
def browser_forms():
    return _ok(inspector.list_forms)


@router.get("/buttons")
def browser_buttons():
    return _ok(inspector.list_buttons)


# ── screenshots ────────────────────────────────────────────────────────────
class ScreenshotRequest(BaseModel):
    full_page: bool = False
    selector: str | None = None
    name: str | None = None
    include_base64: bool = False


@router.post("/screenshot")
def browser_screenshot(req: ScreenshotRequest = ScreenshotRequest()):
    return _ok(
        screenshots.take_screenshot,
        full_page=req.full_page,
        selector=req.selector,
        name=req.name,
        include_base64=req.include_base64,
    )


# ── recording ──────────────────────────────────────────────────────────────
class RecordStartRequest(BaseModel):
    label: str = ""


@router.post("/record/start")
def record_start(req: RecordStartRequest = RecordStartRequest()):
    return _ok(recorder.start_recording, req.label)


@router.post("/record/stop")
def record_stop():
    return _ok(recorder.stop_recording)


@router.get("/record/list")
def record_list():
    return {"recordings": recorder.list_recordings()}


@router.get("/record/{recording_id}")
def record_get(recording_id: str):
    return _ok(recorder.get_recording, recording_id)


@router.post("/record/{recording_id}/replay")
def record_replay(recording_id: str):
    return _ok(recorder.replay, recording_id)
