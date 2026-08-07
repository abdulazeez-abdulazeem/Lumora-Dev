"""
Build manager – verify deps, run build commands, keep history/logs.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lumora.deployment.build")


class BuildManager:
    def __init__(self, storage_dir: Optional[str] = None):
        self.root = Path(storage_dir or ".lumora-deploy")
        self.root.mkdir(parents=True, exist_ok=True)
        self.history_path = self.root / "builds.json"
        self._history: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.history_path.exists():
            try:
                self._history = json.loads(self.history_path.read_text())
            except Exception:
                self._history = []

    def _save(self) -> None:
        self.history_path.write_text(json.dumps(self._history[-100:], indent=2))

    def check_dependencies(self, project_dir: str) -> Dict[str, Any]:
        root = Path(project_dir)
        issues = []
        checks = {}
        req = root / "requirements.txt"
        pkg = root / "package.json"
        if req.exists():
            checks["requirements.txt"] = True
        else:
            checks["requirements.txt"] = False
            issues.append("No requirements.txt found")
        if pkg.exists():
            checks["package.json"] = True
        else:
            checks["package.json"] = False
        pyproject = root / "pyproject.toml"
        checks["pyproject.toml"] = pyproject.exists()
        return {"ok": len(issues) == 0, "checks": checks, "issues": issues}

    def build(
        self,
        project_dir: str,
        command: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        build_id = uuid.uuid4().hex[:10]
        t0 = time.time()
        dep = self.check_dependencies(project_dir)
        logs: List[str] = [f"[build {build_id}] dependency check: {dep}"]

        # default: no-op verification build for Python projects
        cmd = command
        if not cmd:
            if (Path(project_dir) / "package.json").exists():
                cmd = "npm run build"
            else:
                cmd = "python -c \"print('lumora-build-ok')\""

        status = "success"
        artifact = None
        try:
            r = subprocess.run(
                cmd,
                shell=True,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=300,
                env={**dict(__import__("os").environ), **(env or {})},
            )
            logs.append(r.stdout[-3000:] if r.stdout else "")
            if r.stderr:
                logs.append(r.stderr[-1500:])
            if r.returncode != 0:
                status = "failed"
        except Exception as e:
            status = "failed"
            logs.append(str(e))

        duration = round((time.time() - t0) * 1000, 1)
        record = {
            "build_id": build_id,
            "project_dir": project_dir,
            "command": cmd,
            "status": status,
            "duration_ms": duration,
            "logs": "\n".join(logs)[-5000:],
            "dependencies": dep,
            "artifact": artifact,
            "timestamp": time.time(),
        }
        self._history.append(record)
        self._save()
        return record

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self._history[-limit:])

    def get(self, build_id: str) -> Optional[Dict[str, Any]]:
        for b in reversed(self._history):
            if b.get("build_id") == build_id:
                return b
        return None
