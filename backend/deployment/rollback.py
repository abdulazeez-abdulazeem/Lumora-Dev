"""
Rollback manager – snapshots and restore points for deployments.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class RollbackManager:
    def __init__(self, storage_dir: Optional[str] = None):
        self.root = Path(storage_dir or ".lumora-deploy")
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "snapshots.json"
        self._snapshots: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._snapshots = json.loads(self.path.read_text())
            except Exception:
                self._snapshots = []

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._snapshots[-50:], indent=2))

    def snapshot(self, deployment: Dict[str, Any], label: str = "") -> Dict[str, Any]:
        snap = {
            "snapshot_id": uuid.uuid4().hex[:10],
            "label": label or deployment.get("deployment_id", "unnamed"),
            "deployment": deployment,
            "timestamp": time.time(),
        }
        self._snapshots.append(snap)
        self._save()
        return snap

    def list(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self._snapshots[-limit:])

    def get(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        for s in reversed(self._snapshots):
            if s.get("snapshot_id") == snapshot_id:
                return s
        return None

    def rollback(self, snapshot_id: str) -> Dict[str, Any]:
        snap = self.get(snapshot_id)
        if not snap:
            return {"success": False, "message": f"Snapshot {snapshot_id} not found"}
        # Record rollback intent; actual platform rollback is platform-specific
        result = {
            "success": True,
            "snapshot_id": snapshot_id,
            "restored": snap.get("deployment"),
            "message": f"Rollback to {snap.get('label')} recorded",
            "timestamp": time.time(),
        }
        self.snapshot(result["restored"] or {}, label=f"rollback-from-{snapshot_id}")
        return result
