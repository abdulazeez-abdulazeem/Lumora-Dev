"""
Multi-Agent REST API – /multiagent/*
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .agent_manager import get_agent_manager

logger = logging.getLogger("lumora.multiagent.router")
router = APIRouter(prefix="/multiagent", tags=["multiagent"])


class StartRequest(BaseModel):
    goal: str
    auto_run: bool = True
    max_steps: int = 20


class AssignRequest(BaseModel):
    title: str
    role: str
    description: str = ""
    depends_on: Optional[List[str]] = None


class DelegateRequest(BaseModel):
    from_role: str
    to_role: str
    title: str
    description: str = ""


class ShareRequest(BaseModel):
    author: str
    text: str


@router.post("/start")
async def start(req: StartRequest):
    try:
        mgr = get_agent_manager()
        return {"success": True, **mgr.start(req.goal, auto_run=req.auto_run, max_steps=req.max_steps)}
    except Exception as e:
        logger.exception("start failed")
        raise HTTPException(500, str(e))


@router.get("/status")
async def status():
    return get_agent_manager().status()


@router.get("/agents")
async def agents():
    return {"agents": get_agent_manager().list_agents()}


@router.get("/tasks")
async def tasks(status: Optional[str] = None):
    return {"tasks": get_agent_manager().tasks(status=status)}


@router.get("/messages")
async def messages(limit: int = 50):
    return {"messages": get_agent_manager().messages(limit=limit)}


@router.get("/history")
async def history(limit: int = 20):
    return {"history": get_agent_manager().history(limit=limit)}


@router.post("/assign")
async def assign(req: AssignRequest):
    task = get_agent_manager().assign_task(
        title=req.title, role=req.role, description=req.description, depends_on=req.depends_on
    )
    return {"success": True, "task": task.model_dump()}


@router.post("/delegate")
async def delegate(req: DelegateRequest):
    task = get_agent_manager().delegate(req.from_role, req.to_role, req.title, req.description)
    return {"success": True, "task": task.model_dump()}


@router.post("/share")
async def share(req: ShareRequest):
    get_agent_manager().share_context(req.author, req.text)
    return {"success": True}


@router.post("/run-ready")
async def run_ready(max_tasks: int = 5):
    results = get_agent_manager().run_ready(max_tasks=max_tasks)
    return {"success": True, "results": results}
