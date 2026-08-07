"""
Lumora Dev Knowledge Engine (v3 Phase 3A)

Long-term project knowledge: document ingestion, chunking, semantic search,
citations, and integration with Memory, Planner, Execution, Vision, Agent.
"""

from .knowledge_manager import KnowledgeManager, get_knowledge_manager
from .document_loader import DocumentLoader
from .chunker import Chunker
from .embeddings import EmbeddingProvider
from .vector_store import VectorStore
from .retrieval import Retriever
from .summarizer import Summarizer
from .citations import CitationFormatter

__all__ = [
    "KnowledgeManager",
    "get_knowledge_manager",
    "DocumentLoader",
    "Chunker",
    "EmbeddingProvider",
    "VectorStore",
    "Retriever",
    "Summarizer",
    "CitationFormatter",
]
