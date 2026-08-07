"""
Lumora Dev v3 – Task planner
Breaks work into subtasks; supports pause / resume / retry.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
PLANS_FILE = ROOT / ".lumora-plans.json"


def _read() -> dict:
    if not PLANS_FILE.exists():
        return {"plans": {}}
    try:
        return json.loads(PLANS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {"plans": {}}


def _write(data: dict) -> None:
    PLANS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_plan(title: str, steps: list[str], parent_task_id: str = "") -> dict:
    plan_id = f"plan-{uuid.uuid4().hex[:8]}"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    plan = {
        "id": plan_id,
        "title": title,
        "parent_task_id": parent_task_id,
        "status": "running",  # running | paused | completed | failed
        "created_at": now,
        "updated_at": now,
        "current_step": 0,
        "steps": [
            {
                "index": i,
                "title": s,
                "status": "pending",  # pending | running | done | failed | skipped
                "attempts": 0,
                "error": "",
                "started_at": "",
                "ended_at": "",
            }
            for i, s in enumerate(steps)
        ],
    }
    data = _read()
    data["plans"][plan_id] = plan
    _write(data)
    return plan


def get_plan(plan_id: str) -> Optional[dict]:
    return _read().get("plans", {}).get(plan_id)


def list_plans(limit: int = 20) -> list[dict]:
    plans = list(_read().get("plans", {}).values())
    plans.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return plans[:limit]


def _save_plan(plan: dict) -> dict:
    plan["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    data = _read()
    data["plans"][plan["id"]] = plan
    _write(data)
    return plan


def start_step(plan_id: str, index: int | None = None) -> dict:
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("Plan not found")
    if plan["status"] == "paused":
        plan["status"] = "running"
    idx = plan["current_step"] if index is None else index
    if idx < 0 or idx >= len(plan["steps"]):
        raise ValueError("Invalid step index")
    step = plan["steps"][idx]
    step["status"] = "running"
    step["attempts"] = step.get("attempts", 0) + 1
    step["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    step["error"] = ""
    plan["current_step"] = idx
    return _save_plan(plan)


def complete_step(plan_id: str, index: int | None = None) -> dict:
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("Plan not found")
    idx = plan["current_step"] if index is None else index
    step = plan["steps"][idx]
    step["status"] = "done"
    step["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    # advance
    next_idx = idx + 1
    if next_idx >= len(plan["steps"]):
        plan["status"] = "completed"
        plan["current_step"] = idx
    else:
        plan["current_step"] = next_idx
    return _save_plan(plan)


def fail_step(plan_id: str, error: str, index: int | None = None) -> dict:
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("Plan not found")
    idx = plan["current_step"] if index is None else index
    step = plan["steps"][idx]
    step["status"] = "failed"
    step["error"] = error
    step["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    plan["status"] = "failed"
    return _save_plan(plan)


def retry_step(plan_id: str, index: int | None = None) -> dict:
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("Plan not found")
    idx = plan["current_step"] if index is None else index
    plan["status"] = "running"
    return start_step(plan_id, idx)


def pause_plan(plan_id: str) -> dict:
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("Plan not found")
    plan["status"] = "paused"
    return _save_plan(plan)


def resume_plan(plan_id: str) -> dict:
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("Plan not found")
    if plan["status"] in ("paused", "failed"):
        plan["status"] = "running"
        # if current step failed, set back to running
        idx = plan["current_step"]
        if idx < len(plan["steps"]) and plan["steps"][idx]["status"] == "failed":
            plan["steps"][idx]["status"] = "pending"
    return _save_plan(plan)


def plan_progress(plan_id: str) -> dict:
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError("Plan not found")
    total = len(plan["steps"])
    done = sum(1 for s in plan["steps"] if s["status"] == "done")
    return {
        "id": plan_id,
        "status": plan["status"],
        "current_step": plan["current_step"],
        "total_steps": total,
        "done_steps": done,
        "percent": int(100 * done / total) if total else 0,
        "title": plan["title"],
    }


def simple_decompose(user_message: str) -> list[str]:
    """
    Heuristic planner when LLM is not used for decomposition.
    Produces a reasonable step list from keywords.
    """
    msg = user_message.lower()
    steps = ["Understand request and inspect relevant files"]
    if any(w in msg for w in ("create", "add", "implement", "build", "new")):
        steps.append("Create or update required files")
        steps.append("Validate syntax and imports")
    if any(w in msg for w in ("fix", "bug", "error", "broken")):
        steps.append("Locate the failing code")
        steps.append("Apply fix")
        steps.append("Re-check related files")
    if any(w in msg for w in ("refactor", "clean", "reorganize")):
        steps.append("Map current structure")
        steps.append("Apply refactor in small steps")
        steps.append("Verify behavior unchanged")
    if any(w in msg for w in ("test", "pytest", "jest")):
        steps.append("Run tests")
        steps.append("Fix failures if any")
    if any(w in msg for w in ("git", "commit", "push")):
        steps.append("Review git status")
        steps.append("Stage and commit changes")
    if len(steps) == 1:
        steps.append("Execute the requested changes")
        steps.append("Summarize results")
    else:
        steps.append("Summarize results and update memory")
    return steps
