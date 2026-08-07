"""
Deployment REST API – /deployment/*
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .deployment_manager import get_deployment_manager

logger = logging.getLogger("lumora.deployment.router")
router = APIRouter(prefix="/deployment", tags=["deployment"])


class BuildRequest(BaseModel):
    project_dir: str = "."
    command: Optional[str] = None
    profile: str = "production"


class DeployRequest(BaseModel):
    platform: str = "static"
    project_dir: str = "."
    profile: str = "production"
    config: Dict[str, Any] = Field(default_factory=dict)
    build_first: bool = True
    build_command: Optional[str] = None


class RollbackRequest(BaseModel):
    snapshot_id: str


class WorkflowRequest(BaseModel):
    goal: str
    platform: str = "static"
    project_dir: str = "."


class EnvSetRequest(BaseModel):
    profile: str
    variables: Dict[str, str]


@router.post("/build")
async def build(req: BuildRequest):
    try:
        return get_deployment_manager().build(req.project_dir, command=req.command, profile=req.profile)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/deploy")
async def deploy(req: DeployRequest):
    try:
        return get_deployment_manager().deploy(
            platform=req.platform,
            project_dir=req.project_dir,
            profile=req.profile,
            config=req.config,
            build_first=req.build_first,
            build_command=req.build_command,
        )
    except KeyError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("deploy failed")
        raise HTTPException(500, str(e))


@router.get("/status")
async def status(deployment_id: Optional[str] = None):
    return get_deployment_manager().status(deployment_id)


@router.get("/history")
async def history(limit: int = 20):
    return {"history": get_deployment_manager().history(limit=limit)}


@router.get("/logs")
async def logs(deployment_id: Optional[str] = None, build_id: Optional[str] = None):
    return get_deployment_manager().logs(deployment_id=deployment_id, build_id=build_id)


@router.post("/rollback")
async def rollback(req: RollbackRequest):
    result = get_deployment_manager().rollback(req.snapshot_id)
    if not result.get("success"):
        raise HTTPException(404, result.get("message", "rollback failed"))
    return result


@router.get("/platforms")
async def platforms():
    return {"platforms": get_deployment_manager().platforms()}


@router.get("/snapshots")
async def snapshots(limit: int = 20):
    return {"snapshots": get_deployment_manager().snapshots(limit=limit)}


@router.post("/workflow")
async def workflow(req: WorkflowRequest):
    return get_deployment_manager().multiagent_deploy_workflow(req.goal, platform=req.platform, project_dir=req.project_dir)


@router.get("/environments")
async def environments():
    mgr = get_deployment_manager()
    return {"profiles": mgr.envs.list_profiles(), "detail": {p: mgr.envs.get(p) for p in mgr.envs.list_profiles()}}


@router.post("/environments")
async def set_environment(req: EnvSetRequest):
    get_deployment_manager().envs.set(req.profile, req.variables)
    return {"success": True, "profile": req.profile}
