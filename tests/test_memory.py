"""Persistent memory tests."""
from __future__ import annotations

from backend import memory as memory_mod


def test_memory_persist(project_root, monkeypatch):
    monkeypatch.setattr(memory_mod, "ROOT", project_root)
    monkeypatch.setattr(memory_mod, "MEMORY_FILE", project_root / ".lumora-memory.json")
    memory_mod.set_architecture("Next.js + FastAPI")
    memory_mod.remember_decision("Use Tailwind", "UI")
    memory_mod.remember_preference("indent", "2")
    memory_mod.record_task_summary("task-1", "Build API", "completed")
    m = memory_mod.get_memory()
    assert "Next.js" in m["architecture"]
    assert m["project_decisions"]
    assert m["user_preferences"].get("indent") == "2"
    assert m["completed_work"]
    # reload
    m2 = memory_mod.get_memory()
    assert m2["architecture"] == m["architecture"]


def test_memory_context(project_root, monkeypatch):
    monkeypatch.setattr(memory_mod, "ROOT", project_root)
    monkeypatch.setattr(memory_mod, "MEMORY_FILE", project_root / ".lumora-memory.json")
    memory_mod.set_architecture("Monolith")
    ctx = memory_mod.memory_context_for_agent()
    assert "Monolith" in ctx
