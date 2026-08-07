"""Codebase indexer unit tests."""
from __future__ import annotations

from backend.codebase_indexer import index_project, search_index, get_stats


def test_index_and_search(project_root, monkeypatch):
    import backend.codebase_indexer as ci

    monkeypatch.setattr(ci, "ROOT", project_root)
    monkeypatch.setattr(ci, "INDEX_FILE", project_root / ".codebase-index.json")

    idx = index_project(force=True)
    assert idx["stats"]["total_files"] >= 1
    assert idx["stats"]["total_symbols"] >= 1

    results = search_index("hello")
    assert any(r["name"] == "hello" for r in results)

    stats = get_stats()
    assert stats["total_symbols"] >= 1


def test_search_empty_query(project_root, monkeypatch):
    import backend.codebase_indexer as ci

    monkeypatch.setattr(ci, "ROOT", project_root)
    monkeypatch.setattr(ci, "INDEX_FILE", project_root / ".codebase-index.json")
    index_project(force=True)
    results = search_index("")
    assert isinstance(results, list)
