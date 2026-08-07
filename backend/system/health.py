"""
Health monitor – probe each subsystem and classify status.
"""

from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("lumora.system.health")


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentHealth(BaseModel):
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    latency_ms: float = 0.0
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
    checked_at: float = Field(default_factory=time.time)


class HealthMonitor:
    """Probe existing subsystems without changing their behavior."""

    def check_all(self) -> Dict[str, Any]:
        results: List[ComponentHealth] = []
        results.append(self._check("memory", self._probe_memory))
        results.append(self._check("planner", self._probe_planner))
        results.append(self._check("knowledge", self._probe_knowledge))
        results.append(self._check("browser", self._probe_browser))
        results.append(self._check("vision", self._probe_vision))
        results.append(self._check("execution", self._probe_execution))
        results.append(self._check("multiagent", self._probe_multiagent))
        results.append(self._check("git", self._probe_git))
        results.append(self._check("terminal", self._probe_terminal))
        results.append(self._check("codebase_indexer", self._probe_indexer))

        overall = HealthStatus.HEALTHY
        for c in results:
            if c.status == HealthStatus.UNHEALTHY:
                overall = HealthStatus.UNHEALTHY
                break
            if c.status == HealthStatus.DEGRADED and overall == HealthStatus.HEALTHY:
                overall = HealthStatus.DEGRADED

        return {
            "overall": overall.value,
            "components": [c.model_dump() for c in results],
            "checked_at": time.time(),
        }

    def _check(self, name: str, fn) -> ComponentHealth:
        t0 = time.time()
        try:
            status, message, details = fn()
            return ComponentHealth(
                name=name,
                status=status,
                latency_ms=round((time.time() - t0) * 1000, 2),
                message=message,
                details=details or {},
            )
        except Exception as e:
            logger.debug("health %s failed: %s", name, e)
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=round((time.time() - t0) * 1000, 2),
                message=str(e),
            )

    def _probe_memory(self):
        try:
            from backend import memory as mem_mod
            # module import is enough; optional get_memory
            if hasattr(mem_mod, "get_memory"):
                m = mem_mod.get_memory()
                return HealthStatus.HEALTHY, "memory available", {"type": type(m).__name__}
            return HealthStatus.HEALTHY, "memory module loaded", {}
        except Exception as e:
            return HealthStatus.DEGRADED, str(e), {}

    def _probe_planner(self):
        try:
            from backend import planner  # noqa: F401
            return HealthStatus.HEALTHY, "planner module loaded", {}
        except Exception as e:
            return HealthStatus.DEGRADED, str(e), {}

    def _probe_knowledge(self):
        from backend.knowledge.knowledge_manager import get_knowledge_manager
        st = get_knowledge_manager().status()
        return HealthStatus.HEALTHY, f"docs={st.get('documents', 0)} chunks={st.get('chunks', 0)}", st

    def _probe_browser(self):
        try:
            from backend.browser.browser_manager import get_manager
            mgr = get_manager()
            status = "available"
            if hasattr(mgr, "status"):
                try:
                    s = mgr.status()
                    status = str(s)[:120]
                except Exception:
                    pass
            return HealthStatus.HEALTHY, status, {}
        except Exception as e:
            return HealthStatus.DEGRADED, str(e), {}

    def _probe_vision(self):
        from backend.vision.vision_manager import get_vision_manager, HAS_PIL
        get_vision_manager()
        st = HealthStatus.HEALTHY if HAS_PIL else HealthStatus.DEGRADED
        return st, f"pil={HAS_PIL}", {"pil": HAS_PIL}

    def _probe_execution(self):
        from backend.execution import run_ui_validation_step, knowledge_context_for_goal  # noqa: F401
        return HealthStatus.HEALTHY, "execution hooks available", {}

    def _probe_multiagent(self):
        from backend.multiagent.agent_manager import get_agent_manager
        st = get_agent_manager().status()
        return HealthStatus.HEALTHY, f"agents={len(st.get('agents', []))}", {"queue": st.get("queue")}

    def _probe_git(self):
        import subprocess
        r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return HealthStatus.HEALTHY, "git ok", {"dirty": bool(r.stdout.strip())}
        return HealthStatus.DEGRADED, r.stderr[:200] or "git failed", {}

    def _probe_terminal(self):
        import subprocess
        r = subprocess.run(["echo", "lumora-health"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and "lumora-health" in r.stdout:
            return HealthStatus.HEALTHY, "terminal ok", {}
        return HealthStatus.DEGRADED, "echo failed", {}

    def _probe_indexer(self):
        try:
            from backend import codebase_indexer  # noqa: F401
            return HealthStatus.HEALTHY, "indexer module loaded", {}
        except Exception as e:
            return HealthStatus.DEGRADED, str(e), {}
