"""
Telemetry collector – records tool usage, timings, and subsystem events.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from .metrics import MetricsStore
from .event_bus import get_event_bus


class TelemetryCollector:
    def __init__(self, metrics: Optional[MetricsStore] = None):
        self.metrics = metrics or MetricsStore()
        self.bus = get_event_bus()

    def record_tool(self, tool_name: str, duration_ms: float, success: bool = True) -> None:
        self.metrics.incr(f"tool.{tool_name}.calls")
        self.metrics.timing(f"tool.{tool_name}.duration", duration_ms)
        if not success:
            self.metrics.incr(f"tool.{tool_name}.errors")
        self.bus.publish("telemetry.tool", source=tool_name, payload={
            "duration_ms": duration_ms, "success": success
        })

    def record_api(self, path: str, duration_ms: float, status: int = 200) -> None:
        self.metrics.incr("api.requests")
        self.metrics.timing("api.latency", duration_ms)
        self.metrics.timing(f"api.path.{path.replace('/', '_')}", duration_ms)
        if status >= 400:
            self.metrics.incr("api.errors")

    def record_agent(self, role: str, duration_ms: float) -> None:
        self.metrics.incr(f"agent.{role}.runs")
        self.metrics.timing(f"agent.{role}.duration", duration_ms)

    def record_knowledge_query(self, duration_ms: float, hits: int = 0) -> None:
        self.metrics.incr("knowledge.queries")
        self.metrics.timing("knowledge.query_latency", duration_ms)
        self.metrics.gauge("knowledge.last_hits", float(hits))

    def record_vision(self, action: str, duration_ms: float) -> None:
        self.metrics.incr(f"vision.{action}")
        self.metrics.timing(f"vision.{action}.duration", duration_ms)

    def record_browser(self, action: str, duration_ms: float) -> None:
        self.metrics.incr(f"browser.{action}")
        self.metrics.timing(f"browser.{action}.duration", duration_ms)

    @contextmanager
    def span(self, name: str) -> Generator[None, None, None]:
        t0 = time.time()
        ok = True
        try:
            yield
        except Exception:
            ok = False
            raise
        finally:
            self.metrics.timing(name, (time.time() - t0) * 1000)
            if not ok:
                self.metrics.incr(f"{name}.errors")

    def snapshot(self) -> Dict[str, Any]:
        return self.metrics.snapshot()
