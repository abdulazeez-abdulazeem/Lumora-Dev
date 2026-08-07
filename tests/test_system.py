"""Tests for System Integration & Reliability (Phase 3C)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def orch():
    from backend.system.orchestrator import SystemOrchestrator
    return SystemOrchestrator()


def test_health_check(orch):
    report = orch.health_report()
    assert "overall" in report
    assert "components" in report
    names = {c["name"] for c in report["components"]}
    assert "knowledge" in names
    assert "multiagent" in names
    assert "vision" in names
    assert "memory" in names


def test_status(orch):
    st = orch.status()
    assert st["version"] == "3.0.0-phase3c"
    assert "overall_health" in st
    assert "components" in st


def test_metrics_and_telemetry(orch):
    orch.telemetry.record_tool("search_knowledge", 12.5, True)
    orch.telemetry.record_api("/knowledge/search", 8.0, 200)
    orch.telemetry.record_knowledge_query(5.0, hits=3)
    snap = orch.metrics_report()
    assert snap["counters"].get("tool.search_knowledge.calls", 0) >= 1
    assert "timers" in snap
    tel = orch.telemetry_report()
    assert "metrics" in tel and "recent_events" in tel


def test_diagnostics(orch):
    report = orch.diagnostics_report()
    assert "health" in report
    assert "dependencies" in report
    assert "suggestions" in report
    assert "recovery_actions" in report
    mods = {d["module"] for d in report["dependencies"]}
    assert "fastapi" in mods or "PIL" in mods


def test_event_bus():
    from backend.system.event_bus import EventBus
    bus = EventBus()
    received = []
    bus.subscribe("test.topic", lambda e: received.append(e))
    bus.publish("test.topic", source="unit", payload={"x": 1})
    assert len(received) == 1
    hist = bus.history(topic="test.topic")
    assert len(hist) >= 1


def test_metrics_store():
    from backend.system.metrics import MetricsStore
    m = MetricsStore()
    m.incr("a")
    m.timing("t", 10)
    m.timing("t", 20)
    m.gauge("g", 3.5)
    snap = m.snapshot()
    assert snap["counters"]["a"] == 1
    assert snap["timers"]["t"]["count"] == 2
    assert snap["gauges"]["g"] == 3.5


def test_warmup(orch):
    results = orch.warm_subsystems()
    assert "knowledge" in results
    assert "multiagent" in results


def test_router_routes():
    from backend.system.system_router import router
    paths = [getattr(r, "path", "") for r in router.routes]
    for need in ("health", "status", "metrics", "telemetry", "diagnostics", "events"):
        assert any(need in p for p in paths), need


def test_span_context(orch):
    with orch.telemetry.span("test.span"):
        pass
    snap = orch.metrics_report()
    assert "test.span" in snap["timers"]


def test_integration_knowledge_health(orch):
    report = orch.health_report()
    kn = next(c for c in report["components"] if c["name"] == "knowledge")
    assert kn["status"] in ("healthy", "degraded")


def test_integration_multiagent_health(orch):
    report = orch.health_report()
    ma = next(c for c in report["components"] if c["name"] == "multiagent")
    assert ma["status"] in ("healthy", "degraded")
