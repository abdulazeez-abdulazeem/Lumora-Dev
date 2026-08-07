"""
Knowledge Manager – central API for ingest, search, reindex, project docs.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .chunker import Chunker
from .document_loader import DocumentLoader, LoadedDocument
from .embeddings import EmbeddingProvider
from .retrieval import Retriever
from .summarizer import Summarizer
from .vector_store import VectorStore

logger = logging.getLogger("lumora.knowledge")


class KnowledgeManager:
    def __init__(self, storage_dir: Optional[str] = None):
        root = Path(storage_dir or os.environ.get("LUMORA_KNOWLEDGE_DIR", ".lumora-knowledge"))
        root.mkdir(parents=True, exist_ok=True)
        self.root = root
        self.loader = DocumentLoader()
        self.chunker = Chunker()
        self.embedder = EmbeddingProvider()
        self.store = VectorStore(root / "store.json", embedder=self.embedder)
        self.retriever = Retriever(self.store)
        self.summarizer = Summarizer()

    # ── ingest ──────────────────────────────────────────────────────
    def import_file(
        self,
        path: str,
        tags: Optional[List[str]] = None,
        project: str = "",
    ) -> Dict[str, Any]:
        doc = self.loader.load_file(path, tags=tags, project=project)
        return self._ingest(doc)

    def import_text(
        self,
        text: str,
        source: str = "inline",
        title: str = "",
        tags: Optional[List[str]] = None,
        project: str = "",
    ) -> Dict[str, Any]:
        doc = self.loader.load_text(text, source=source, title=title, tags=tags, project=project)
        return self._ingest(doc)

    def import_directory(
        self,
        directory: str,
        recursive: bool = True,
        tags: Optional[List[str]] = None,
        project: str = "",
        patterns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        docs = self.loader.load_directory(
            directory, recursive=recursive, tags=tags, project=project, patterns=patterns
        )
        results = []
        for d in docs:
            results.append(self._ingest(d))
        return {
            "imported": len(results),
            "documents": results,
            "stats": self.store.stats(),
        }

    def import_project_docs(self, project_root: Optional[str] = None) -> Dict[str, Any]:
        """Auto-index README, CHANGELOG, ROADMAP, docs/, *.md at repo root."""
        root = Path(project_root or Path.cwd())
        patterns = [
            "README*", "CHANGELOG*", "ROADMAP*", "ARCHITECTURE*", "CONTRIBUTING*",
            "docs/**/*.md", "**/*.md",
        ]
        # load known files first
        known = []
        for name in ("README.md", "CHANGELOG.md", "CHANGELOG_v3.md", "ROADMAP.md",
                     "VISION.md", "BROWSER_AUTOMATION.md", "KNOWLEDGE_ENGINE.md",
                     "V3_PHASE2C_REPORT.md", "V3_PHASE3A_REPORT.md"):
            p = root / name
            if p.exists():
                known.append(str(p))
        docs_dir = root / "docs"
        if docs_dir.is_dir():
            known.extend(str(p) for p in docs_dir.rglob("*.md"))
        results = []
        seen = set()
        for path in known:
            if path in seen:
                continue
            seen.add(path)
            try:
                results.append(self.import_file(path, project=root.name))
            except Exception as e:
                logger.warning("import %s failed: %s", path, e)
        # also memory notes if available
        try:
            from backend.memory import get_memory  # type: ignore
            mem = get_memory()
            notes = getattr(mem, "list_notes", lambda: [])()
            if notes:
                blob = "\n".join(str(n) for n in notes[:50])
                results.append(self.import_text(blob, source="project-memory", title="Project Memory",
                                                tags=["memory"], project=root.name))
        except Exception:
            pass
        return {"imported": len(results), "documents": results, "stats": self.store.stats()}

    def _ingest(self, doc: LoadedDocument) -> Dict[str, Any]:
        chunks = self.chunker.chunk(doc.meta.doc_id, doc.text, tags=doc.meta.tags)
        n = self.store.upsert_document(doc.meta.doc_id, doc.meta.model_dump(), chunks)
        return {
            "doc_id": doc.meta.doc_id,
            "title": doc.meta.title,
            "source": doc.meta.source,
            "chunks": n,
            "char_count": doc.meta.char_count,
        }

    # ── search ──────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        top_k: int = 8,
        tags: Optional[List[str]] = None,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.retriever.search(query, top_k=top_k, tags=tags, project=project)

    def search_project_docs(self, query: str, top_k: int = 6) -> Dict[str, Any]:
        return self.retriever.search_project_docs(query, top_k=top_k)

    def summarize_document(self, doc_id: Optional[str] = None, text: Optional[str] = None) -> str:
        if text:
            return self.summarizer.summarize(text)
        if doc_id:
            docs = {d["doc_id"]: d for d in self.store.list_documents()}
            # reconstruct from chunks
            chunks = [
                c for c in self.store._data["chunks"].values()
                if c.get("doc_id") == doc_id
            ]
            chunks.sort(key=lambda x: x.get("index", 0))
            blob = "\n".join(c.get("text", "") for c in chunks)
            return self.summarizer.summarize(blob)
        return ""

    def list_documents(self) -> List[dict]:
        return self.store.list_documents()

    def delete(self, doc_id: str) -> bool:
        return self.store.delete_document(doc_id)

    def reindex_project(self, project_root: Optional[str] = None) -> Dict[str, Any]:
        return self.import_project_docs(project_root)

    def status(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "version": "3.0.0-phase3a",
            **self.store.stats(),
            "storage": str(self.root),
        }

    def context_for_execution(self, goal: str, top_k: int = 6) -> str:
        """Called by execution engine before code changes."""
        result = self.search(goal, top_k=top_k)
        return result.get("context_block") or ""


_mgr: Optional[KnowledgeManager] = None


def get_knowledge_manager() -> KnowledgeManager:
    global _mgr
    if _mgr is None:
        _mgr = KnowledgeManager()
    return _mgr
