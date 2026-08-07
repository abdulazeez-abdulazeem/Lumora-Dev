"""
Knowledge REST API – /knowledge/*
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .knowledge_manager import get_knowledge_manager

logger = logging.getLogger("lumora.knowledge.router")
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class ImportFileRequest(BaseModel):
    path: str
    tags: Optional[List[str]] = None
    project: str = ""


class ImportTextRequest(BaseModel):
    text: str
    source: str = "inline"
    title: str = ""
    tags: Optional[List[str]] = None
    project: str = ""


class ImportDirRequest(BaseModel):
    directory: str
    recursive: bool = True
    tags: Optional[List[str]] = None
    project: str = ""


class SearchRequest(BaseModel):
    query: str
    top_k: int = 8
    tags: Optional[List[str]] = None
    project: Optional[str] = None


class DeleteRequest(BaseModel):
    doc_id: str


@router.post("/import")
async def import_doc(req: ImportFileRequest):
    try:
        mgr = get_knowledge_manager()
        return {"success": True, **mgr.import_file(req.path, tags=req.tags, project=req.project)}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.exception("import failed")
        raise HTTPException(500, str(e))


@router.post("/import-text")
async def import_text(req: ImportTextRequest):
    try:
        mgr = get_knowledge_manager()
        return {"success": True, **mgr.import_text(req.text, source=req.source, title=req.title,
                                                   tags=req.tags, project=req.project)}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/import-dir")
async def import_dir(req: ImportDirRequest):
    try:
        mgr = get_knowledge_manager()
        return {"success": True, **mgr.import_directory(req.directory, recursive=req.recursive,
                                                        tags=req.tags, project=req.project)}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/search")
async def search(req: SearchRequest):
    try:
        mgr = get_knowledge_manager()
        return {"success": True, **mgr.search(req.query, top_k=req.top_k, tags=req.tags, project=req.project)}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/list")
async def list_docs():
    mgr = get_knowledge_manager()
    return {"documents": mgr.list_documents(), **mgr.status()}


@router.post("/delete")
async def delete_doc(req: DeleteRequest):
    mgr = get_knowledge_manager()
    ok = mgr.delete(req.doc_id)
    if not ok:
        raise HTTPException(404, "document not found")
    return {"success": True, "doc_id": req.doc_id}


@router.post("/reindex")
async def reindex(project_root: Optional[str] = None):
    try:
        mgr = get_knowledge_manager()
        return {"success": True, **mgr.reindex_project(project_root)}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/status")
async def status():
    return get_knowledge_manager().status()
