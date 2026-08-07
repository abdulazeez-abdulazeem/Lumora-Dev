"""
Deployment Manager – orchestrates build → deploy → monitor → rollback.
Integrates Multi-Agent Deployment Advisor workflow.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .build_manager import BuildManager
from .environment_manager import EnvironmentManager
from .secrets_manager import SecretsManager
from .monitoring import DeploymentMonitor
from .rollback import RollbackManager
from .platform_router import get_registry, get_platform

logger = logging.getLogger("lumora.deployment")


class DeploymentManager:
    def __init__(self, storage_dir: Optional[str] = None):
        self.root = Path(storage_dir or ".lumora-deploy")
        self.root.mkdir(parents=True, exist_ok=True)
        self.builds = BuildManager(str(self.root))
        self.envs = EnvironmentManager(str(self.root))
        self.secrets = SecretsManager(str(self.root))
        self.monitor = DeploymentMonitor()
        self.rollback_mgr = RollbackManager(str(self.root))
        self.registry = get_registry()
        self._history: List[Dict[str, Any]] = []

    def platforms(self) -> List[Dict[str, Any]]:
        return self.registry.list()

    def build(
        self,
        project_dir: str = ".",
        command: Optional[str] = None,
        profile: str = "production",
    ) -> Dict[str, Any]:
        env = self.envs.resolve(profile)
        result = self.builds.build(project_dir, command=command, env=env)
        try:
            from backend.system.orchestrator import get_system_orchestrator
            get_system_orchestrator().telemetry.record_tool("deployment.build", result.get("duration_ms", 0), result.get("status") == "success")
        except Exception:
            pass
        return result

    def deploy(
        self,
        platform: str = "static",
        project_dir: str = ".",
        profile: str = "production",
        config: Optional[Dict[str, Any]] = None,
        build_first: bool = True,
        build_command: Optional[str] = None,
    ) -> Dict[str, Any]:
        deployment_id = uuid.uuid4().hex[:12]
        t0 = time.time()
        config = dict(config or {})
        # inject secrets if present
        for key in ("VERCEL_TOKEN", "NETLIFY_AUTH_TOKEN", "RAILWAY_TOKEN", "RENDER_API_KEY"):
            if key not in config and self.secrets.get(key):
                config["token"] = self.secrets.get(key)
                break

        build_result = None
        if build_first:
            build_result = self.build(project_dir, command=build_command, profile=profile)
            if build_result.get("status") == "failed":
                rec = {
                    "deployment_id": deployment_id,
                    "platform": platform,
                    "status": "failed",
                    "message": "Build failed",
                    "build": build_result,
                    "timestamp": time.time(),
                }
                self._history.append(rec)
                self.monitor.record(deployment_id, "failed", rec)
                return rec

        adapter = get_platform(platform)
        validation = adapter.validate(config)
        deploy_result = adapter.deploy(project_dir, config, build_artifact=build_result.get("artifact") if build_result else None)

        status = deploy_result.get("status", "unknown")
        record = {
            "deployment_id": deployment_id,
            "platform": platform,
            "profile": profile,
            "status": status,
            "validation": validation,
            "build": build_result,
            "result": deploy_result,
            "duration_ms": round((time.time() - t0) * 1000, 1),
            "timestamp": time.time(),
            "url": deploy_result.get("url"),
        }
        self._history.append(record)
        self.monitor.record(deployment_id, status, record)
        # auto-snapshot successful deploys for rollback
        if status in ("success", "dry_run", "queued"):
            self.rollback_mgr.snapshot(record, label=f"{platform}-{deployment_id}")
        # notify multi-agent / system
        try:
            from backend.system.event_bus import get_event_bus
            get_event_bus().publish("deployment.complete", source="deployment", payload={
                "deployment_id": deployment_id, "platform": platform, "status": status
            })
        except Exception:
            pass
        try:
            from backend.multiagent.agent_manager import get_agent_manager
            get_agent_manager().share_context("deployment_advisor", f"Deployed {platform}: {status} id={deployment_id}")
        except Exception:
            pass
        return record

    def status(self, deployment_id: Optional[str] = None) -> Dict[str, Any]:
        if deployment_id:
            for d in reversed(self._history):
                if d.get("deployment_id") == deployment_id:
                    checks = self.monitor.history(deployment_id)
                    return {**d, "checks": checks}
            return {"error": "not found", "deployment_id": deployment_id}
        latest = self._history[-1] if self._history else None
        return {
            "latest": latest,
            "total": len(self._history),
            "platforms": [p["name"] for p in self.platforms()],
        }

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self._history[-limit:])

    def logs(self, deployment_id: Optional[str] = None, build_id: Optional[str] = None) -> Dict[str, Any]:
        if build_id:
            b = self.builds.get(build_id)
            return {"build_id": build_id, "logs": (b or {}).get("logs", "")}
        if deployment_id:
            for d in reversed(self._history):
                if d.get("deployment_id") == deployment_id:
                    build_logs = ((d.get("build") or {}).get("logs") or "")
                    result_logs = ((d.get("result") or {}).get("logs") or "")
                    return {"deployment_id": deployment_id, "logs": build_logs + "\n" + str(result_logs)}
        # latest
        if self._history:
            return self.logs(deployment_id=self._history[-1]["deployment_id"])
        return {"logs": ""}

    def rollback(self, snapshot_id: str) -> Dict[str, Any]:
        return self.rollback_mgr.rollback(snapshot_id)

    def snapshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.rollback_mgr.list(limit=limit)

    def multiagent_deploy_workflow(self, goal: str, platform: str = "static", project_dir: str = ".") -> Dict[str, Any]:
        """Planner → Build → (test hint) → Review → Deploy → Verify via multi-agent + deploy."""
        workflow: Dict[str, Any] = {"goal": goal, "platform": platform, "steps": []}
        try:
            from backend.multiagent.agent_manager import get_agent_manager
            mgr = get_agent_manager()
            # use deployment_advisor + pipeline subset
            plan = mgr.coordinator.start_goal(
                f"Deploy: {goal}",
                pipeline=[
                    ("planner", "Plan deployment"),
                    ("research", "Check docs/config"),
                    ("testing", "Verify build readiness"),
                    ("review", "Review deploy plan"),
                    ("deployment_advisor", "Advise deployment"),
                ],
            )
            run = mgr.coordinator.run_until_idle(max_steps=10)
            workflow["steps"].append({"multiagent": plan, "run_summary": run.get("queue")})
        except Exception as e:
            workflow["steps"].append({"multiagent_error": str(e)})

        build = self.build(project_dir)
        workflow["steps"].append({"build": {"build_id": build.get("build_id"), "status": build.get("status")}})

        deploy = self.deploy(platform=platform, project_dir=project_dir, build_first=False)
        workflow["steps"].append({"deploy": deploy})

        url = deploy.get("url")
        health = self.monitor.health_check(url)
        workflow["steps"].append({"verify": health})
        workflow["success"] = deploy.get("status") in ("success", "dry_run", "queued")
        return workflow


_mgr: Optional[DeploymentManager] = None


def get_deployment_manager() -> DeploymentManager:
    global _mgr
    if _mgr is None:
        _mgr = DeploymentManager()
    return _mgr
