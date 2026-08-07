"""Orchestrator task + activity tests."""
from __future__ import annotations

from backend.orchestrator import (
    create_task,
    update_task,
    complete_task,
    add_activity,
    get_activity,
    get_recent_tasks,
    get_task,
)


def test_task_lifecycle(project_root, monkeypatch):
    import backend.orchestrator as orch

    monkeypatch.setattr(orch, "TASKS_FILE", project_root / ".tasks.table")
    monkeypatch.setattr(orch, "ACTIVITY_LOG", [])

    tid = create_task("Test task")
    assert tid.startswith("task-")
    t = get_task(tid)
    assert t is not None
    assert t["status"] == "running"

    update_task(tid, progress=50, current_step="halfway")
    complete_task(tid)
    t = get_task(tid)
    assert t["status"] == "completed"
    assert t["progress"] == 100


def test_activity(project_root, monkeypatch):
    import backend.orchestrator as orch

    monkeypatch.setattr(orch, "ACTIVITY_LOG", [])
    add_activity("coder", "wrote file", "step1", 10)
    events = get_activity()
    assert len(events) >= 1
    assert events[-1]["agent"] == "coder"
