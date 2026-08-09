"""
Lumora Dev – File Explorer endpoints
Full CRUD access to the project directory tree.
"""
from pathlib import Path
import shutil
import subprocess
import os
import json
import time
import httpx
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.providers import list_providers, get_provider
from backend.security import encrypt_secret, decrypt_secret

router = APIRouter()
logger = logging.getLogger("lumora.files")

# Lumora Dev application root (source/runtime — NOT the user project tree)
APP_ROOT = Path(__file__).resolve().parent.parent

# Legacy alias — many helpers still reference ROOT; effective file root is dynamic.
ROOT = APP_ROOT

# Directories to skip entirely (never show in user workspace tree either)
IGNORE_DIRS: set[str] = {
    ".git", "venv", "__pycache__", "node_modules",
    ".cache", ".local", ".agents", ".pythonlibs",
    "_vendor", ".vercel",
}

# Filenames that belong to Lumora runtime — never treat as "user project" at app root
_LUMORA_RUNTIME_NAMES = {
    "Dockerfile", "Procfile", "railway.toml", "render.yaml", "vercel.json",
    "requirements.txt", "requirements-browser.txt", "server.py", "agent.py",
    "app.py", "ROADMAP.md", "SYSTEM.md", "CHANGELOG.md", "CHANGELOG_v3.md",
}


def _user_workspaces_root() -> Path:
    """Writable isolated area for user projects (separate from Lumora source)."""
    import os
    override = os.environ.get("LUMORA_USER_WORKSPACES")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    # Prefer project-local dir when writable (Docker/local); else /tmp on Vercel
    preferred = APP_ROOT / "user-workspaces"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        p = Path("/tmp/lumora-user-workspaces")
        p.mkdir(parents=True, exist_ok=True)
        return p


USER_WORKSPACES_ROOT = _user_workspaces_root()

# Request-scoped active workspace id (set by middleware / dependency)
_active_workspace_id: str | None = None


def set_active_workspace(ws_id: str | None) -> None:
    global _active_workspace_id
    _active_workspace_id = (ws_id or "").strip() or None


def get_active_workspace_id() -> str | None:
    return _active_workspace_id


def effective_root() -> Path:
    """Root for file CRUD: active user workspace, never the full Lumora source tree."""
    ws_id = _active_workspace_id
    if not ws_id:
        # No project selected — empty isolated sandbox (not APP_ROOT)
        empty = USER_WORKSPACES_ROOT / "_empty"
        empty.mkdir(parents=True, exist_ok=True)
        return empty
    root = USER_WORKSPACES_ROOT / ws_id
    root.mkdir(parents=True, exist_ok=True)
    return root

# Specific filenames to hide (e.g. secrets)
IGNORE_FILES: set[str] = {".env"}

# Max characters returned by GET /file (prevents huge responses)
MAX_FILE_READ = 500_000


# ── Request schemas ─────────────────────────────────────────────────────────
class CreateItemRequest(BaseModel):
    path: str = Field(..., description="Relative path for the new item")
    type: str = Field("file", description="'file' or 'folder'")
    content: str = Field("", description="Initial content for new file (ignored for folders)")


class RenameRequest(BaseModel):
    old_path: str = Field(..., description="Current relative path")
    new_path: str = Field(..., description="New relative path")


class DeleteRequest(BaseModel):
    path: str = Field(..., description="Relative path to delete")


class WriteFileRequest(BaseModel):
    path: str = Field(..., description="Relative path of the file to write")
    content: str = Field(..., description="New content for the file")


class TerminalExecRequest(BaseModel):
    command: str = Field(..., description="Shell command to execute")
    cwd: str = Field(".", description="Working directory relative to project root")
    mode: str = Field("safe", description="'safe' (allowlist) or 'full'")
    confirm: bool = Field(False, description="Required for destructive commands")


# ── Helpers ─────────────────────────────────────────────────────────────────
def _safe_path(rel: str) -> Path:
    """
    Resolve a relative path within the *active user workspace* root.
    Never allows access outside that workspace (source repo is isolated).
    """
    safe_root = effective_root().resolve()
    if not rel or rel.strip() in ("", "."):
        return safe_root

    target = (safe_root / rel).resolve()

    try:
        target.relative_to(safe_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path is outside project workspace")

    for part in target.relative_to(safe_root).parts:
        if part in IGNORE_DIRS or part in IGNORE_FILES:
            raise HTTPException(status_code=403, detail=f"Access denied: '{part}' is protected")

    return target


def build_tree(path: Path, rel: str = "") -> list:
    """Recursively build a JSON-serialisable file tree."""
    items: list = []
    try:
        entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return items

    for entry in entries:
        if entry.is_dir() and entry.name in IGNORE_DIRS:
            continue
        if entry.is_file() and entry.name in IGNORE_FILES:
            continue

        rel_path = f"{rel}/{entry.name}" if rel else entry.name

        if entry.is_dir():
            items.append({
                "name": entry.name,
                "path": rel_path,
                "type": "folder",
                "children": build_tree(entry, rel_path),
            })
        else:
            items.append({
                "name": entry.name,
                "path": rel_path,
                "type": "file",
            })

    return items


# ── Read routes ─────────────────────────────────────────────────────────────
@router.get("/files")
def list_files():
    """Return the active *user project* directory tree (not Lumora source)."""
    root = effective_root()
    ws = get_active_workspace_id()
    files = build_tree(root)
    return {
        "files": files,
        "workspace_id": ws or "",
        "workspace_root": str(root),
        "is_user_workspace": bool(ws),
        "hint": None if ws else "No project selected. Create or open a project to see its files.",
    }


@router.get("/file")
def get_file(path: str = Query(..., description="Relative path from project root")):
    """Return the text content of a single file."""
    target = _safe_path(path)

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    if not target.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.exception("Failed to read file %s", path)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    truncated = False
    if len(content) > MAX_FILE_READ:
        content = content[:MAX_FILE_READ]
        truncated = True

    return {"path": path, "content": content, "truncated": truncated}


# ── Write / Create routes ───────────────────────────────────────────────────
@router.post("/files/create")
def create_item(req: CreateItemRequest):
    """Create a new file or folder."""
    target = _safe_path(req.path)
    if target.exists():
        raise HTTPException(status_code=409, detail=f"Already exists: {req.path}")
    try:
        if req.type == "folder":
            target.mkdir(parents=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(req.content, encoding="utf-8")
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/file")
def write_file(req: WriteFileRequest):
    """Create or overwrite a file with new content."""
    target = _safe_path(req.path)
    if target.exists() and target.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is a directory: {req.path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(req.content, encoding="utf-8")
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Rename route ────────────────────────────────────────────────────────────
@router.put("/file")
def rename_file(req: RenameRequest):
    """Rename (or move) a file or folder."""
    old = _safe_path(req.old_path)
    new = _safe_path(req.new_path)
    if not old.exists():
        raise HTTPException(status_code=404, detail=f"Not found: {req.old_path}")
    if new.exists():
        raise HTTPException(status_code=409, detail=f"Already exists: {req.new_path}")
    new.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(old), str(new))
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Delete route ────────────────────────────────────────────────────────────
@router.delete("/file")
def delete_file(req: DeleteRequest):
    """Delete a file or empty folder."""
    target = _safe_path(req.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Not found: {req.path}")
    try:
        if target.is_dir():
            if any(target.iterdir()):
                raise HTTPException(status_code=400, detail="Cannot delete a non-empty folder")
            target.rmdir()
        else:
            target.unlink()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Terminal execution ─────────────────────────────────────────────────
def _rel_cwd(target_cwd: Path) -> str:
    try:
        return str(target_cwd.relative_to(ROOT)) if target_cwd != ROOT else "."
    except ValueError:
        return str(target_cwd)


# ── Settings file helpers ────────────────────────────────────────────────
SETTINGS_FILE = ROOT / ".lumora-settings.json"

def _read_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {"providers": {}, "default_provider": "openrouter", "default_model": "qwen/qwen3-coder:free"}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {"providers": {}, "default_provider": "openrouter", "default_model": "qwen/qwen3-coder:free"}

def _write_settings(data: dict):
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


@router.post("/terminal/exec")
def terminal_exec(req: TerminalExecRequest):
    """Execute a shell command and return the output."""
    target_cwd = ROOT
    if req.cwd and req.cwd != ".":
        try:
            target_cwd = _safe_path(req.cwd)
        except HTTPException:
            target_cwd = ROOT
    if not target_cwd.exists():
        target_cwd = ROOT
    if not target_cwd.is_dir():
        target_cwd = target_cwd.parent

    cmd = req.command.strip()

    # v3 terminal policy
    from backend.security import evaluate_terminal
    policy = evaluate_terminal(cmd, mode=getattr(req, "mode", "safe") or "safe", confirm=bool(getattr(req, "confirm", False)))
    if not policy.get("allowed"):
        return {
            "output": f"Blocked: {policy.get('reason', 'not allowed')}\n",
            "exit_code": 126,
            "cwd": _rel_cwd(target_cwd),
            "policy": policy,
        }

    if cmd in ('clear', 'cls'):
        return {"output": "\033[2J\033[H", "exit_code": 0, "cwd": _rel_cwd(target_cwd)}

    if cmd.startswith('cd '):
        target = cmd[3:].strip().strip('"').strip("'")
        new_cwd = (target_cwd / target).resolve()
        if not str(new_cwd).startswith(str(ROOT.resolve())):
            return {"output": f"cd: permission denied: {target}\n", "exit_code": 1, "cwd": _rel_cwd(target_cwd)}
        if not new_cwd.exists():
            return {"output": f"cd: no such directory: {target}\n", "exit_code": 1, "cwd": _rel_cwd(target_cwd)}
        if not new_cwd.is_dir():
            return {"output": f"cd: not a directory: {target}\n", "exit_code": 1, "cwd": _rel_cwd(target_cwd)}
        os.chdir(str(new_cwd))
        return {"output": "", "exit_code": 0, "cwd": _rel_cwd(new_cwd)}

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(target_cwd),
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "NO_COLOR": "0", "FORCE_COLOR": "1", "TERM": "xterm-256color", "PWD": str(target_cwd)},
        )
        output = result.stdout
        if result.stderr:
            output += result.stderr
        return {"output": output, "exit_code": result.returncode, "cwd": _rel_cwd(target_cwd)}
    except subprocess.TimeoutExpired:
        return {"output": "Command timed out (30s limit)\n", "exit_code": -1, "cwd": _rel_cwd(target_cwd)}
    except Exception as exc:
        logger.exception("Terminal exec failed: %s", cmd[:80])
        return {"output": f"Error: {exc}\n", "exit_code": -1, "cwd": _rel_cwd(target_cwd)}


# ── Settings routes ──────────────────────────────────────────────────────
@router.get("/settings")
def get_settings():
    """Return current user settings (API keys never exposed)."""
    settings = _read_settings()
    providers_list = list_providers()
    # Build provider info with connection status (key presence, not the key itself)
    provider_status = {}
    for p in providers_list:
        env_key = os.getenv(p.key_env_var, "")
        stored_key = settings.get("providers", {}).get(p.id, {}).get("api_key", "")
        has_key = bool(env_key or stored_key)
        provider_status[p.id] = {
            "id": p.id,
            "name": p.name,
            "base_url": p.base_url,
            "docs_url": p.docs_url,
            "key_help_url": p.key_help_url,
            "icon": p.icon,
            "connected": has_key,
            "models_fixed": p.models_fixed if not p.supports_model_list else [],
            "supports_model_list": p.supports_model_list,
        }

    # Load saved models per provider
    for pid in provider_status:
        saved_models = settings.get("providers", {}).get(pid, {}).get("models", [])
        if saved_models:
            provider_status[pid]["cached_models"] = saved_models

    return {
        "providers": provider_status,
        "default_provider": settings.get("default_provider", "openrouter"),
        "default_model": settings.get("default_model", "qwen/qwen3-coder:free"),
    }


class SaveProviderRequest(BaseModel):
    provider_id: str
    api_key: str


@router.post("/settings/provider")
def save_provider(req: SaveProviderRequest):
    """Save an API key for a provider. Key stored in settings JSON and set in env."""
    prov = get_provider(req.provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {req.provider_id}")

    settings = _read_settings()
    settings.setdefault("providers", {})
    settings["providers"].setdefault(req.provider_id, {})
    settings["providers"][req.provider_id]["api_key"] = encrypt_secret(req.api_key) if req.api_key else ""
    _write_settings(settings)

    # Also set in current process environment for immediate use
    os.environ[prov.key_env_var] = req.api_key

    return {"ok": True}


class DeleteProviderRequest(BaseModel):
    provider_id: str


@router.delete("/settings/provider")
def delete_provider(req: DeleteProviderRequest):
    """Remove an API key for a provider."""
    prov = get_provider(req.provider_id)
    settings = _read_settings()
    if req.provider_id in settings.get("providers", {}):
        settings["providers"][req.provider_id].pop("api_key", None)
        settings["providers"][req.provider_id].pop("models", None)
        _write_settings(settings)
    # Clear from env
    if prov and prov.key_env_var in os.environ:
        del os.environ[prov.key_env_var]
    return {"ok": True}


class TestProviderRequest(BaseModel):
    provider_id: str


@router.post("/settings/test")
def test_provider(req: TestProviderRequest):
    """Test a provider connection by listing models or reaching the base URL."""
    prov = get_provider(req.provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {req.provider_id}")

    settings = _read_settings()
    api_key = decrypt_secret(settings.get("providers", {}).get(req.provider_id, {}).get("api_key", ""))
    if not api_key:
        api_key = os.getenv(prov.key_env_var, "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No API key configured for this provider")

    target_url = prov.model_list_url or prov.base_url
    headers = {}
    if prov.model_list_key_header and api_key:
        headers[prov.model_list_key_header] = f"{prov.model_list_key_prefix} {api_key}".strip()

    try:
        resp = httpx.get(target_url, headers=headers, timeout=10)
        if resp.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Provider returned {resp.status_code}")
        return {"ok": True, "status_code": resp.status_code}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Connection failed: {exc}")


@router.post("/settings/models/{provider_id}")
def fetch_models(provider_id: str):
    """Fetch available models from a provider."""
    prov = get_provider(provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_id}")

    if prov.models_fixed:
        models = [{"id": m, "name": m} for m in prov.models_fixed]
        # Cache in settings
        settings = _read_settings()
        settings.setdefault("providers", {}).setdefault(provider_id, {})
        settings["providers"][provider_id]["models"] = models
        _write_settings(settings)
        return {"models": models}

    settings = _read_settings()
    api_key = decrypt_secret(settings.get("providers", {}).get(provider_id, {}).get("api_key", ""))
    if not api_key:
        api_key = os.getenv(prov.key_env_var, "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No API key configured for this provider")

    headers = {}
    if prov.model_list_key_header and api_key:
        headers[prov.model_list_key_header] = f"{prov.model_list_key_prefix} {api_key}".strip()

    try:
        resp = httpx.get(prov.model_list_url, headers=headers, timeout=10)
        if resp.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Provider returned {resp.status_code}")
        data = resp.json()
        # Different providers have different response shapes — normalize to {id, name}
        models = []
        raw = data.get("data") or data.get("models") or []
        for m in raw:
            mid = m.get("id") or m.get("name") or str(m)
            mname = m.get("name") or m.get("display_name") or mid
            models.append({"id": mid, "name": mname})

        # Cache in settings
        settings = _read_settings()
        settings.setdefault("providers", {}).setdefault(provider_id, {})
        settings["providers"][provider_id]["models"] = models
        _write_settings(settings)
        return {"models": models}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch models: {exc}")


class SetDefaultRequest(BaseModel):
    provider: str = Field(default="openrouter")
    model: str = Field(default="qwen/qwen3-coder:free")


@router.post("/settings/default")
def set_default(req: SetDefaultRequest):
    """Set the default provider and model."""
    settings = _read_settings()
    settings["default_provider"] = req.provider
    settings["default_model"] = req.model
    _write_settings(settings)
    return {"ok": True}


# ── Workspace routes ───────────────────────────────────────────────────
def _workspaces_file() -> Path:
    preferred = APP_ROOT / ".workspaces.table"
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        if not preferred.exists():
            preferred.write_text('{"fields":[],"data":[]}', encoding="utf-8")
        return preferred
    except OSError:
        p = Path("/tmp/lumora-workspaces.table")
        if not p.exists():
            p.write_text('{"fields":[],"data":[]}', encoding="utf-8")
        return p

WORKSPACES_FILE = _workspaces_file()


def _read_workspaces() -> dict:
    if not WORKSPACES_FILE.exists():
        return {"fields": [], "data": []}
    try:
        return json.loads(WORKSPACES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {"fields": [], "data": []}

def _write_workspaces(data: dict):
    try:
        WORKSPACES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        alt = Path("/tmp/lumora-workspaces.table")
        alt.write_text(json.dumps(data, indent=2), encoding="utf-8")



@router.get("/workspaces")
def list_workspaces():
    """Return all workspaces."""
    ws = _read_workspaces()
    return {"workspaces": sorted(ws.get("data", []), key=lambda w: w.get("last_opened_at", ""), reverse=True)}


class WorkspaceCreateRequest(BaseModel):
    name: str
    description: str = ""
    language: str = ""
    framework: str = ""
    tags: str = ""
    template: str = ""


@router.post("/workspaces")
def create_workspace(req: WorkspaceCreateRequest):
    """Create a new workspace."""
    ws = _read_workspaces()
    ws_id = req.name.lower().replace(" ", "-").replace(".", "")
    existing = [w for w in ws["data"] if w["id"] == ws_id]
    if existing:
        ws_id = ws_id + "-" + str(len(ws["data"]))
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    icon_map = {"react": "⚛️", "next.js": "▲", "python": "🐍", "fastapi": "🚀", "node.js": "💚", "html": "🌐", "": "📁"}
    # Physical isolated directory for this user project
    ws_dir = USER_WORKSPACES_ROOT / ws_id
    ws_dir.mkdir(parents=True, exist_ok=True)
    # Seed README so the tree is never empty
    readme = ws_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            f"# {req.name}\n\n{req.description or 'User project workspace for Lumora Dev.'}\n",
            encoding="utf-8",
        )
    # HTML template seed
    tpl = (req.template or req.framework or "").lower()
    if tpl in ("html", "html/css/js", "static") and not (ws_dir / "index.html").exists():
        (ws_dir / "index.html").write_text(
            f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\"/>\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
            f"<title>{req.name}</title>\n<link rel=\"stylesheet\" href=\"styles.css\"/>\n</head>\n"
            f"<body>\n  <main>\n    <h1>{req.name}</h1>\n    <p>Start building with Lumora Dev.</p>\n  </main>\n"
            f"  <script src=\"script.js\"></script>\n</body>\n</html>\n",
            encoding="utf-8",
        )
        (ws_dir / "styles.css").write_text(
            "*,*::before,*::after{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;"
            "background:#0a0a0c;color:#f4f4f5;min-height:100vh;display:grid;place-items:center}"
            "main{text-align:center;padding:2rem}h1{font-size:2rem;margin-bottom:.5rem}\n",
            encoding="utf-8",
        )
        (ws_dir / "script.js").write_text("// Project scripts\nconsole.log('Lumora workspace ready');\n", encoding="utf-8")

    ws["data"].append({
        "id": ws_id,
        "name": req.name,
        "description": req.description,
        "path": str(ws_dir),  # absolute path under user-workspaces
        "language": req.language,
        "framework": req.framework,
        "tags": req.tags,
        "favorite": 0,
        "icon": icon_map.get(req.framework.lower(), icon_map.get(req.template.lower(), "📁")),
        "created_at": now,
        "last_opened_at": now,
        "provider": "openrouter",
        "model": "",
        "git_branch": "main",
        "theme": "matte-dark",
    })
    _write_workspaces(ws)
    return {"ok": True, "id": ws_id, "path": str(ws_dir)}


class WorkspaceUpdateRequest(BaseModel):
    name: str = ""
    description: str = ""
    favorite: int = -1
    tags: str = ""
    provider: str = ""
    model: str = ""
    theme: str = ""


@router.put("/workspaces/{ws_id}")
def update_workspace(ws_id: str, req: WorkspaceUpdateRequest):
    """Update workspace metadata."""
    ws = _read_workspaces()
    for row in ws["data"]:
        if row["id"] == ws_id:
            if req.name: row["name"] = req.name
            if req.description: row["description"] = req.description
            if req.favorite >= 0: row["favorite"] = req.favorite
            if req.tags: row["tags"] = req.tags
            if req.provider: row["provider"] = req.provider
            if req.model: row["model"] = req.model
            if req.theme: row["theme"] = req.theme
            row["last_opened_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            _write_workspaces(ws)
            return {"ok": True}
    raise HTTPException(status_code=404, detail="Workspace not found")


@router.delete("/workspaces/{ws_id}")
def delete_workspace(ws_id: str):
    """Delete a workspace entry."""
    ws = _read_workspaces()
    ws["data"] = [w for w in ws["data"] if w["id"] != ws_id]
    _write_workspaces(ws)
    return {"ok": True}


@router.delete("/folder")
def delete_folder(path: str = Query(..., description="Relative path from project root")):
    """
    Compatibility endpoint from Project B: delete an empty folder.
    Prefer DELETE /file with JSON body for unified file/folder delete.
    """
    target = _safe_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {path}")
    if not target.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"'{path}' is a file — use DELETE /file instead."
        )
    contents = list(target.iterdir())
    if contents:
        raise HTTPException(
            status_code=409,
            detail=f"Folder is not empty ({len(contents)} item{'s' if len(contents) != 1 else ''} inside). Delete contents first."
        )
    try:
        target.rmdir()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"path": path, "deleted": True}
