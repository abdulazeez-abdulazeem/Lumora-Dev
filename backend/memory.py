"""
Lumora Dev v3 – Persistent project memory
Survives process restarts via JSON file under project root.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent

def _writable_data_path(name: str) -> Path:
    """Prefer project root; on read-only hosts (Vercel /var/task) use /tmp."""
    preferred = ROOT / name
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        # probe write
        probe = preferred.parent / ".lumora-write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        fb = Path("/tmp") / name
        fb.parent.mkdir(parents=True, exist_ok=True)
        return fb

MEMORY_FILE = _writable_data_path(".lumora-memory.json")

_DEFAULT = {
    "architecture": "",
    "coding_preferences": [],
    "user_preferences": {},
    "project_decisions": [],
    "completed_work": [],
    "pending_work": [],
    "previous_tasks": [],
    "notes": [],
    "updated_at": "",
}


def _read() -> dict:
    if not MEMORY_FILE.exists():
        return dict(_DEFAULT)
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        for k, v in _DEFAULT.items():
            data.setdefault(k, v if not isinstance(v, (list, dict)) else type(v)())
        return data
    except (json.JSONDecodeError, ValueError):
        return dict(_DEFAULT)


def _write(data: dict) -> None:
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    MEMORY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_memory() -> dict:
    return _read()


def update_memory(**kwargs: Any) -> dict:
    data = _read()
    for key, value in kwargs.items():
        if key in _DEFAULT and key != "updated_at":
            data[key] = value
    _write(data)
    return data


def append_memory(field: str, item: Any, limit: int = 100) -> dict:
    data = _read()
    if field not in data or not isinstance(data[field], list):
        data[field] = []
    data[field].append(item)
    data[field] = data[field][-limit:]
    _write(data)
    return data


def record_task_summary(task_id: str, title: str, status: str, notes: str = "") -> None:
    entry = {
        "id": task_id,
        "title": title,
        "status": status,
        "notes": notes,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if status == "completed":
        append_memory("completed_work", entry)
    elif status in ("pending", "running", "paused"):
        data = _read()
        # replace existing pending with same id
        pending = [p for p in data.get("pending_work", []) if p.get("id") != task_id]
        if status != "completed":
            pending.append(entry)
        data["pending_work"] = pending[-50:]
        _write(data)
    append_memory("previous_tasks", entry, limit=50)


def remember_decision(decision: str, context: str = "") -> None:
    append_memory("project_decisions", {
        "decision": decision,
        "context": context,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })


def remember_preference(key: str, value: Any) -> None:
    data = _read()
    prefs = data.get("user_preferences") or {}
    prefs[key] = value
    data["user_preferences"] = prefs
    _write(data)


def set_architecture(summary: str) -> None:
    update_memory(architecture=summary)


def memory_context_for_agent() -> str:
    """Compact text block injected into agent system context."""
    m = _read()
    lines = ["### Project Memory"]
    if m.get("architecture"):
        lines.append(f"Architecture: {m['architecture'][:800]}")
    prefs = m.get("coding_preferences") or []
    if prefs:
        lines.append("Coding preferences: " + "; ".join(str(p) for p in prefs[-10:]))
    up = m.get("user_preferences") or {}
    if up:
        lines.append("User preferences: " + ", ".join(f"{k}={v}" for k, v in list(up.items())[-10:]))
    decisions = m.get("project_decisions") or []
    if decisions:
        lines.append("Recent decisions:")
        for d in decisions[-5:]:
            lines.append(f"  - {d.get('decision', '')}")
    pending = m.get("pending_work") or []
    if pending:
        lines.append("Pending work:")
        for p in pending[-5:]:
            lines.append(f"  - [{p.get('status')}] {p.get('title', '')}")
    completed = m.get("completed_work") or []
    if completed:
        lines.append("Recently completed:")
        for c in completed[-5:]:
            lines.append(f"  - {c.get('title', '')}")
    return "\n".join(lines) if len(lines) > 1 else ""
