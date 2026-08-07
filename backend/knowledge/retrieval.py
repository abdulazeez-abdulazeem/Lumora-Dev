"""
Retriever – semantic + keyword search with citations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .vector_store import VectorStore
from .citations import CitationFormatter


class Retriever:
    def __init__(self, store: VectorStore):
        self.store = store
        self.formatter = CitationFormatter()

    def search(
        self,
        query: str,
        top_k: int = 8,
        tags: Optional[List[str]] = None,
        project: Optional[str] = None,
        min_score: float = 0.05,
    ) -> Dict[str, Any]:
        hits = self.store.search(query, top_k=top_k, tags=tags, project=project)
        hits = [h for h in hits if h["score"] >= min_score]
        citations = self.formatter.format_hits(hits)
        return {
            "query": query,
            "count": len(hits),
            "results": hits,
            "citations": citations,
            "context_block": self.formatter.as_context_block(hits),
        }

    def search_project_docs(self, query: str, top_k: int = 6) -> Dict[str, Any]:
        return self.search(query, top_k=top_k, tags=["readme", "changelog", "roadmap", "api", "architecture"])
