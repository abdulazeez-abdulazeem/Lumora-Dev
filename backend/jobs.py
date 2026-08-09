"""
Lumora Dev – Long-running job store (file-based).

Used on serverless (Vercel) where a single HTTP request cannot exceed maxDuration.
Jobs persist under a writable directory so status/polling works across invocations
on the same instance, and for local/Docker the same paths work under /tmp or project root.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

def _jobs_dir() -> Path:
    preferred = Path(__file__).resolve().parent.parent / ".lumora-jobs"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        p = Path("/tmp/lumora-jobs")
        p.mkdir(parents=True, exist_ok=True)
        return p


JOBS_DIR = _jobs_dir()

# Heuristics for routing to long-running path (still may run in-request with higher budget)
_LONG_KEYWORDS = (
    "build me", "create a website", "create a landing", "landing page",
    "full stack", "generate a project", "scaffold", "build a website",
    "build an app", "create an app", "make a website", "develop a",
    "coffee shop", "ecommerce", "e-commerce", "dashboard app",
)


def is_long_running_request(message: str) -> bool:
    m = (message or "").lower()
    if len(m) > 400:
        return True
    return any(k in m for k in _LONG_KEYWORDS)


def _path(job_id: str) -> Path:
    safe = "".join(c for c in job_id if c.isalnum() or c in "-_")
    return JOBS_DIR / f"{safe}.json"


def save_job(job: dict) -> None:
    job = dict(job)
    job["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    p = _path(job["id"])
    p.write_text(json.dumps(job, indent=2), encoding="utf-8")


def load_job(job_id: str) -> Optional[dict]:
    p = _path(job_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None


def create_job(message: str, thread_id: str = "", task_id: str = "") -> dict:
    jid = f"job-{uuid.uuid4().hex[:12]}"
    job = {
        "id": jid,
        "task_id": task_id or jid,
        "thread_id": thread_id or jid,
        "message": message,
        "status": "queued",  # queued | running | completed | failed | timed_out
        "response": "",
        "error": "",
        "progress": 0,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_ms": 0,
        "partial": False,
    }
    save_job(job)
    return job


def list_recent_jobs(limit: int = 20) -> list[dict]:
    jobs = []
    for p in sorted(JOBS_DIR.glob("job-*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        try:
            jobs.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return jobs
