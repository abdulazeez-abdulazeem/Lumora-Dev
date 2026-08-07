"""Tests for Knowledge Engine (Phase 3A)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def mgr(tmp_path):
    from backend.knowledge.knowledge_manager import KnowledgeManager
    return KnowledgeManager(storage_dir=str(tmp_path / "kb"))


def test_import_text(mgr):
    r = mgr.import_text(
        "# Architecture\n\nWe use FastAPI and LangGraph for the agent loop.\n\n## Memory\nPersistent JSON memory.",
        source="test-arch.md",
        title="Architecture",
        tags=["architecture"],
        project="lumora",
    )
    assert r["chunks"] >= 1
    assert r["doc_id"]


def test_chunker_preserves_code():
    from backend.knowledge.chunker import Chunker
    text = "# Title\n\nIntro text.\n\n```python\ndef foo():\n    return 1\n```\n\nMore text after code."
    chunks = Chunker(max_chars=500).chunk("d1", text)
    assert any("def foo" in c.text for c in chunks)


def test_search(mgr):
    mgr.import_text(
        "The authentication module uses JWT tokens and refresh rotation.",
        source="auth.md",
        title="Auth",
        tags=["api"],
    )
    mgr.import_text(
        "Database layer uses SQLite with a safe identifier helper.",
        source="db.md",
        title="DB",
        tags=["database"],
    )
    res = mgr.search("JWT authentication tokens", top_k=3)
    assert res["count"] >= 1
    assert res["results"][0]["score"] > 0
    assert res["citations"]


def test_search_project_docs(mgr):
    mgr.import_text("Roadmap includes knowledge engine and multi-agent.", source="ROADMAP.md",
                    title="Roadmap", tags=["roadmap"])
    res = mgr.search_project_docs("knowledge engine")
    assert "results" in res


def test_delete(mgr):
    r = mgr.import_text("temporary doc", source="tmp.md", title="Tmp")
    assert mgr.delete(r["doc_id"]) is True
    assert mgr.delete("nonexistent") is False


def test_summarize(mgr):
    text = "First sentence about agents. Second sentence about planning. Third about execution loops. Fourth about vision. Fifth about knowledge."
    s = mgr.summarize_document(text=text)
    assert len(s) > 10


def test_list_and_status(mgr):
    mgr.import_text("hello world knowledge", source="h.md", title="Hello")
    docs = mgr.list_documents()
    assert len(docs) >= 1
    st = mgr.status()
    assert st["documents"] >= 1
    assert st["chunks"] >= 1


def test_embeddings_cosine():
    from backend.knowledge.embeddings import EmbeddingProvider
    e = EmbeddingProvider(dim=64)
    a = e.embed("fastapi router knowledge search")
    b = e.embed("fastapi knowledge search router")
    c = e.embed("completely unrelated banana recipe")
    assert EmbeddingProvider.cosine(a, b) > EmbeddingProvider.cosine(a, c)


def test_context_for_execution(mgr):
    mgr.import_text("Always validate SQL identifiers before executing queries.",
                    source="guidelines.md", title="Guidelines", tags=["guidelines"])
    ctx = mgr.context_for_execution("safe SQL query execution")
    assert isinstance(ctx, str)


def test_execution_knowledge_hook(tmp_path, monkeypatch):
    from backend.knowledge.knowledge_manager import KnowledgeManager
    km = KnowledgeManager(storage_dir=str(tmp_path / "kb2"))
    km.import_text("Use Playwright for browser automation tests.", source="browser.md", title="Browser")
    # patch singleton-ish usage via direct call
    from backend.execution.ui_loop import knowledge_context_for_goal
    # may use global manager; still should not crash
    out = knowledge_context_for_goal("browser automation")
    assert isinstance(out, str)


def test_router_import():
    from backend.knowledge.knowledge_router import router
    paths = [getattr(r, "path", "") for r in router.routes]
    assert any("search" in p for p in paths)
    assert any("import" in p for p in paths)
    assert any("list" in p for p in paths)


def test_loader_markdown(tmp_path):
    from backend.knowledge.document_loader import DocumentLoader
    f = tmp_path / "README.md"
    f.write_text("# Lumora\n\nHello knowledge engine.")
    doc = DocumentLoader().load_file(f, project="test")
    assert "Lumora" in doc.meta.title or "README" in doc.meta.title
    assert "Hello" in doc.text


def test_agent_tools_in_source():
    src = (ROOT / "agent.py").read_text()
    for name in ("search_knowledge", "import_documents", "summarize_document", "cite_sources", "search_project_docs"):
        assert name in src


def test_import_project_docs(mgr, tmp_path, monkeypatch):
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n\nThis is the official README for testing knowledge reindex.")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n- Added knowledge engine")
    monkeypatch.chdir(tmp_path)
    r = mgr.import_project_docs(str(tmp_path))
    assert r["imported"] >= 1


def test_loader_html(tmp_path):
    from backend.knowledge.document_loader import DocumentLoader
    f = tmp_path / "page.html"
    f.write_text("<html><body><h1>Title</h1><p>Body content here.</p></body></html>")
    doc = DocumentLoader().load_file(f)
    assert "Body content" in doc.text
    assert "script" not in doc.text.lower() or "Title" in doc.text


def test_loader_json(tmp_path):
    from backend.knowledge.document_loader import DocumentLoader
    f = tmp_path / "openapi.json"
    f.write_text('{"openapi":"3.0.0","info":{"title":"Lumora API"}}')
    doc = DocumentLoader().load_file(f, tags=["api"])
    assert "openapi" in doc.text
    assert "api" in doc.meta.tags


def test_vector_store_stats(mgr):
    st = mgr.store.stats()
    assert "documents" in st and "chunks" in st


def test_citations_format():
    from backend.knowledge.citations import CitationFormatter
    hits = [{"title": "A", "source": "a.md", "score": 0.9, "text": "hello world knowledge"}]
    cites = CitationFormatter().format_hits(hits)
    assert cites[0]["index"] == 1
    block = CitationFormatter().as_context_block(hits)
    assert "Knowledge context" in block


def test_retriever_min_score(mgr):
    mgr.import_text("unique zebra quantum phrase only here", source="z.md", title="Z")
    res = mgr.retriever.search("unique zebra quantum", top_k=3, min_score=0.01)
    assert res["count"] >= 1
