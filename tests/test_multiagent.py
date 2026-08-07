"""Tests for Multi-Agent Collaboration (Phase 3B)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def mgr():
    from backend.multiagent.agent_manager import AgentManager
    return AgentManager()


def test_list_agents(mgr):
    agents = mgr.list_agents()
    roles = {a["role"] for a in agents}
    assert "planner" in roles
    assert "coding" in roles
    assert "research" in roles
    assert "deployment_advisor" in roles
    assert len(agents) >= 8


def test_assign_and_complete(mgr):
    t = mgr.assign_task("Write hello", "coding", "simple function")
    assert t.task_id
    assert t.status.value == "pending"
    results = mgr.run_ready(max_tasks=1)
    assert results and results[0]["dispatched"]
    updated = mgr.queue.get(t.task_id)
    assert updated.status.value == "completed"


def test_pipeline_dependencies(mgr):
    plan = mgr.coordinator.start_goal("Add health endpoint", skip_roles=["debugging"])
    assert plan["count"] >= 5
    # first task should be ready, others blocked by deps
    ready = mgr.queue.ready_tasks()
    assert len(ready) == 1
    assert ready[0].role == "planner"


def test_run_until_idle(mgr):
    mgr.start("Implement cache layer", auto_run=True, max_steps=15)
    summary = mgr.queue.summary()
    assert summary["total"] >= 5
    completed = summary["by_status"].get("completed", 0)
    assert completed >= 3


def test_messaging(mgr):
    mgr.bus.send("planner", "coding", "Please implement X", topic="delegate")
    inbox = mgr.bus.inbox("coding")
    assert any("implement X" in m.body for m in inbox)
    hist = mgr.bus.history(10)
    assert len(hist) >= 1


def test_shared_context(mgr):
    mgr.share_context("planner", "Use FastAPI patterns")
    snap = mgr.context.snapshot()
    assert any("FastAPI" in n["text"] for n in snap["notes"])
    block = mgr.context.context_block_for_agent("coding", query="fastapi")
    assert "Shared context" in block


def test_delegate_helpers(mgr):
    r = mgr.request_review("auth module")
    assert r.role == "review"
    t = mgr.request_test("auth module")
    assert t.role == "testing"
    s = mgr.request_research("JWT best practices")
    assert s.role == "research"


def test_conflicts(mgr):
    from backend.multiagent.task_queue import Task, TaskStatus
    a = Task(title="edit a", role="coding", status=TaskStatus.IN_PROGRESS, metadata={"file": "app.py"})
    b = Task(title="edit b", role="coding", status=TaskStatus.IN_PROGRESS, metadata={"file": "app.py"})
    mgr.queue.add(a)
    mgr.queue.add(b)
    conf = mgr.queue.conflicts()
    assert len(conf) >= 1


def test_status_api_shape(mgr):
    st = mgr.status()
    assert st["version"] == "3.0.0-phase3b"
    assert "agents" in st and "queue" in st


def test_router_routes():
    from backend.multiagent.multiagent_router import router
    paths = [getattr(r, "path", "") for r in router.routes]
    assert any("start" in p for p in paths)
    assert any("status" in p for p in paths)
    assert any("agents" in p for p in paths)
    assert any("tasks" in p for p in paths)
    assert any("messages" in p for p in paths)


def test_agent_tools_in_source():
    src = (ROOT / "agent.py").read_text()
    for name in ("assign_task", "delegate_work", "share_context", "request_review", "request_test", "request_research"):
        assert name in src


def test_knowledge_integration(mgr, tmp_path):
    from backend.knowledge.knowledge_manager import KnowledgeManager
    km = KnowledgeManager(storage_dir=str(tmp_path / "kb"))
    km.import_text("Always use parameterized queries for SQL.", source="sec.md", title="Security")
    # shared context knowledge_snippet uses global mgr; just ensure no crash
    block = mgr.context.context_block_for_agent("research", query="SQL")
    assert isinstance(block, str)


def test_execution_history_in_context(mgr):
    mgr.context.add_execution_event({"task_id": "abc", "role": "coding", "title": "x"})
    snap = mgr.context.snapshot()
    assert len(snap["execution_log"]) >= 1
