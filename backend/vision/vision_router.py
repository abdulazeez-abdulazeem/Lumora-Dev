"""
Vision REST API – /vision/*
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .vision_manager import get_vision_manager, VisionResult

logger = logging.getLogger("lumora.vision.router")
router = APIRouter(prefix="/vision", tags=["vision"])


def _ok(result: VisionResult) -> Dict[str, Any]:
    return {
        "success": result.success,
        "message": result.message,
        "confidence": result.confidence,
        "data": result.data,
        "issues": result.issues,
        "timestamp": result.timestamp,
    }


class AnalyzeRequest(BaseModel):
    screenshot: str = Field(..., description="Path, base64 or data-URL of screenshot")
    context: Optional[Dict[str, Any]] = None


class OCRRequest(BaseModel):
    screenshot: str
    regions: Optional[List[Dict[str, Any]]] = None


class ValidateRequest(BaseModel):
    screenshot: str
    expectations: Dict[str, Any] = Field(default_factory=dict)


class CompareRequest(BaseModel):
    expected: str
    actual: str


class AnnotateRequest(BaseModel):
    screenshot: str
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    output_name: Optional[str] = None


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    try:
        mgr = get_vision_manager()
        return _ok(mgr.analyze(req.screenshot, context=req.context))
    except Exception as e:
        logger.exception("analyze failed")
        raise HTTPException(500, str(e))


@router.post("/ocr")
async def ocr(req: OCRRequest):
    try:
        mgr = get_vision_manager()
        return _ok(mgr.ocr(req.screenshot, regions=req.regions))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/validate")
async def validate(req: ValidateRequest):
    try:
        mgr = get_vision_manager()
        return _ok(mgr.validate_ui(req.screenshot, req.expectations))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/compare")
async def compare(req: CompareRequest):
    try:
        mgr = get_vision_manager()
        return _ok(mgr.compare(req.expected, req.actual))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/annotate")
async def annotate(req: AnnotateRequest):
    try:
        mgr = get_vision_manager()
        return _ok(mgr.annotate(req.screenshot, req.issues, output_name=req.output_name))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/layout")
async def layout(req: AnalyzeRequest):
    try:
        mgr = get_vision_manager()
        return _ok(mgr.inspect_layout(req.screenshot))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/history")
async def history(limit: int = 20):
    mgr = get_vision_manager()
    return {"history": mgr.history(limit)}


@router.get("/status")
async def status():
    from .vision_manager import HAS_PIL, HAS_TESSERACT
    return {
        "status": "ok",
        "pil": HAS_PIL,
        "tesseract": HAS_TESSERACT,
        "version": "3.0.0-phase2c",
    }
