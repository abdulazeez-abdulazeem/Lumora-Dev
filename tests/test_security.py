"""Local security: crypto, sessions, terminal policy."""
from __future__ import annotations

from backend.security import (
    encrypt_secret, decrypt_secret, evaluate_terminal,
    set_password, clear_password, is_auth_enabled, login, validate_session,
)


def test_encrypt_roundtrip(project_root, monkeypatch):
    import backend.security as sec
    monkeypatch.setattr(sec, "ROOT", project_root)
    monkeypatch.setattr(sec, "KEY_FILE", project_root / ".lumora-secret.key")
    monkeypatch.setattr(sec, "SECURITY_FILE", project_root / ".lumora-security.json")
    token = encrypt_secret("sk-test-key")
    assert token != "sk-test-key"
    assert decrypt_secret(token) == "sk-test-key"


def test_terminal_safe_ls():
    r = evaluate_terminal("ls -la", mode="safe")
    assert r["allowed"] is True


def test_terminal_blocks_unknown():
    r = evaluate_terminal("nmap localhost", mode="safe")
    assert r["allowed"] is False


def test_terminal_destructive_needs_confirm():
    r = evaluate_terminal("rm -rf tmp", mode="safe", confirm=False)
    assert r["destructive"] is True
    assert r["allowed"] is False
    r2 = evaluate_terminal("rm -rf tmp", mode="safe", confirm=True)
    assert r2["allowed"] is True


def test_password_session(project_root, monkeypatch):
    import backend.security as sec
    monkeypatch.setattr(sec, "ROOT", project_root)
    monkeypatch.setattr(sec, "KEY_FILE", project_root / ".lumora-secret.key")
    monkeypatch.setattr(sec, "SECURITY_FILE", project_root / ".lumora-security.json")
    clear_password()
    assert is_auth_enabled() is False
    set_password("secret123")
    assert is_auth_enabled() is True
    tok = login("secret123")
    assert validate_session(tok)
    assert not validate_session("bad-token")
    clear_password()
