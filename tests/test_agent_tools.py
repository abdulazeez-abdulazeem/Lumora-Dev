"""Agent filesystem tool unit tests (no LLM)."""
from __future__ import annotations

import agent as agent_mod


def test_list_files(project_root, monkeypatch):
    monkeypatch.setattr(agent_mod, "PROJECT_ROOT", project_root)
    out = agent_mod.list_files.invoke({"directory": "."})
    assert "README.md" in out or "sample.py" in out


def test_read_write(project_root, monkeypatch):
    monkeypatch.setattr(agent_mod, "PROJECT_ROOT", project_root)
    msg = agent_mod.write_file.invoke({"filepath": "a.txt", "content": "hi"})
    assert "Successfully" in msg
    content = agent_mod.read_file.invoke({"filepath": "a.txt"})
    assert content == "hi"


def test_path_traversal_blocked(project_root, monkeypatch):
    monkeypatch.setattr(agent_mod, "PROJECT_ROOT", project_root)
    out = agent_mod.read_file.invoke({"filepath": "../outside.txt"})
    assert "Error" in out


def test_protected_env_blocked(project_root, monkeypatch):
    monkeypatch.setattr(agent_mod, "PROJECT_ROOT", project_root)
    (project_root / ".env").write_text("SECRET=1", encoding="utf-8")
    out = agent_mod.read_file.invoke({"filepath": ".env"})
    assert "Error" in out
