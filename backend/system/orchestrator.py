"""
System Orchestrator – unified entry for health, telemetry, diagnostics,
and light coordination across existing subsystems.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from .health import HealthMonitor
from .diagnostics import DiagnosticsEngine
from .telemetry import TelemetryCollector
from .metrics import MetricsStore
from .event_bus import EventBus, get_event_bus

logger = logging.getLogger("lumora.system")


class SystemOrchestrator:
    def __init__(self):
        self.metrics = MetricsStore()
        self.telemetry = TelemetryCollector(self.metrics)
        self.health = HealthMonitor()
        self.diagnostics = DiagnosticsEngine(self.health)
        self.bus = get_event_bus()
        self.started_at = time.time()
        self.bus.publish("system.start", source="orchestrator", payload={"ts": self.started_at})

    def status(self) -> Dict[str, Any]:
        health = self.health.check_all()
        return {
            "version": "3.0.0-phase3c",
            "uptime_s": round(time.time() - self.started_at, 1),
            "overall_health": health["overall"],
            "components": {c["name"]: c["status"] for c in health["components"]},
            "metrics_summary": {
                "api_requests": self.metrics.snapshot()["counters"].get("api.requests", 0),
                "knowledge_queries": self.metrics.snapshot()["counters"].get("knowledge.queries", 0),
            },
        }

    def health_report(self) -> Dict[str, Any]:
        report = self.health.check_all()
        self.bus.publish("system.health", source="orchestrator", payload={"overall": report["overall"]})
        return report

    def metrics_report(self) -> Dict[str, Any]:
        return self.telemetry.snapshot()

    def telemetry_report(self) -> Dict[str, Any]:
        snap = self.telemetry.snapshot()
        events = [e.model_dump() for e in self.bus.history(limit=30)]
        return {"metrics": snap, "recent_events": events}

    def diagnostics_report(self) -> Dict[str, Any]:
        report = self.diagnostics.run()
        self.bus.publish("system.diagnostics", source="orchestrator", payload={
            "failed": len(report.get("failed_or_degraded", []))
        })
        return report

    def events(self, topic: Optional[str] = None, limit: int = 50) -> list:
        return [e.model_dump() for e in self.bus.history(topic=topic, limit=limit)]

    def record_api_latency(self, path: str, duration_ms: float, status: int = 200) -> None:
        self.telemetry.record_api(path, duration_ms, status)

    def warm_subsystems(self) -> Dict[str, str]:
        """Lightweight warm-up / connectivity check (no behavior change)."""
        results = {}
        try:
            from backend.knowledge.knowledge_manager import get_knowledge_manager
            get_knowledge_manager().status()
            results["knowledge"] = "ok"
        except Exception as e:
            results["knowledge"] = str(e)
        try:
            from backend.multiagent.agent_manager import get_agent_manager
            get_agent_manager().list_agents()
            results["multiagent"] = "ok"
        except Exception as e:
            results["multiagent"] = str(e)
        try:
            from backend.vision.vision_manager import get_vision_manager
            get_vision_manager()
            results["vision"] = "ok"
        except Exception as e:
            results["vision"] = str(e)
        self.bus.publish("system.warmup", source="orchestrator", payload=results)
        return results


_orch: Optional[SystemOrchestrator] = None


def get_system_orchestrator() -> SystemOrchestrator:
    global _orch
    if _orch is None:
        _orch = SystemOrchestrator()
    return _orch
