"""
Environment profiles – development, staging, production.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_PROFILES = {
    "development": {"ENV": "development", "DEBUG": "1"},
    "staging": {"ENV": "staging", "DEBUG": "0"},
    "production": {"ENV": "production", "DEBUG": "0"},
}


class EnvironmentManager:
    def __init__(self, storage_dir: Optional[str] = None):
        self.root = Path(storage_dir or ".lumora-deploy")
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "environments.json"
        self._profiles: Dict[str, Dict[str, str]] = dict(DEFAULT_PROFILES)
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._profiles.update(data)
            except Exception:
                pass

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._profiles, indent=2))

    def list_profiles(self) -> List[str]:
        return list(self._profiles.keys())

    def get(self, name: str) -> Dict[str, str]:
        return dict(self._profiles.get(name, {}))

    def set(self, name: str, variables: Dict[str, str]) -> None:
        self._profiles[name] = {str(k): str(v) for k, v in variables.items()}
        self._save()

    def update(self, name: str, variables: Dict[str, str]) -> Dict[str, str]:
        cur = self.get(name)
        cur.update({str(k): str(v) for k, v in variables.items()})
        self.set(name, cur)
        return cur

    def resolve(self, name: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        env = dict(os.environ)
        env.update(self.get(name))
        if extra:
            env.update(extra)
        return env

    def validate(self, name: str, required: Optional[List[str]] = None) -> Dict[str, Any]:
        profile = self.get(name)
        missing = [k for k in (required or []) if k not in profile and k not in os.environ]
        return {"profile": name, "ok": len(missing) == 0, "missing": missing, "keys": list(profile.keys())}
