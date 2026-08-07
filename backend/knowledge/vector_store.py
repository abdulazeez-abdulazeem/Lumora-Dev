"""
Simple JSON-backed vector store for chunks + embeddings.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .chunker import Chunk
from .embeddings import EmbeddingProvider

logger = logging.getLogger("lumora.knowledge.store")


class VectorStore:
    def __init__(self, path: str | Path, embedder: Optional[EmbeddingProvider] = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder or EmbeddingProvider()
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {"documents": {}, "chunks": {}}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load vector store: %s", e)
                self._data = {"documents": {}, "chunks": {}}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def upsert_document(self, doc_id: str, meta: dict, chunks: List[Chunk]) -> int:
        with self._lock:
            self._data["documents"][doc_id] = meta
            # remove old chunks for this doc
            self._data["chunks"] = {
                cid: c for cid, c in self._data["chunks"].items() if c.get("doc_id") != doc_id
            }
            texts = [c.text for c in chunks]
            vectors = self.embedder.embed_batch(texts)
            for c, vec in zip(chunks, vectors):
                self._data["chunks"][c.chunk_id] = {
                    **c.model_dump(),
                    "vector": vec,
                }
            self._save()
            return len(chunks)

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id not in self._data["documents"]:
                return False
            del self._data["documents"][doc_id]
            self._data["chunks"] = {
                cid: c for cid, c in self._data["chunks"].items() if c.get("doc_id") != doc_id
            }
            self._save()
            return True

    def list_documents(self) -> List[dict]:
        return list(self._data["documents"].values())

    def search(
        self,
        query: str,
        top_k: int = 8,
        tags: Optional[List[str]] = None,
        project: Optional[str] = None,
    ) -> List[dict]:
        qvec = self.embedder.embed(query)
        results = []
        for cid, rec in self._data["chunks"].items():
            if tags:
                if not any(t in (rec.get("tags") or []) for t in tags):
                    continue
            if project:
                doc = self._data["documents"].get(rec.get("doc_id"), {})
                if doc.get("project") != project:
                    continue
            vec = rec.get("vector") or []
            score = EmbeddingProvider.cosine(qvec, vec)
            # light keyword boost
            q_tokens = set(query.lower().split())
            text_l = (rec.get("text") or "").lower()
            overlap = sum(1 for t in q_tokens if t in text_l)
            score = score + 0.05 * overlap
            results.append({
                "chunk_id": cid,
                "doc_id": rec.get("doc_id"),
                "text": rec.get("text"),
                "heading": rec.get("heading"),
                "score": round(score, 4),
                "tags": rec.get("tags"),
                "source": self._data["documents"].get(rec.get("doc_id"), {}).get("source"),
                "title": self._data["documents"].get(rec.get("doc_id"), {}).get("title"),
            })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def stats(self) -> dict:
        return {
            "documents": len(self._data["documents"]),
            "chunks": len(self._data["chunks"]),
            "path": str(self.path),
        }

    def clear(self) -> None:
        with self._lock:
            self._data = {"documents": {}, "chunks": {}}
            self._save()
