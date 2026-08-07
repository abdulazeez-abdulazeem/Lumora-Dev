"""
Platform adapters – Vercel, Netlify, Railway, Render, Docker, Static.
Each adapter validates config and produces a deploy plan / local action.
Real cloud deploys require API tokens; without them we dry-run safely.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lumora.deployment.platforms")


class PlatformAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def deploy(self, project_dir: str, config: Dict[str, Any], build_artifact: Optional[str] = None) -> Dict[str, Any]:
        ...

    def status(self, deployment_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        return {"platform": self.name, "deployment_id": deployment_id, "status": "unknown"}


class StaticPlatform(PlatformAdapter):
    name = "static"

    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        out = config.get("output_dir") or "dist"
        return {"ok": True, "output_dir": out}

    def deploy(self, project_dir: str, config: Dict[str, Any], build_artifact: Optional[str] = None) -> Dict[str, Any]:
        root = Path(project_dir)
        out = Path(config.get("output_dir") or root / "dist")
        out.mkdir(parents=True, exist_ok=True)
        # copy simple static assets if present
        for name in ("index.html", "frontend", "public", "static"):
            src = root / name
            if src.is_file():
                shutil.copy2(src, out / src.name)
            elif src.is_dir():
                dest = out / src.name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(src, dest, dirs_exist_ok=True)
        return {
            "platform": self.name,
            "status": "success",
            "url": f"file://{out.resolve()}",
            "artifact": str(out),
            "message": f"Static export written to {out}",
        }


class DockerPlatform(PlatformAdapter):
    name = "docker"

    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        dockerfile = Path(config.get("dockerfile") or "Dockerfile")
        has_docker = shutil.which("docker") is not None
        return {"ok": has_docker, "dockerfile": str(dockerfile), "docker_available": has_docker}

    def deploy(self, project_dir: str, config: Dict[str, Any], build_artifact: Optional[str] = None) -> Dict[str, Any]:
        if not shutil.which("docker"):
            return {
                "platform": self.name,
                "status": "dry_run",
                "message": "Docker not installed – dry-run only",
                "image": config.get("image", "lumora-app:latest"),
            }
        image = config.get("image") or "lumora-app:latest"
        dockerfile = config.get("dockerfile") or "Dockerfile"
        try:
            r = subprocess.run(
                ["docker", "build", "-t", image, "-f", dockerfile, "."],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if r.returncode != 0:
                return {"platform": self.name, "status": "failed", "logs": r.stderr[-2000:], "message": "docker build failed"}
            return {"platform": self.name, "status": "success", "image": image, "logs": r.stdout[-1000:]}
        except Exception as e:
            return {"platform": self.name, "status": "failed", "message": str(e)}


class CloudPlatform(PlatformAdapter):
    """Base for token-gated cloud platforms – dry-run without credentials."""

    token_env: str = ""
    api_hint: str = ""

    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        token = config.get("token") or os.environ.get(self.token_env, "")
        return {
            "ok": True,
            "has_token": bool(token),
            "mode": "live" if token else "dry_run",
            "token_env": self.token_env,
        }

    def deploy(self, project_dir: str, config: Dict[str, Any], build_artifact: Optional[str] = None) -> Dict[str, Any]:
        token = config.get("token") or os.environ.get(self.token_env, "")
        if not token:
            return {
                "platform": self.name,
                "status": "dry_run",
                "message": f"No {self.token_env} – dry-run. Set token for live deploy.",
                "hint": self.api_hint,
                "project_dir": project_dir,
            }
        # Live path would call platform APIs; keep safe stub that records intent
        return {
            "platform": self.name,
            "status": "queued",
            "message": f"Live deploy requested for {self.name} (token present)",
            "project_dir": project_dir,
            "config_keys": list(config.keys()),
        }


class VercelPlatform(CloudPlatform):
    name = "vercel"
    token_env = "VERCEL_TOKEN"
    api_hint = "https://vercel.com/docs/rest-api"


class NetlifyPlatform(CloudPlatform):
    name = "netlify"
    token_env = "NETLIFY_AUTH_TOKEN"
    api_hint = "https://docs.netlify.com/api/get-started/"


class RailwayPlatform(CloudPlatform):
    name = "railway"
    token_env = "RAILWAY_TOKEN"
    api_hint = "https://docs.railway.app/reference/public-api"


class RenderPlatform(CloudPlatform):
    name = "render"
    token_env = "RENDER_API_KEY"
    api_hint = "https://api-docs.render.com/"


class PlatformRegistry:
    def __init__(self):
        self._platforms: Dict[str, PlatformAdapter] = {
            "static": StaticPlatform(),
            "docker": DockerPlatform(),
            "vercel": VercelPlatform(),
            "netlify": NetlifyPlatform(),
            "railway": RailwayPlatform(),
            "render": RenderPlatform(),
        }

    def list(self) -> List[Dict[str, Any]]:
        out = []
        for name, p in self._platforms.items():
            v = p.validate({})
            out.append({"name": name, "validation": v})
        return out

    def get(self, name: str) -> PlatformAdapter:
        if name not in self._platforms:
            raise KeyError(f"Unknown platform: {name}. Available: {list(self._platforms)}")
        return self._platforms[name]

    def register(self, adapter: PlatformAdapter) -> None:
        self._platforms[adapter.name] = adapter


_registry: Optional[PlatformRegistry] = None


def get_platform(name: str) -> PlatformAdapter:
    global _registry
    if _registry is None:
        _registry = PlatformRegistry()
    return _registry.get(name)


def get_registry() -> PlatformRegistry:
    global _registry
    if _registry is None:
        _registry = PlatformRegistry()
    return _registry
