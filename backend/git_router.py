"""
Lumora Dev – Git & GitHub Router
Safe subprocess-based Git operations + GitHub API integration.
"""
import subprocess
import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger("lumora.git")

ROOT = Path(__file__).resolve().parent.parent


# ── Helpers ─────────────────────────────────────────────────────────────────
def _run_git(cmd: list[str], cwd: Path | None = None) -> dict:
    """Run a git command and return {ok, output, error}."""
    workdir = str(cwd or ROOT)
    try:
        result = subprocess.run(
            ["git"] + cmd,
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        return {
            "ok": result.returncode == 0,
            "output": (result.stdout + result.stderr).strip(),
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Git command timed out", "exit_code": -1}
    except FileNotFoundError:
        return {"ok": False, "output": "Git is not installed on this system", "exit_code": -1}
    except Exception as e:
        logger.exception("git command failed: %s", cmd)
        return {"ok": False, "output": str(e), "exit_code": -1}


def _has_repo() -> bool:
    """Check if current directory is a git repository."""
    dotgit = ROOT / ".git"
    return dotgit.exists() and dotgit.is_dir()


# ── Status ──────────────────────────────────────────────────────────────────
@router.get("/git/status")
def git_status():
    """Return full repository status: branch, changed/staged/untracked files, commit history."""
    if not _has_repo():
        return {"has_repo": False}

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    status = _run_git(["status", "--porcelain"])
    log = _run_git(["log", "--oneline", "-20", "--decorate"])

    staged = []
    unstaged = []
    untracked = []
    for line in status["output"].split("\n"):
        if not line.strip():
            continue
        code = line[:2]
        fname = line[3:].strip()
        # Untracked files are reported as "?? path"
        if code == "??":
            untracked.append(fname)
            continue
        ix = code[0]
        wx = code[1]
        if ix not in (" ", "?"):
            staged.append(fname)
        if wx not in (" ", "?"):
            unstaged.append(fname)

    return {
        "has_repo": True,
        "branch": branch["output"].strip(),
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "history": log["output"].strip(),
    }


# ── Init / Clone ────────────────────────────────────────────────────────────
class InitRequest(BaseModel):
    pass


@router.post("/git/init")
def git_init(req: InitRequest):
    """Initialize a new git repository."""
    if _has_repo():
        raise HTTPException(status_code=409, detail="Repository already exists")
    r = _run_git(["init"])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    _run_git(["checkout", "-b", "main"])
    return r


class CloneRequest(BaseModel):
    url: str
    branch: str = "main"


@router.post("/git/clone")
def git_clone(req: CloneRequest):
    """Clone a remote repository."""
    if _has_repo():
        raise HTTPException(status_code=409, detail="Repository already exists in this directory")
    # Clone into a temp dir, then verify
    cmd = ["clone", "--branch", req.branch, req.url, str(ROOT)]
    r = _run_git(cmd, ROOT.parent)
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


# ── Stage / Unstage ─────────────────────────────────────────────────────────
class StageRequest(BaseModel):
    files: list[str] = Field(min_length=1)


@router.post("/git/stage")
def git_stage(req: StageRequest):
    """Stage files."""
    r = _run_git(["add"] + req.files)
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


@router.post("/git/unstage")
def git_unstage(req: StageRequest):
    """Unstage files."""
    r = _run_git(["reset", "HEAD", "--"] + req.files)
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


@router.post("/git/stage-all")
def git_stage_all():
    """Stage all changed and untracked files."""
    r = _run_git(["add", "-A"])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


# ── Commit ──────────────────────────────────────────────────────────────────
class CommitRequest(BaseModel):
    message: str


@router.post("/git/commit")
def git_commit(req: CommitRequest):
    """Create a commit."""
    r = _run_git(["commit", "-m", req.message])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


# ── Branches ────────────────────────────────────────────────────────────────
@router.get("/git/branches")
def git_branches():
    """List local branches."""
    r = _run_git(["branch", "--format=%(refname:short)"])
    active = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    branches = [b.strip() for b in r["output"].split("\n") if b.strip()]
    return {"branches": branches, "active": active["output"].strip()}


class BranchRequest(BaseModel):
    name: str


@router.post("/git/branch/create")
def git_branch_create(req: BranchRequest):
    """Create and switch to a new branch."""
    r = _run_git(["checkout", "-b", req.name])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


@router.post("/git/branch/switch")
def git_branch_switch(req: BranchRequest):
    """Switch to an existing branch."""
    r = _run_git(["checkout", req.name])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


@router.delete("/git/branch/{name}")
def git_branch_delete(name: str):
    """Delete a local branch."""
    r = _run_git(["branch", "-d", name])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


# ── Push / Pull / Fetch / Merge ─────────────────────────────────────────────
@router.post("/git/push")
def git_push():
    """Push to remote."""
    r = _run_git(["push", "-u", "origin", "HEAD"])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


@router.post("/git/pull")
def git_pull():
    """Pull from remote."""
    r = _run_git(["pull", "--rebase"])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


@router.post("/git/fetch")
def git_fetch():
    """Fetch from remote."""
    r = _run_git(["fetch", "--all"])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


class MergeRequest(BaseModel):
    branch: str


@router.post("/git/merge")
def git_merge(req: MergeRequest):
    """Merge a branch into current."""
    r = _run_git(["merge", req.branch])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r


# ── Diff ────────────────────────────────────────────────────────────────────
@router.get("/git/diff")
def git_diff(file: str = ""):
    """Get diff for all files or a specific file."""
    cmd = ["diff", "--unified=5"]
    if file:
        cmd.append("--")
        cmd.append(file)
    else:
        cmd.append("HEAD")
    r = _run_git(cmd)
    return {"diff": r["output"]}


@router.get("/git/diff-staged")
def git_diff_staged(file: str = ""):
    """Get diff for staged changes."""
    cmd = ["diff", "--cached", "--unified=5"]
    if file:
        cmd.append("--")
        cmd.append(file)
    r = _run_git(cmd)
    return {"diff": r["output"]}


# ── History ─────────────────────────────────────────────────────────────────
@router.get("/git/history")
def git_history(count: int = 30):
    """Return commit history."""
    r = _run_git(["log", f"-{count}", "--oneline", "--decorate", "--graph"])
    return {"history": r["output"]}


# ═════════════════════════════════════════════════════════════════════════════
#  GITHUB ROUTES
# ═════════════════════════════════════════════════════════════════════════════

import httpx

# GitHub token is loaded from .lumora-settings.json
def _get_github_token() -> str:
    settings_file = ROOT / ".lumora-settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
            token = settings.get("github", {}).get("token", "")
            if token:
                return token
        except (json.JSONDecodeError, ValueError):
            pass
    raise HTTPException(status_code=401, detail="GitHub not connected. Add your token in Source Control settings.")


def _gh_headers() -> dict:
    token = _get_github_token()
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Lumora-Dev",
    }


class GitHubTokenRequest(BaseModel):
    token: str


@router.post("/github/connect")
def github_connect(req: GitHubTokenRequest):
    """Save GitHub token and verify it."""
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {req.token}",
        "User-Agent": "Lumora-Dev",
    }
    try:
        resp = httpx.get("https://api.github.com/user", headers=headers, timeout=10)
        if resp.status_code >= 400:
            raise HTTPException(status_code=401, detail="Invalid GitHub token")
        user_data = resp.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Cannot reach GitHub: {e}")

    # Save token
    settings_file = ROOT / ".lumora-settings.json"
    settings = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            settings = {}
    settings.setdefault("github", {})
    settings["github"]["token"] = req.token
    settings["github"]["username"] = user_data.get("login", "")
    settings_file.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return {"ok": True, "username": user_data.get("login", "")}


@router.delete("/github/disconnect")
def github_disconnect():
    """Remove GitHub token."""
    settings_file = ROOT / ".lumora-settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
            settings.pop("github", None)
            settings_file.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, ValueError):
            pass
    return {"ok": True}


@router.get("/github/repos")
def github_list_repos():
    """List user's GitHub repositories."""
    headers = _gh_headers()
    repos = []
    page = 1
    while page <= 3:
        try:
            resp = httpx.get(
                f"https://api.github.com/user/repos?per_page=50&page={page}&sort=updated",
                headers=headers, timeout=15,
            )
            if resp.status_code >= 400:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch repos")
            data = resp.json()
            if not data:
                break
            for r in data:
                repos.append({
                    "name": r["name"],
                    "full_name": r.get("full_name", ""),
                    "private": r.get("private", False),
                    "html_url": r.get("html_url", ""),
                    "clone_url": r.get("clone_url", ""),
                    "description": r.get("description", ""),
                    "default_branch": r.get("default_branch", "main"),
                })
            page += 1
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Cannot reach GitHub: {e}")
    return {"repos": repos}


class GitHubCreateRepoRequest(BaseModel):
    name: str
    private: bool = False
    description: str = ""


@router.post("/github/repos/create")
def github_create_repo(req: GitHubCreateRepoRequest):
    """Create a new GitHub repository."""
    headers = _gh_headers()
    try:
        resp = httpx.post(
            "https://api.github.com/user/repos",
            json={"name": req.name, "private": req.private, "description": req.description, "auto_init": False},
            headers=headers, timeout=15,
        )
        if resp.status_code >= 400:
            detail = resp.json().get("message", "Failed to create repo")
            raise HTTPException(status_code=resp.status_code, detail=detail)
        data = resp.json()
        return {
            "name": data["name"],
            "html_url": data.get("html_url", ""),
            "clone_url": data.get("clone_url", ""),
        }
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Cannot reach GitHub: {e}")


class GitHubSetRemoteRequest(BaseModel):
    remote_url: str


@router.post("/github/remote")
def github_set_remote(req: GitHubSetRemoteRequest):
    """Set the origin remote for the current repo."""
    # Remove existing origin if any
    _run_git(["remote", "remove", "origin"])
    r = _run_git(["remote", "add", "origin", req.remote_url])
    if not r["ok"]:
        raise HTTPException(status_code=500, detail=r["output"])
    return r
