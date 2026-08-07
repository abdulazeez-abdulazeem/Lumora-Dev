"""
Secrets manager – local encrypted or plain storage for deploy tokens.
Uses Fernet when cryptography is available; otherwise file with restricted mode.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("lumora.deployment.secrets")


class SecretsManager:
    def __init__(self, storage_dir: Optional[str] = None):
        self.root = Path(storage_dir or ".lumora-deploy")
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "secrets.json"
        self._data: Dict[str, str] = {}
        self._fernet = None
        try:
            from cryptography.fernet import Fernet
            key_path = self.root / ".secrets_key"
            if key_path.exists():
                key = key_path.read_bytes()
            else:
                key = Fernet.generate_key()
                key_path.write_bytes(key)
                try:
                    os.chmod(key_path, 0o600)
                except Exception:
                    pass
            self._fernet = Fernet(key)
        except Exception:
            logger.debug("cryptography not available – storing secrets in plain JSON")
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = self.path.read_bytes()
            if self._fernet:
                raw = self._fernet.decrypt(raw)
            self._data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            logger.warning("secrets load failed: %s", e)
            self._data = {}

    def _save(self) -> None:
        payload = json.dumps(self._data).encode("utf-8")
        if self._fernet:
            payload = self._fernet.encrypt(payload)
        self.path.write_bytes(payload)
        try:
            os.chmod(self.path, 0o600)
        except Exception:
            pass

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._save()

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._data.get(key, default)

    def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            self._save()
            return True
        return False

    def list_keys(self) -> list:
        return list(self._data.keys())
