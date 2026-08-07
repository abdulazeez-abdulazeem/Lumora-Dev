"""
System REST API – /system/*
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .orchestrator import get_system_orchestrator

logger = logging.getLogger("lumora.system.router")
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health():
    return get_system_orchestrator().health_report()


@router.get("/status")
async def status():
    return get_system_orchestrator().status()


@router.get("/metrics")
async def metrics():
    return get_system_orchestrator().metrics_report()


@router.get("/telemetry")
async def telemetry():
    return get_system_orchestrator().telemetry_report()


@router.get("/diagnostics")
async def diagnostics():
    return get_system_orchestrator().diagnostics_report()


@router.get("/events")
async def events(topic: Optional[str] = None, limit: int = 50):
    return {"events": get_system_orchestrator().events(topic=topic, limit=limit)}


@router.post("/warmup")
async def warmup():
    return {"success": True, "results": get_system_orchestrator().warm_subsystems()}
