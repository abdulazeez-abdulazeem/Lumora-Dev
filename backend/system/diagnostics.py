"""
Diagnostics engine – produce a full system diagnostic report.
"""

from __future__ import annotations

import importlib
import platform
import sys
import time
from typing import Any, Dict, List

from .health import HealthMonitor, HealthStatus


OPTIONAL_DEPS = [
    ("PIL", "Pillow – vision analysis"),
    ("playwright", "Playwright – browser automation"),
    ("pytesseract", "OCR (optional)"),
    ("pypdf", "PDF ingestion (optional)"),
    ("fastapi", "API server"),
    ("langchain_core", "Agent tooling"),
]


class DiagnosticsEngine:
    def __init__(self, health: HealthMonitor | None = None):
        self.health = health or HealthMonitor()

    def run(self) -> Dict[str, Any]:
        health = self.health.check_all()
        deps = self._check_dependencies()
        config_issues = self._check_config()
        failed = [
            c for c in health["components"]
            if c["status"] in (HealthStatus.UNHEALTHY.value, HealthStatus.DEGRADED.value)
        ]
        suggestions = self._suggestions(failed, deps, config_issues)

        return {
            "generated_at": time.time(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "health": health,
            "failed_or_degraded": failed,
            "dependencies": deps,
            "config_issues": config_issues,
            "recovery_actions": self._recovery(failed),
            "suggestions": suggestions,
        }

    def _check_dependencies(self) -> List[Dict[str, Any]]:
        out = []
        for mod, desc in OPTIONAL_DEPS:
            try:
                importlib.import_module(mod)
                out.append({"module": mod, "available": True, "description": desc})
            except ImportError:
                out.append({"module": mod, "available": False, "description": desc})
        return out

    def _check_config(self) -> List[str]:
        issues = []
        import os
        if not os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
            issues.append("No LLM API key in environment (OPENROUTER_API_KEY / OPENAI_API_KEY)")
        return issues

    def _recovery(self, failed: List[Dict]) -> List[str]:
        actions = []
        for c in failed:
            name = c.get("name")
            if name == "browser":
                actions.append("Restart browser manager: POST /browser/close then /browser/launch")
            elif name == "vision":
                actions.append("Install Pillow: pip install Pillow")
            elif name == "knowledge":
                actions.append("Reindex project docs: POST /knowledge/reindex")
            elif name == "git":
                actions.append("Ensure cwd is a git repository")
            elif name == "multiagent":
                actions.append("Reset multi-agent queue via new AgentManager instance")
            else:
                actions.append(f"Inspect logs for subsystem: {name}")
        return actions

    def _suggestions(self, failed, deps, config_issues) -> List[str]:
        tips = []
        for d in deps:
            if not d["available"] and d["module"] in ("PIL", "playwright", "fastapi"):
                tips.append(f"Install missing dependency: {d['module']} ({d['description']})")
        tips.extend(config_issues)
        if failed:
            tips.append(f"{len(failed)} subsystem(s) degraded – review recovery_actions")
        if not tips:
            tips.append("System looks healthy – no immediate actions")
        return tips
