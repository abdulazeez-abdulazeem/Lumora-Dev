"""
Lumora Dev v3 – Local security helpers
- Optional password gate
- Fernet encryption for API keys at rest
- Session tokens for local API access
- Terminal command policy (allowlist + destructive confirm)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

ROOT = Path(__file__).resolve().parent.parent
SECURITY_FILE = ROOT / ".lumora-security.json"
# Machine-local key file (gitignored)
KEY_FILE = ROOT / ".lumora-secret.key"

# ── Fernet key management ───────────────────────────────────────────────────

def _load_or_create_fernet() -> Fernet:
    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        KEY_FILE.write_bytes(key)
        try:
            KEY_FILE.chmod(0o600)
        except OSError:
            pass
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        return ""
    f = _load_or_create_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    f = _load_or_create_fernet()
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        # Legacy plaintext fallback during migration
        return token


# ── Local password + sessions ───────────────────────────────────────────────

def _read_security() -> dict:
    if not SECURITY_FILE.exists():
        return {"password_hash": "", "sessions": {}, "auth_enabled": False}
    try:
        return json.loads(SECURITY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {"password_hash": "", "sessions": {}, "auth_enabled": False}


def _write_security(data: dict) -> None:
    SECURITY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        SECURITY_FILE.chmod(0o600)
    except OSError:
        pass


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, _ = stored.split("$", 1)
    return hmac.compare_digest(_hash_password(password, salt), stored)


def set_password(password: str) -> None:
    data = _read_security()
    data["password_hash"] = _hash_password(password)
    data["auth_enabled"] = True
    _write_security(data)


def clear_password() -> None:
    data = _read_security()
    data["password_hash"] = ""
    data["auth_enabled"] = False
    data["sessions"] = {}
    _write_security(data)


def is_auth_enabled() -> bool:
    return bool(_read_security().get("auth_enabled") and _read_security().get("password_hash"))


def create_session(ttl_seconds: int = 86400 * 7) -> str:
    data = _read_security()
    token = secrets.token_urlsafe(32)
    data.setdefault("sessions", {})[token] = {
        "created": time.time(),
        "expires": time.time() + ttl_seconds,
    }
    # prune expired
    now = time.time()
    data["sessions"] = {k: v for k, v in data["sessions"].items() if v.get("expires", 0) > now}
    _write_security(data)
    return token


def validate_session(token: str | None) -> bool:
    if not is_auth_enabled():
        return True  # auth disabled → open local mode
    if not token:
        return False
    data = _read_security()
    sess = data.get("sessions", {}).get(token)
    if not sess:
        return False
    if sess.get("expires", 0) < time.time():
        data["sessions"].pop(token, None)
        _write_security(data)
        return False
    return True


def login(password: str) -> str:
    data = _read_security()
    if not data.get("auth_enabled"):
        # First-time or disabled: accept and optionally enable
        return create_session()
    if not verify_password(password, data.get("password_hash", "")):
        raise ValueError("Invalid password")
    return create_session()


# ── Terminal command policy ─────────────────────────────────────────────────

# Safe commands (prefix match after strip)
SAFE_COMMANDS = {
    "ls", "dir", "pwd", "cd", "cat", "head", "tail", "less", "more",
    "echo", "printf", "which", "type", "file", "stat", "wc", "find",
    "grep", "rg", "ag", "tree", "du", "df", "date", "whoami", "uname",
    "git", "npm", "npx", "node", "python", "python3", "pip", "pip3",
    "pytest", "tsc", "eslint", "prettier", "cargo", "go", "make",
    "curl", "wget", "mkdir", "touch", "cp", "mv", "true", "false",
    "clear", "cls", "env", "printenv", "sleep",
}

# Destructive patterns requiring explicit confirmation
DESTRUCTIVE_PATTERNS = [
    re.compile(r"\brm\b", re.I),
    re.compile(r"\brmdir\b", re.I),
    re.compile(r"\bdel\b", re.I),
    re.compile(r"\bunlink\b", re.I),
    re.compile(r"\btruncate\b", re.I),
    re.compile(r"\bdrop\s+table\b", re.I),
    re.compile(r"\bgit\s+push\b", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\b", re.I),
    re.compile(r"\bchmod\b", re.I),
    re.compile(r"\bchown\b", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r"\bdd\b", re.I),
    re.compile(r">\s*/", re.I),
    re.compile(r"\bsudo\b", re.I),
    re.compile(r"\bcurl\b.*\|\s*(ba)?sh", re.I),
    re.compile(r"\bwget\b.*\|\s*(ba)?sh", re.I),
]


def classify_command(command: str) -> dict:
    """
    Return {allowed: bool, destructive: bool, reason: str, base: str}
    """
    cmd = (command or "").strip()
    if not cmd:
        return {"allowed": False, "destructive": False, "reason": "Empty command", "base": ""}

    # Extract base command (first token, handle env prefixes simply)
    tokens = cmd.split()
    base = tokens[0]
    if base.endswith("\\") or "=" in base:
        base = tokens[1] if len(tokens) > 1 else base
    base = Path(base).name.lower()

    destructive = any(p.search(cmd) for p in DESTRUCTIVE_PATTERNS)

    # Allowlist check on base
    if base not in SAFE_COMMANDS and not destructive:
        # Still allow if looks like path to known tool
        if base not in SAFE_COMMANDS:
            return {
                "allowed": False,
                "destructive": False,
                "reason": f"Command '{base}' is not on the safe allowlist. Use mode=full or confirm.",
                "base": base,
            }

    if destructive:
        return {
            "allowed": False,  # needs confirm
            "destructive": True,
            "reason": "Destructive command requires confirm=true",
            "base": base,
        }

    return {"allowed": True, "destructive": False, "reason": "ok", "base": base}


def evaluate_terminal(command: str, mode: str = "safe", confirm: bool = False) -> dict:
    """
    mode: 'safe' (allowlist) | 'full' (all except still require confirm for destructive)
    """
    info = classify_command(command)
    if mode == "full":
        if info["destructive"] and not confirm:
            return {**info, "allowed": False}
        return {**info, "allowed": True if not info["destructive"] or confirm else False,
                "reason": info["reason"] if info["destructive"] and not confirm else "ok"}

    # safe mode
    if info["destructive"]:
        if confirm and info["base"] in SAFE_COMMANDS or confirm:
            # allow destructive only with confirm even in safe mode for rm etc.
            return {**info, "allowed": True, "reason": "confirmed"}
        return info
    return info
