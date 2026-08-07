"""Shared fixtures for Lumora Dev v2.5 tests."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Project root on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """Isolated temp project root for file/git/db tests."""
    # Minimal project structure
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "README.md").write_text("# Test project\n", encoding="utf-8")
    (tmp_path / "sample.py").write_text(
        "def hello():\n    return 'world'\n\nclass Foo:\n    pass\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def client(project_root, monkeypatch):
    """FastAPI TestClient with agent lifespan mocked (no real LLM)."""
    # Point routers at tmp root by patching ROOT where used
    import backend.files_router as fr
    import backend.git_router as gr
    import backend.db_router as dr
    import backend.codebase_indexer as ci
    import backend.orchestrator as orch

    monkeypatch.setattr(fr, "ROOT", project_root)
    monkeypatch.setattr(gr, "ROOT", project_root)
    monkeypatch.setattr(dr, "ROOT", project_root)
    monkeypatch.setattr(ci, "ROOT", project_root)
    monkeypatch.setattr(ci, "INDEX_FILE", project_root / ".codebase-index.json")
    monkeypatch.setattr(orch, "TASKS_FILE", project_root / ".tasks.table")
    monkeypatch.setattr(orch, "ACTIVITY_LOG", [])

    # Avoid loading real agent on lifespan
    import backend.api as api_mod

    def fake_create_agent():
        class FakeAgent:
            def invoke(self, state, config=None):
                from langchain_core.messages import AIMessage

                return {"messages": [AIMessage(content="Test response from fake agent")]}

        return FakeAgent()

    monkeypatch.setattr(api_mod, "create_agent", fake_create_agent)
    # Reset agent singleton
    api_mod._agent = None

    from fastapi.testclient import TestClient

    with TestClient(api_mod.app) as c:
        yield c
