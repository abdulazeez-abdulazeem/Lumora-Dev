"""
Lumora Development Agent – v2.5

Autonomous coding assistant with:
- Strong Lumora Studio knowledge
- Conversation memory (LangGraph checkpoint)
- File system tools (list / read / write / create / delete / rename)
- Codebase search, terminal, git, and database tools
- Multi-provider LLM support via settings or environment
"""

import os
import json
from pathlib import Path
from typing import Annotated, TypedDict, Literal
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

load_dotenv()

try:
    from backend.security import decrypt_secret
except Exception:
    def decrypt_secret(x):  # type: ignore
        return x or ""

# ------------------------------------------------------------
# Project root (the folder where the agent is running)
# ------------------------------------------------------------
def _resolve_project_root() -> Path:
    """Local/Docker: CWD. Vercel: writable /tmp workspace (deployment FS is read-only)."""
    import os
    override = os.environ.get("LUMORA_PROJECT_ROOT")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p
    if os.environ.get("LUMORA_RUNTIME") == "vercel":
        p = Path("/tmp/lumora-workspace")
        p.mkdir(parents=True, exist_ok=True)
        return p
    return Path.cwd()


PROJECT_ROOT = _resolve_project_root()

# Directories / files the agent must not touch
_AGENT_IGNORE_DIRS = {
    ".git", "venv", ".venv", "__pycache__", "node_modules",
    ".cache", ".local", ".agents", ".pythonlibs",
}
_AGENT_IGNORE_FILES = {".env", ".lumora-settings.json"}
_MAX_READ_CHARS = 15000


def _safe_resolve(rel: str) -> Path | None:
    """Resolve *rel* under PROJECT_ROOT. Returns None if outside root or protected."""
    try:
        # Prefer live env so /chat can retarget the agent to the active workspace
        import os
        env_root = os.environ.get("LUMORA_PROJECT_ROOT")
        root = Path(env_root).resolve() if env_root else PROJECT_ROOT.resolve()
        target = (root / (rel or ".")).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return None
        for part in target.relative_to(root).parts:
            if part in _AGENT_IGNORE_DIRS or part in _AGENT_IGNORE_FILES:
                return None
        return target
    except (OSError, ValueError):
        return None


# ------------------------------------------------------------
# 1. Tools – file operations
# ------------------------------------------------------------
@tool
def list_files(directory: str = ".") -> str:
    """List files and folders in a directory (relative to current working directory).
    Use this to understand the project structure.
    Example: list_files(".") or list_files("src/app")
    """
    try:
        path = _safe_resolve(directory)
        if path is None:
            return "Error: Access outside project root or to a protected path is not allowed."
        if not path.exists():
            return f"Directory not found: {directory}"
        if not path.is_dir():
            return f"Not a directory: {directory}"

        items = []
        for item in sorted(path.iterdir()):
            if item.name in _AGENT_IGNORE_DIRS or item.name in _AGENT_IGNORE_FILES:
                continue
            prefix = "📁 " if item.is_dir() else "📄 "
            items.append(f"{prefix}{item.name}")
        return "\n".join(items) if items else "(empty directory)"
    except Exception as e:
        return f"Error listing files: {e}"


@tool
def read_file(filepath: str) -> str:
    """Read the contents of a file.
    Use this to examine existing code before editing or explaining it.
    Example: read_file("src/app/page.tsx")
    """
    try:
        path = _safe_resolve(filepath)
        if path is None:
            return "Error: Access outside project root or to a protected path is not allowed."
        if not path.exists():
            return f"File not found: {filepath}"
        if not path.is_file():
            return f"Not a file: {filepath}"

        content = path.read_text(encoding="utf-8", errors="replace")
        if len(content) > _MAX_READ_CHARS:
            return content[:_MAX_READ_CHARS] + "\n\n... [file truncated – too large]"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(filepath: str, content: str) -> str:
    """Create or overwrite a file with the given content.
    Always confirm with the user before overwriting important files.
    Example: write_file("src/components/Button.tsx", "export function Button() { ... }")
    """
    try:
        path = _safe_resolve(filepath)
        if path is None:
            return "Error: Access outside project root or to a protected path is not allowed."

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {filepath}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool
def create_directory(directory: str) -> str:
    """Create a new directory (and parent directories if needed).
    Example: create_directory("src/components/ui")
    """
    try:
        path = _safe_resolve(directory)
        if path is None:
            return "Error: Access outside project root or to a protected path is not allowed."
        path.mkdir(parents=True, exist_ok=True)
        return f"Directory created (or already exists): {directory}"
    except Exception as e:
        return f"Error creating directory: {e}"


@tool
def search_codebase(query: str = "") -> str:
    """Search the entire codebase index for files, functions, classes, routes, components, or imports matching a query.
    Use this BEFORE editing code to understand what exists and how files relate.
    Example: search_codebase("Button component") or search_codebase("api route users")
    """
    from backend.codebase_indexer import search_index, index_project, get_stats
    index_project()  # ensure index exists
    results = search_index(query, 30)
    if not results:
        # Try broader search
        results = search_index(query, 50)
    if not results:
        return f"No symbols found for '{query}'. Try a different search term."
    out_lines = [f"Found {len(results)} result(s) for '{query}':"]
    for r in results[:25]:
        out_lines.append(f"  [{r['type'].upper()}] {r['name']} — {r['file']}:{r['line']}")
    return "\n".join(out_lines)


@tool
def get_project_map() -> str:
    """Get a high-level overview of the project: file count, symbol counts by type and language."""
    from backend.codebase_indexer import get_stats, index_project
    index_project()
    stats = get_stats()
    type_str = ", ".join(f"{k}: {v}" for k, v in stats.get("by_type", {}).items())
    lang_str = ", ".join(f"{k}: {v}" for k, v in stats.get("by_lang", {}).items())
    return f"Project overview:\n  Files: {stats.get('total_files', 0)}\n  Symbols: {stats.get('total_symbols', 0)}\n  By type: {type_str}\n  By language: {lang_str}"


# ── Additional Agent Tools (HTTP-backed) ────────────────────────────
import subprocess
import httpx

_API_BASE = "http://localhost:8000"


@tool
def delete_file(filepath: str) -> str:
    """Delete a file permanently. Requires user confirmation."""
    try:
        r = httpx.delete(f"{_API_BASE}/file", json={"path": filepath}, timeout=10)
        return f"Deleted: {filepath}" if r.status_code < 400 else f"Failed: {r.json().get('detail', r.text)}"
    except Exception as e:
        return f"Error: {e}"


@tool
def rename_file(old_path: str, new_path: str) -> str:
    """Rename or move a file."""
    try:
        r = httpx.put(f"{_API_BASE}/file", json={"old_path": old_path, "new_path": new_path}, timeout=10)
        return f"Renamed: {old_path} → {new_path}" if r.status_code < 400 else f"Failed: {r.json().get('detail', r.text)}"
    except Exception as e:
        return f"Error: {e}"


@tool
def run_terminal(command: str, workdir: str = ".") -> str:
    """Execute a shell command (npm, pip, python, node, git, ls, mkdir, rm, etc.)
    Example: run_terminal("npm install") or run_terminal("pytest", "tests")"""
    try:
        r = httpx.post(f"{_API_BASE}/terminal/exec", json={"command": command, "cwd": workdir}, timeout=35)
        data = r.json()
        return f"Exit: {data.get('exit_code', -1)}\n{data.get('output', '')}"
    except Exception as e:
        return f"Terminal error: {e}"


@tool
def git_stage(files: str) -> str:
    """Stage files for commit. Use 'all' to stage everything."""
    try:
        if files.strip().lower() in ("all", ".", "*"):
            r = httpx.post(f"{_API_BASE}/git/stage-all", timeout=10)
        else:
            payload = {"files": [f.strip() for f in files.split(",") if f.strip()]}
            r = httpx.post(f"{_API_BASE}/git/stage", json=payload, timeout=10)
        return r.json().get("output", "Staged") if r.status_code < 400 else f"Failed: {r.text}"
    except Exception as e:
        return f"Git error: {e}"


@tool
def git_commit(message: str) -> str:
    """Create a git commit. Never push."""
    try:
        r = httpx.post(f"{_API_BASE}/git/commit", json={"message": message}, timeout=10)
        return r.json().get("output", "Committed") if r.status_code < 400 else f"Failed: {r.text}"
    except Exception as e:
        return f"Git error: {e}"


@tool
def db_query(sql: str) -> str:
    """Execute a SQL query on the project database and return results.
    Use this to explore the database schema, query tables, or verify data.
    Example: db_query("SELECT * FROM users LIMIT 5") or db_query("SELECT name FROM sqlite_master WHERE type='table'")
    """
    try:
        r = httpx.post(f"{_API_BASE}/db/query", json={"sql": sql}, timeout=15)
        if r.status_code >= 400:
            return f"Query error: {r.text}"
        data = r.json()
        out = []
        for result in data.get("results", []):
            if result["type"] == "error":
                out.append(f"ERROR: {result['message']}")
            elif result["type"] == "write":
                out.append(f"OK — {result.get('affected', 0)} rows affected")
            else:
                cols = result.get("columns", [])
                rows = result.get("rows", [])
                out.append(f"Columns: {', '.join(cols)}")
                out.append(f"Rows ({result.get('count', 0)}):")
                for row in rows[:20]:
                    out.append("  " + str(dict(row)))
                if len(rows) > 20:
                    out.append(f"  ... and {len(rows) - 20} more rows")
        out.append(f"Time: {data.get('elapsed_ms', 0)}ms")
        return "\n".join(out)
    except Exception as e:
        return f"Database error: {e}"


@tool
def db_tables() -> str:
    """List all tables in the project database."""
    try:
        r = httpx.get(f"{_API_BASE}/db/tables", timeout=10)
        tables = r.json().get("tables", [])
        return "Tables: " + ", ".join(tables) if tables else "No tables found."
    except Exception as e:
        return f"Database error: {e}"



@tool
def remember(note: str, kind: str = "note") -> str:
    """Persist a project note, decision, or preference for future sessions.
    kind: note | decision | preference:key"""
    try:
        from backend import memory as memory_mod
        if kind == "decision":
            memory_mod.remember_decision(note)
        elif kind.startswith("preference:"):
            key = kind.split(":", 1)[1] or "general"
            memory_mod.remember_preference(key, note)
        else:
            memory_mod.append_memory("notes", {"text": note, "at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ")})
        return f"Remembered ({kind}): {note[:120]}"
    except Exception as e:
        return f"Memory error: {e}"


@tool
def begin_edit_session(label: str = "") -> str:
    """Start a multi-file edit session that supports rollback."""
    try:
        from backend.edit_session import begin_session
        return begin_session(label)
    except Exception as e:
        return f"Error: {e}"


@tool
def edit_session_write(session_id: str, filepath: str, content: str) -> str:
    """Write a file inside an edit session (snapshots previous content for rollback)."""
    try:
        from backend.edit_session import record_write
        from pathlib import Path
        r = record_write(session_id, filepath, Path.cwd(), content)
        return f"Wrote {filepath} in session {session_id}"
    except Exception as e:
        return f"Error: {e}"


@tool
def edit_session_rollback(session_id: str) -> str:
    """Rollback all files in an edit session to their pre-edit content."""
    try:
        from backend.edit_session import rollback_session
        from pathlib import Path
        data = rollback_session(session_id, Path.cwd())
        return f"Rolled back: {data.get('restored', [])}"
    except Exception as e:
        return f"Error: {e}"



@tool
def browser_open(url: str, headless: bool = True) -> str:
    """Launch browser if needed and navigate to a URL. Example: browser_open("https://example.com")"""
    try:
        from backend.browser.browser_manager import get_manager
        mgr = get_manager()
        st = mgr.status()
        if not st.get("running"):
            mgr.launch(headless=headless)
        r = mgr.goto(url)
        return f"Opened {r.get('url')} — title: {r.get('title')}"
    except Exception as e:
        return f"Browser error: {e}"


@tool
def browser_click(selector: str, double: bool = False) -> str:
    """Click an element by CSS selector."""
    try:
        from backend.browser import actions
        r = actions.click(selector, double=double)
        return f"Clicked {selector}" if r.get("ok") else str(r)
    except Exception as e:
        return f"Browser error: {e}"


@tool
def browser_type(selector: str, text: str) -> str:
    """Type text into an input matching the CSS selector."""
    try:
        from backend.browser import actions
        r = actions.type_text(selector, text)
        return f"Typed into {selector}" if r.get("ok") else str(r)
    except Exception as e:
        return f"Browser error: {e}"


@tool
def browser_inspect(what: str = "info") -> str:
    """Inspect the current page. what: info | text | forms | buttons"""
    try:
        from backend.browser import inspector
        if what == "text":
            r = inspector.visible_text(6000)
            return r.get("text", "")[:4000]
        if what == "forms":
            return str(inspector.list_forms())
        if what == "buttons":
            return str(inspector.list_buttons())
        r = inspector.page_info()
        return f"Title: {r.get('title')} | URL: {r.get('url')}"
    except Exception as e:
        return f"Browser error: {e}"


@tool
def browser_screenshot(full_page: bool = False) -> str:
    """Capture a screenshot of the current page. Saves under frontend/screenshots/."""
    try:
        from backend.browser import screenshots
        r = screenshots.take_screenshot(full_page=full_page, include_base64=False)
        return f"Screenshot saved: {r.get('filename')} ({r.get('size')} bytes)"
    except Exception as e:
        return f"Browser error: {e}"


@tool
def browser_close() -> str:
    """Close the browser session."""
    try:
        from backend.browser.browser_manager import get_manager
        get_manager().close()
        return "Browser closed"
    except Exception as e:
        return f"Browser error: {e}"


# ── Final unified tool list ─────────────────────────────────────────

@tool
def analyze_screenshot(screenshot: str = "") -> str:
    """Analyze a screenshot (path or base64) for blank screens, layout problems, and visual issues.
    If screenshot is empty, attempts to use the latest browser screenshot."""
    try:
        from backend.vision.vision_manager import get_vision_manager
        from backend.browser.screenshots import take_screenshot
        mgr = get_vision_manager()
        if not screenshot:
            # try capture current browser page
            try:
                shot = take_screenshot(full_page=False)
                if isinstance(shot, dict) and shot.get("path"):
                    screenshot = shot["path"]
                elif isinstance(shot, str):
                    screenshot = shot
            except Exception:
                return "No screenshot provided and browser capture failed."
        result = mgr.analyze(screenshot)
        return f"{result.message} | confidence={result.confidence:.2f} | issues={len(result.issues)} | data_keys={list(result.data.keys())}"
    except Exception as e:
        return f"analyze_screenshot error: {e}"


@tool
def validate_ui(screenshot: str, expectations_json: str = "{}") -> str:
    """Validate UI against expectations (JSON string with buttons/texts/forms/navigation/must_not_contain)."""
    try:
        import json
        from backend.vision.vision_manager import get_vision_manager
        exp = json.loads(expectations_json) if expectations_json else {}
        result = get_vision_manager().validate_ui(screenshot, exp)
        return f"{result.message} | score={result.confidence:.2f} | issues={result.issues}"
    except Exception as e:
        return f"validate_ui error: {e}"


@tool
def compare_ui(expected: str, actual: str) -> str:
    """Compare expected vs actual screenshot; returns similarity and difference summary."""
    try:
        from backend.vision.vision_manager import get_vision_manager
        result = get_vision_manager().compare(expected, actual)
        sim = result.data.get("similarity")
        return f"{result.message} | similarity={sim} | issues={len(result.issues)}"
    except Exception as e:
        return f"compare_ui error: {e}"


@tool
def annotate_screenshot(screenshot: str, issues_json: str = "[]") -> str:
    """Annotate a screenshot with issue markers. issues_json is a JSON list of issue dicts."""
    try:
        import json
        from backend.vision.vision_manager import get_vision_manager
        issues = json.loads(issues_json) if issues_json else []
        result = get_vision_manager().annotate(screenshot, issues)
        return f"{result.message} | path={result.data.get('annotated_path')}"
    except Exception as e:
        return f"annotate_screenshot error: {e}"


@tool
def inspect_layout(screenshot: str = "") -> str:
    """Run layout analysis (alignment, empty space, overflow heuristics) on a screenshot."""
    try:
        from backend.vision.vision_manager import get_vision_manager
        if not screenshot:
            return "screenshot path or base64 required"
        result = get_vision_manager().inspect_layout(screenshot)
        return f"{result.message} | confidence={result.confidence:.2f} | issues={result.issues}"
    except Exception as e:
        return f"inspect_layout error: {e}"



@tool
def search_knowledge(query: str, top_k: int = 6) -> str:
    """Search the project knowledge base (docs, README, API refs, design decisions). Use before coding."""
    try:
        from backend.knowledge.knowledge_manager import get_knowledge_manager
        res = get_knowledge_manager().search(query, top_k=top_k)
        cites = res.get("citations") or []
        lines = [f"Found {res.get('count', 0)} passages:"]
        for c in cites[:top_k]:
            lines.append(f"[{c['index']}] {c.get('title')} (score={c.get('score')}) – {c.get('snippet','')[:180]}")
        return "\n".join(lines) if lines else "No results."
    except Exception as e:
        return f"search_knowledge error: {e}"


@tool
def import_documents(path: str, tags: str = "") -> str:
    """Import a file or directory into the knowledge base. tags is comma-separated."""
    try:
        from backend.knowledge.knowledge_manager import get_knowledge_manager
        from pathlib import Path as P
        mgr = get_knowledge_manager()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] or None
        target = P(path)
        if target.is_dir():
            r = mgr.import_directory(path, tags=tag_list)
            return f"Imported {r.get('imported')} documents. Stats: {r.get('stats')}"
        r = mgr.import_file(path, tags=tag_list)
        return f"Imported {r.get('title')} ({r.get('chunks')} chunks) id={r.get('doc_id')}"
    except Exception as e:
        return f"import_documents error: {e}"


@tool
def summarize_document(doc_id: str = "", text: str = "") -> str:
    """Summarize a knowledge document by id, or summarize provided text."""
    try:
        from backend.knowledge.knowledge_manager import get_knowledge_manager
        return get_knowledge_manager().summarize_document(doc_id=doc_id or None, text=text or None) or "Empty summary."
    except Exception as e:
        return f"summarize_document error: {e}"


@tool
def cite_sources(query: str, top_k: int = 5) -> str:
    """Return formatted citations for knowledge search results."""
    try:
        from backend.knowledge.knowledge_manager import get_knowledge_manager
        res = get_knowledge_manager().search(query, top_k=top_k)
        from backend.knowledge.citations import CitationFormatter
        return CitationFormatter().cite_inline(res.get("results") or [])
    except Exception as e:
        return f"cite_sources error: {e}"


@tool
def search_project_docs(query: str) -> str:
    """Search README, CHANGELOG, ROADMAP, architecture and API docs specifically."""
    try:
        from backend.knowledge.knowledge_manager import get_knowledge_manager
        res = get_knowledge_manager().search_project_docs(query)
        return res.get("context_block") or f"No project docs matched for: {query}"
    except Exception as e:
        return f"search_project_docs error: {e}"



@tool
def assign_task(title: str, role: str, description: str = "") -> str:
    """Assign a task to a specialized agent role (planner/research/coding/testing/debugging/review/documentation/deployment_advisor)."""
    try:
        from backend.multiagent.agent_manager import get_agent_manager
        t = get_agent_manager().assign_task(title=title, role=role, description=description)
        return f"Assigned {t.task_id} to {role}: {title}"
    except Exception as e:
        return f"assign_task error: {e}"


@tool
def delegate_work(from_role: str, to_role: str, title: str, description: str = "") -> str:
    """Delegate work from one agent role to another."""
    try:
        from backend.multiagent.agent_manager import get_agent_manager
        t = get_agent_manager().delegate(from_role, to_role, title, description)
        return f"Delegated {t.task_id} {from_role} → {to_role}: {title}"
    except Exception as e:
        return f"delegate_work error: {e}"


@tool
def share_context(author: str, text: str) -> str:
    """Share a note into the multi-agent shared context and message bus."""
    try:
        from backend.multiagent.agent_manager import get_agent_manager
        get_agent_manager().share_context(author, text)
        return f"Shared from {author}: {text[:120]}"
    except Exception as e:
        return f"share_context error: {e}"


@tool
def request_review(subject: str) -> str:
    """Request a code review from the Review agent."""
    try:
        from backend.multiagent.agent_manager import get_agent_manager
        t = get_agent_manager().request_review(subject)
        return f"Review requested: {t.task_id}"
    except Exception as e:
        return f"request_review error: {e}"


@tool
def request_test(subject: str) -> str:
    """Request testing from the Testing agent."""
    try:
        from backend.multiagent.agent_manager import get_agent_manager
        t = get_agent_manager().request_test(subject)
        return f"Test requested: {t.task_id}"
    except Exception as e:
        return f"request_test error: {e}"


@tool
def request_research(subject: str) -> str:
    """Request research from the Research agent (Knowledge Engine)."""
    try:
        from backend.multiagent.agent_manager import get_agent_manager
        t = get_agent_manager().request_research(subject)
        return f"Research requested: {t.task_id}"
    except Exception as e:
        return f"request_research error: {e}"



@tool
def deploy_app(platform: str = "static", project_dir: str = ".", profile: str = "production") -> str:
    """Build and deploy the project to a platform (static/docker/vercel/netlify/railway/render)."""
    try:
        from backend.deployment.deployment_manager import get_deployment_manager
        r = get_deployment_manager().deploy(platform=platform, project_dir=project_dir, profile=profile)
        return f"Deploy {r.get('deployment_id')}: {r.get('status')} platform={platform} url={r.get('url')}"
    except Exception as e:
        return f"deploy_app error: {e}"


@tool
def build_project(project_dir: str = ".", command: str = "") -> str:
    """Run a production build / verification for the project."""
    try:
        from backend.deployment.deployment_manager import get_deployment_manager
        r = get_deployment_manager().build(project_dir, command=command or None)
        return f"Build {r.get('build_id')}: {r.get('status')} ({r.get('duration_ms')}ms)"
    except Exception as e:
        return f"build_project error: {e}"


@tool
def rollback_deployment(snapshot_id: str) -> str:
    """Rollback to a previous deployment snapshot."""
    try:
        from backend.deployment.deployment_manager import get_deployment_manager
        r = get_deployment_manager().rollback(snapshot_id)
        return r.get("message") or str(r)
    except Exception as e:
        return f"rollback_deployment error: {e}"


TOOLS = [
    list_files, read_file, write_file, create_directory,
    delete_file, rename_file,
    search_codebase, get_project_map,
    run_terminal,
    git_stage, git_commit,
    db_query, db_tables,
    remember, begin_edit_session, edit_session_write, edit_session_rollback,
    browser_open, browser_click, browser_type, browser_inspect, browser_screenshot, browser_close,
    analyze_screenshot, validate_ui, compare_ui, annotate_screenshot, inspect_layout,
    search_knowledge, import_documents, summarize_document, cite_sources, search_project_docs,
    assign_task, delegate_work, share_context, request_review, request_test, request_research,
    deploy_app, build_project, rollback_deployment,
]


# ------------------------------------------------------------
# 2. Autonomous Multi-Agent System Prompt
# ------------------------------------------------------------
SYSTEM_PROMPT = """You are **Lumora Dev**, an autonomous AI software engineering agent.

You are NOT a chatbot. You are a professional software engineer with access to real file tools. Every user request is a task you must plan, execute, review, and complete.

### Internal Agent Roles (all performed by you)

[PLANNER] — Before any action, outline:
- User's goal and what files are involved
- Ordered step-by-step plan
- Risks or edge cases to watch for

[CODER] — When writing code:
- Read existing files first with read_file
- Create files with write_file, delete with delete_file, rename with rename_file
- Create directories with create_directory
- Search the codebase first with search_codebase
- Use TypeScript + Next.js App Router + Tailwind by default
- Write clean, production-quality code with comments

[REVIEWER] — After coding:
- Check your work for bugs, missing imports, broken references
- Run tests with run_terminal("pytest") or run_terminal("npm test")
- Install dependencies with run_terminal("npm install") when needed
- Verify consistency with existing architecture
- Mention any issues found

[TERMINAL] — Execute commands directly:
- Use run_terminal to run npm, pip, python, node, git, and shell commands
- Build projects: run_terminal("npm run build")
- Start dev servers: run_terminal("npm run dev")
- Run tests: run_terminal("pytest") or run_terminal("npm test")
- Install deps: run_terminal("pip install -r requirements.txt")

[GIT] — Manage version control:
- Stage files with git_stage("file1, file2") or git_stage("all")
- Commit with git_commit("descriptive message")
- Note which files changed
- Never push without user confirmation

[COORDINATOR] — Wrap up:
- List files created/modified
- State next steps
- Report progress: Progress: XX%

### Task Execution Pattern
Always structure your response:
1. [PLANNER] → plan
2. [CODER] → code changes
3. [REVIEWER] → self-review
4. [COORDINATOR] → summary + progress

### About Lumora Studio
- Natural-language AI platform for building websites, apps, dashboards, AI agents
- Stack: Next.js App Router + TypeScript + Tailwind CSS + Supabase + Vercel
- Configurable AI backend via OpenRouter or other providers

You are Lumora Dev v3 — Autonomous software engineering agent. Own every task from plan to completion. Use remember() for lasting decisions. Use edit sessions for multi-file changes that may need rollback.
"""


# ------------------------------------------------------------
# 3. State
# ------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ------------------------------------------------------------
# 4. LLM + Tools
# ------------------------------------------------------------
def get_llm():
    """Create LLM instance from stored settings or .env fallback."""
    # Read settings JSON
    settings_file = PROJECT_ROOT / ".lumora-settings.json"
    settings = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            pass

    provider_id = settings.get("default_provider") or os.getenv("PROVIDER", "openrouter").strip().lower()
    model = settings.get("default_model") or os.getenv("MODEL", "cohere/north-mini-code:free")

    # Determine base_url and API key
    if provider_id == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("openrouter", {}).get("api_key") or "") or os.getenv("OPENROUTER_API_KEY", "")
    elif provider_id == "openai":
        base_url = "https://api.openai.com/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("openai", {}).get("api_key") or "") or os.getenv("OPENAI_API_KEY", "")
    elif provider_id == "google":
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        api_key = decrypt_secret(settings.get("providers", {}).get("google", {}).get("api_key") or "") or os.getenv("GOOGLE_API_KEY", "")
    elif provider_id == "anthropic":
        base_url = "https://api.anthropic.com/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("anthropic", {}).get("api_key") or "") or os.getenv("ANTHROPIC_API_KEY", "")
    elif provider_id == "groq":
        base_url = "https://api.groq.com/openai/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("groq", {}).get("api_key") or "") or os.getenv("GROQ_API_KEY", "")
    elif provider_id == "deepseek":
        base_url = "https://api.deepseek.com/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("deepseek", {}).get("api_key") or "") or os.getenv("DEEPSEEK_API_KEY", "")
    elif provider_id == "mistral":
        base_url = "https://api.mistral.ai/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("mistral", {}).get("api_key") or "") or os.getenv("MISTRAL_API_KEY", "")
    elif provider_id == "cohere":
        base_url = "https://api.cohere.ai/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("cohere", {}).get("api_key") or "") or os.getenv("COHERE_API_KEY", "")
    elif provider_id == "together":
        base_url = "https://api.together.xyz/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("together", {}).get("api_key") or "") or os.getenv("TOGETHER_API_KEY", "")
    elif provider_id == "fireworks":
        base_url = "https://api.fireworks.ai/inference/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("fireworks", {}).get("api_key") or "") or os.getenv("FIREWORKS_API_KEY", "")
    elif provider_id == "ollama":
        base_url = "http://localhost:11434/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("ollama", {}).get("api_key") or "") or os.getenv("OLLAMA_API_KEY", "ollama")
    elif provider_id == "lmstudio":
        base_url = "http://localhost:1234/v1"
        api_key = decrypt_secret(settings.get("providers", {}).get("lmstudio", {}).get("api_key") or "") or os.getenv("LMSTUDIO_API_KEY", "lm-studio")
    else:
        base_url = "https://openrouter.ai/api/v1"
        api_key = os.getenv("OPENROUTER_API_KEY", "")

    if not api_key:
        raise ValueError(
            f"API key not found for provider '{provider_id}'.\n"
            "Add your key in Settings → AI Providers or set it in your .env file."
        )

    llm = ChatOpenAI(
        model=model,
        temperature=0.3,
        api_key=api_key,
        base_url=base_url,
    )
    return llm.bind_tools(TOOLS)


# ------------------------------------------------------------
# 5. Nodes
# ------------------------------------------------------------
def call_model(state: AgentState):
    llm = get_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "__end__"


# ------------------------------------------------------------
# 6. Build the agent graph
# ------------------------------------------------------------
def create_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("assistant", call_model)
    workflow.add_node("tools", ToolNode(TOOLS))

    workflow.add_edge(START, "assistant")
    workflow.add_conditional_edges("assistant", should_continue)
    workflow.add_edge("tools", "assistant")

    memory = MemorySaver()
    agent = workflow.compile(checkpointer=memory)
    return agent


# ------------------------------------------------------------
# 7. CLI (Termux-friendly)
# ------------------------------------------------------------
def main():
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel

    console = Console()
    agent = create_agent()
    config = {"configurable": {"thread_id": "lumora-dev-session"}}

    console.print(
        Panel.fit(
            "[bold cyan]Lumora Development Agent[/bold cyan]\n"
            "Stage 1 + File Tools\n"
            "Generate • Explain • Debug • Read/Write files\n\n"
            "Type your request  |  'exit' to quit",
            border_style="cyan",
        )
    )

    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Goodbye! Keep building Lumora.[/yellow]")
            break

        if user_input.lower() in {"exit", "quit", "q"}:
            console.print("[yellow]Goodbye! Keep building Lumora.[/yellow]")
            break

        if not user_input:
            continue

        result = agent.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )

        # Show only the final AI response (skip intermediate tool messages for clean UI)
        for msg in reversed(result["messages"]):
            if msg.type == "ai" and msg.content:
                console.print("\n[bold blue]Lumora Agent:[/bold blue]")
                console.print(Markdown(msg.content))
                break


if __name__ == "__main__":
    main()
