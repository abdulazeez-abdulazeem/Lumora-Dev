"""Record and replay browser action sequences."""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger("lumora.browser.recorder")

RECORD_DIR = Path(__file__).resolve().parent.parent.parent / ".lumora-browser-recordings"
RECORD_DIR.mkdir(parents=True, exist_ok=True)

_current: dict[str, Any] | None = None


def start_recording(label: str = "") -> dict:
    global _current
    rid = f"rec-{uuid.uuid4().hex[:8]}"
    _current = {
        "id": rid,
        "label": label,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actions": [],
        "status": "recording",
    }
    return {"ok": True, "recording_id": rid}


def record_action(action: str, params: dict) -> None:
    global _current
    if not _current or _current.get("status") != "recording":
        return
    _current["actions"].append({
        "action": action,
        "params": params,
        "at": time.strftime("%H:%M:%S"),
    })


def stop_recording() -> dict:
    global _current
    if not _current:
        return {"ok": False, "error": "No active recording"}
    _current["status"] = "stopped"
    _current["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    path = RECORD_DIR / f"{_current['id']}.json"
    path.write_text(json.dumps(_current, indent=2), encoding="utf-8")
    result = dict(_current)
    _current = None
    result["path"] = str(path)
    return result


def get_recording(recording_id: str) -> dict:
    path = RECORD_DIR / f"{recording_id}.json"
    if not path.exists():
        raise FileNotFoundError(recording_id)
    return json.loads(path.read_text(encoding="utf-8"))


def list_recordings() -> list[dict]:
    out = []
    for p in sorted(RECORD_DIR.glob("rec-*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "id": data.get("id"),
                "label": data.get("label"),
                "actions": len(data.get("actions", [])),
                "status": data.get("status"),
                "started_at": data.get("started_at"),
            })
        except Exception:
            continue
    return out


def replay(recording_id: str) -> dict:
    """Replay a saved recording using current browser session."""
    from backend.browser import actions
    from backend.browser.browser_manager import get_manager

    data = get_recording(recording_id)
    mgr = get_manager()
    if not mgr.status().get("running"):
        mgr.launch(headless=True)

    results = []
    for step in data.get("actions", []):
        action = step.get("action")
        params = step.get("params") or {}
        try:
            if action == "goto":
                r = mgr.goto(params.get("url", ""))
            elif action == "click":
                r = actions.click(params.get("selector", ""), double=params.get("double", False))
            elif action == "type":
                r = actions.type_text(params.get("selector", ""), params.get("text", ""))
            elif action == "press":
                r = actions.press_key(params.get("key", "Enter"), params.get("selector"))
            elif action == "select":
                r = actions.select_option(
                    params.get("selector", ""),
                    value=params.get("value"),
                    label=params.get("label"),
                )
            elif action == "scroll":
                r = actions.scroll(params.get("x", 0), params.get("y", 500))
            elif action == "hover":
                r = actions.hover(params.get("selector", ""))
            else:
                r = {"ok": False, "error": f"Unknown action: {action}"}
            results.append({"action": action, "result": r})
        except Exception as e:
            results.append({"action": action, "error": str(e)})
            break
    return {"recording_id": recording_id, "steps": results, "count": len(results)}
