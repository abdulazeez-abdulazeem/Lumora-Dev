"""Multi-file edit session + rollback."""
from __future__ import annotations

from backend import edit_session as edit_mod


def test_write_and_rollback(project_root, monkeypatch):
    monkeypatch.setattr(edit_mod, "ROOT", project_root)
    monkeypatch.setattr(edit_mod, "SESSIONS_DIR", project_root / ".lumora-edits")
    edit_mod.SESSIONS_DIR.mkdir(exist_ok=True)
    (project_root / "orig.txt").write_text("v1", encoding="utf-8")
    sid = edit_mod.begin_session("test")
    edit_mod.record_write(sid, "orig.txt", project_root, "v2")
    assert (project_root / "orig.txt").read_text() == "v2"
    edit_mod.rollback_session(sid, project_root)
    assert (project_root / "orig.txt").read_text() == "v1"
    sess = edit_mod.get_session(sid)
    assert sess["status"] == "rolled_back"


def test_new_file_rollback(project_root, monkeypatch):
    monkeypatch.setattr(edit_mod, "SESSIONS_DIR", project_root / ".lumora-edits")
    edit_mod.SESSIONS_DIR.mkdir(exist_ok=True)
    sid = edit_mod.begin_session()
    edit_mod.record_write(sid, "brand_new.txt", project_root, "x")
    assert (project_root / "brand_new.txt").exists()
    edit_mod.rollback_session(sid, project_root)
    assert not (project_root / "brand_new.txt").exists()
