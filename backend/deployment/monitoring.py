"""
Deployment monitoring – status, health checks, uptime tracking.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class DeploymentMonitor:
    def __init__(self):
        self._checks: List[Dict[str, Any]] = []

    def record(self, deployment_id: str, status: str, details: Optional[Dict] = None) -> Dict[str, Any]:
        entry = {
            "deployment_id": deployment_id,
            "status": status,
            "details": details or {},
            "timestamp": time.time(),
        }
        self._checks.append(entry)
        if len(self._checks) > 200:
            self._checks = self._checks[-200:]
        return entry

    def health_check(self, url: Optional[str] = None) -> Dict[str, Any]:
        if not url or url.startswith("file://"):
            return {"ok": True, "status": "local", "url": url, "latency_ms": 0}
        try:
            import urllib.request
            t0 = time.time()
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                code = resp.getcode()
            latency = round((time.time() - t0) * 1000, 1)
            return {"ok": 200 <= code < 400, "status_code": code, "url": url, "latency_ms": latency}
        except Exception as e:
            return {"ok": False, "error": str(e), "url": url}

    def history(self, deployment_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        items = self._checks
        if deployment_id:
            items = [c for c in items if c.get("deployment_id") == deployment_id]
        return items[-limit:]
