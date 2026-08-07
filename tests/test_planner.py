"""Task planner tests."""
from __future__ import annotations

from backend import planner as planner_mod


def test_plan_lifecycle(project_root, monkeypatch):
    monkeypatch.setattr(planner_mod, "ROOT", project_root)
    monkeypatch.setattr(planner_mod, "PLANS_FILE", project_root / ".lumora-plans.json")
    plan = planner_mod.create_plan("Demo", ["step a", "step b", "step c"])
    pid = plan["id"]
    planner_mod.start_step(pid, 0)
    planner_mod.complete_step(pid, 0)
    prog = planner_mod.plan_progress(pid)
    assert prog["done_steps"] == 1
    planner_mod.pause_plan(pid)
    assert planner_mod.get_plan(pid)["status"] == "paused"
    planner_mod.resume_plan(pid)
    assert planner_mod.get_plan(pid)["status"] == "running"
    planner_mod.complete_step(pid, 1)
    planner_mod.complete_step(pid, 2)
    assert planner_mod.get_plan(pid)["status"] == "completed"


def test_retry(project_root, monkeypatch):
    monkeypatch.setattr(planner_mod, "ROOT", project_root)
    monkeypatch.setattr(planner_mod, "PLANS_FILE", project_root / ".lumora-plans.json")
    plan = planner_mod.create_plan("Retry", ["only"])
    pid = plan["id"]
    planner_mod.start_step(pid, 0)
    planner_mod.fail_step(pid, "boom", 0)
    planner_mod.retry_step(pid, 0)
    assert planner_mod.get_plan(pid)["steps"][0]["status"] == "running"


def test_decompose():
    steps = planner_mod.simple_decompose("fix the login bug and add tests")
    assert len(steps) >= 3
