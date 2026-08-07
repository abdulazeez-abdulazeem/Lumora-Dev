"""
Lumora Dev v3 – Multi-file edit sessions with rollback
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = ROOT / ".lumora-edits"
SESSIONS_DIR.mkdir(exist_ok=True)


def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def begin_session(label: str = "") -> str:
    sid = f"edit-{uuid.uuid4().hex[:10]}"
    data = {
        "id": sid,
        "label": label,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "open",  # open | committed | rolled_back
        "files": {},  # path -> {before: str|None, after: str|None, existed: bool}
    }
    _session_path(sid).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return sid


def _load(sid: str) -> dict:
    p = _session_path(sid)
    if not p.exists():
        raise ValueError(f"Edit session not found: {sid}")
    return json.loads(p.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    _session_path(data["id"]).write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_write(session_id: str, rel_path: str, root: Path, new_content: str) -> dict:
    """Snapshot original content then write new content."""
    data = _load(session_id)
    if data["status"] != "open":
        raise ValueError("Session is not open")
    target = (root / rel_path).resolve()
    root_res = root.resolve()
    try:
        target.relative_to(root_res)
    except ValueError:
        raise ValueError("Path outside project root")

    if rel_path not in data["files"]:
        existed = target.exists()
        before = target.read_text(encoding="utf-8", errors="replace") if existed and target.is_file() else None
        data["files"][rel_path] = {"before": before, "after": None, "existed": existed}

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_content, encoding="utf-8")
    data["files"][rel_path]["after"] = new_content
    _save(data)
    return {"path": rel_path, "session_id": session_id, "ok": True}


def validate_session_files(session_id: str, root: Path) -> list[dict]:
    """Basic validation: files exist and are readable UTF-8."""
    data = _load(session_id)
    results = []
    for rel, meta in data["files"].items():
        target = root / rel
        entry = {"path": rel, "ok": True, "error": ""}
        if not target.exists():
            entry["ok"] = False
            entry["error"] = "missing"
        else:
            try:
                target.read_text(encoding="utf-8")
            except Exception as e:
                entry["ok"] = False
                entry["error"] = str(e)
        results.append(entry)
    return results


def commit_session(session_id: str) -> dict:
    data = _load(session_id)
    data["status"] = "committed"
    data["committed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    _save(data)
    return data


def rollback_session(session_id: str, root: Path) -> dict:
    data = _load(session_id)
    if data["status"] == "rolled_back":
        return data
    restored = []
    for rel, meta in data["files"].items():
        target = root / rel
        if meta.get("existed") and meta.get("before") is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(meta["before"], encoding="utf-8")
            restored.append(rel)
        elif not meta.get("existed") and target.exists():
            target.unlink()
            restored.append(rel)
    data["status"] = "rolled_back"
    data["rolled_back_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    data["restored"] = restored
    _save(data)
    return data


def get_session(session_id: str) -> dict:
    return _load(session_id)
