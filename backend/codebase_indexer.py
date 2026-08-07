"""
Lumora Dev – Codebase Indexer
Scans the project tree, extracts symbols (functions, classes, routes, imports, components),
and builds a lightweight searchable index + dependency graph.
"""
from pathlib import Path
import json
import re
import time
import logging
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = ROOT / ".codebase-index.json"
logger = logging.getLogger("lumora.indexer")

IGNORE_DIRS = {".git", "venv", "__pycache__", "node_modules", ".cache", ".local", ".agents", ".pythonlibs", "__pycache__",
               ".nexus", "dist", "build", ".next"}
IGNORE_EXTENSIONS = {".ico", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".woff", ".woff2", ".ttf", ".eot", ".map",
                     ".pyc", ".lock", ".min.js", ".min.css"}

# ── Symbol extractors per language ──────────────────────────────────────────

def _extract_python(filepath: Path) -> list[dict]:
    symbols = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return symbols
    lines = content.split("\n")
    rel = str(filepath.relative_to(ROOT))

    for i, line in enumerate(lines, 1):
        # Class definition
        m = re.match(r'^\s*class\s+(\w+)', line)
        if m:
            symbols.append({"type": "class", "name": m.group(1), "file": rel, "line": i, "lang": "python"})
            continue
        # Function / method
        m = re.match(r'^\s*(async\s+)?def\s+(\w+)', line)
        if m:
            name = m.group(2)
            # Skip dunder methods
            if name.startswith("__") and name.endswith("__"):
                symbols.append({"type": "method", "name": name, "file": rel, "line": i, "lang": "python"})
            else:
                indent = len(line) - len(line.lstrip())
                symbols.append({"type": "function" if indent == 0 else "method", "name": name, "file": rel, "line": i, "lang": "python"})
            continue
        # Import
        m = re.match(r'^\s*(?:from\s+(\S+)\s+)?import\s+(.+)', line)
        if m:
            mod = m.group(1) or ""
            targets = [t.strip().split(" as ")[0].strip() for t in m.group(2).split(",")]
            for t in targets:
                symbols.append({"type": "import", "name": t, "module": mod, "file": rel, "line": i, "lang": "python"})
            continue
        # Route decorator
        if "@router." in line or "@app." in line:
            route_match = re.search(r'@(?:router|app)\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)', line)
            if route_match:
                symbols.append({"type": "route", "name": route_match.group(1), "method": "HTTP", "file": rel, "line": i, "lang": "python"})
    return symbols


def _extract_javascript(filepath: Path) -> list[dict]:
    symbols = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return symbols
    lines = content.split("\n")
    rel = str(filepath.relative_to(ROOT))
    ext = filepath.suffix.lower()
    lang = "typescript" if ext in (".ts", ".tsx") else "javascript"

    for i, line in enumerate(lines, 1):
        # Function declarations / arrow functions assigned to variables
        m = re.match(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)', line)
        if m:
            symbols.append({"type": "function", "name": m.group(1), "file": rel, "line": i, "lang": lang})
            continue
        m = re.match(r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(', line)
        if m:
            symbols.append({"type": "function", "name": m.group(1), "file": rel, "line": i, "lang": lang})
            continue
        # Class
        m = re.match(r'^\s*(?:export\s+)?class\s+(\w+)', line)
        if m:
            symbols.append({"type": "class", "name": m.group(1), "file": rel, "line": i, "lang": lang})
            continue
        # Component (capitalized function or const in jsx/tsx)
        if ext in (".jsx", ".tsx"):
            m = re.match(r'^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Z]\w+)', line)
            if m:
                symbols.append({"type": "component", "name": m.group(1), "file": rel, "line": i, "lang": lang})
                continue
            m = re.match(r'^\s*(?:export\s+)?const\s+([A-Z]\w+)\s*[:=]', line)
            if m:
                symbols.append({"type": "component", "name": m.group(1), "file": rel, "line": i, "lang": lang})
                continue
        # Import
        m = re.match(r'^\s*import\s+.*?(?:from\s+)?["\']([^"\']+)["\']', line)
        if m:
            symbols.append({"type": "import", "name": m.group(1), "file": rel, "line": i, "lang": lang})
            continue
        # Hooks
        m = re.match(r'^\s*(?:export\s+)?(?:const|function)\s+(use\w+)', line)
        if m:
            symbols.append({"type": "hook", "name": m.group(1), "file": rel, "line": i, "lang": lang})
            continue
    return symbols


def _extract_shell(filepath: Path) -> list[dict]:
    symbols = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return symbols
    rel = str(filepath.relative_to(ROOT))
    for i, line in enumerate(content.split("\n"), 1):
        m = re.match(r'^\s*(?:function\s+)?(\w+)\s*\(\s*\)\s*\{?', line)
        if m and m.group(1) not in ("if", "then", "else", "fi", "for", "while", "do", "done", "case", "esac", "echo", "cd", "ls"):
            symbols.append({"type": "function", "name": m.group(1), "file": rel, "line": i, "lang": "shell"})
    return symbols


LANG_EXTRACTORS = {
    ".py": _extract_python,
    ".js": _extract_javascript,
    ".jsx": _extract_javascript,
    ".ts": _extract_javascript,
    ".tsx": _extract_javascript,
    ".mjs": _extract_javascript,
    ".sh": _extract_shell,
}


# ── Dependency graph builder ────────────────────────────────────────────────
def _build_dependency_graph(symbols: list[dict]) -> dict:
    """Build a simple dependency graph: which files import which other files."""
    graph = {}
    imports_by_file = {}
    for sym in symbols:
        if sym["type"] == "import":
            imports_by_file.setdefault(sym["file"], []).append(sym["name"])

    # Resolve imports to actual files
    file_set = {s["file"] for s in symbols}
    for src_file, imports in imports_by_file.items():
        deps = []
        for imp in imports:
            # Try to match import to a known file
            for f in file_set:
                if imp in f or f.endswith("/" + imp) or f.endswith("/" + imp + ".py") or f.endswith("/" + imp + ".js"):
                    deps.append(f)
                    break
            else:
                deps.append(imp)  # external dep
        graph[src_file] = deps
    return graph


# ── Main indexer ────────────────────────────────────────────────────────────
def index_project(force: bool = False) -> dict:
    """Scan the entire project, extract symbols, and cache the result."""
    # Return cached if recent (< 5 min)
    if not force and INDEX_FILE.exists():
        try:
            cached = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            age = time.time() - cached.get("indexed_at", 0)
            if age < 300:
                return cached
        except (json.JSONDecodeError, ValueError):
            pass

    symbols = []
    file_list = []
    logger.info("Indexing project at %s (force=%s)", ROOT, force)

    # Walk the project tree
    for entry in sorted(ROOT.rglob("*")):
        if entry.is_dir():
            if entry.name in IGNORE_DIRS or any(p in IGNORE_DIRS for p in entry.parts):
                continue
            continue
        if entry.suffix in IGNORE_EXTENSIONS:
            continue
        if entry.name.startswith("."):
            continue
        rel = str(entry.relative_to(ROOT))
        file_list.append(rel)
        extractor = LANG_EXTRACTORS.get(entry.suffix)
        if extractor:
            symbols.extend(extractor(entry))

    graph = _build_dependency_graph(symbols)

    # Summary stats
    stats = {"total_files": len(file_list), "total_symbols": len(symbols),
             "by_type": {}, "by_lang": {}}
    for s in symbols:
        stats["by_type"][s["type"]] = stats["by_type"].get(s["type"], 0) + 1
        stats["by_lang"][s["lang"]] = stats["by_lang"].get(s["lang"], 0) + 1

    index = {
        "symbols": symbols,
        "files": file_list,
        "dependencies": graph,
        "stats": stats,
        "indexed_at": time.time(),
    }
    INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")
    logger.info(
        "Indexed %s files, %s symbols",
        index["stats"].get("total_files", 0),
        index["stats"].get("total_symbols", 0),
    )
    return index


def search_index(query: str, limit: int = 30) -> list[dict]:
    """Search the symbol index for matching names or file paths."""
    if not INDEX_FILE.exists():
        return []
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []
    q = (query or "").lower().strip()
    if not q:
        return index.get("symbols", [])[:limit]
    results = []
    for s in index.get("symbols", []):
        name = s.get("name", "").lower()
        fpath = s.get("file", "").lower()
        if q in name or q in fpath:
            results.append(s)
            if len(results) >= limit:
                break
    return results


def get_dependencies(filepath: str) -> list[str]:
    """Return dependencies for a file."""
    if not INDEX_FILE.exists():
        return []
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []
    return index.get("dependencies", {}).get(filepath, [])


def get_stats() -> dict:
    """Return index statistics."""
    if not INDEX_FILE.exists():
        return {"total_files": 0, "total_symbols": 0, "by_type": {}, "by_lang": {}}
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {"total_files": 0, "total_symbols": 0, "by_type": {}, "by_lang": {}}
    return index.get("stats", {})


def architecture_overview() -> dict:
    """High-level project summary from the index."""
    index_project()
    if not INDEX_FILE.exists():
        return {"summary": "No index yet", "top_dirs": [], "languages": {}, "entrypoints": []}
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {"summary": "Index unreadable", "top_dirs": [], "languages": {}, "entrypoints": []}

    files = index.get("files", [])
    stats = index.get("stats", {})
    deps = index.get("dependencies", {})

    # Top-level dirs
    top = {}
    for f in files:
        part = f.split("/")[0] if "/" in f else "(root)"
        top[part] = top.get(part, 0) + 1
    top_dirs = sorted(top.items(), key=lambda x: -x[1])[:15]

    # Entrypoints heuristic
    entrypoints = [
        f for f in files
        if any(x in f.lower() for x in ("main.py", "app.py", "server.py", "index.js", "index.ts", "page.tsx", "agent.py"))
    ][:20]

    # Hub files (most depended-upon names)
    reverse = {}
    for src, dests in deps.items():
        for d in dests:
            reverse[d] = reverse.get(d, 0) + 1
    hubs = sorted(reverse.items(), key=lambda x: -x[1])[:10]

    summary = (
        f"{stats.get('total_files', 0)} files, {stats.get('total_symbols', 0)} symbols. "
        f"Languages: {stats.get('by_lang', {})}."
    )
    return {
        "summary": summary,
        "top_dirs": [{"name": n, "files": c} for n, c in top_dirs],
        "languages": stats.get("by_lang", {}),
        "by_type": stats.get("by_type", {}),
        "entrypoints": entrypoints,
        "dependency_hubs": [{"name": n, "imported_by": c} for n, c in hubs],
        "total_files": stats.get("total_files", 0),
        "total_symbols": stats.get("total_symbols", 0),
    }


def semantic_search(query: str, limit: int = 30) -> list[dict]:
    """
    Lightweight semantic-ish search: token overlap on symbol names + file paths.
    No external embedding model required (local-first).
    """
    if not INDEX_FILE.exists():
        index_project()
    try:
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return []
    tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9_]+", query or "") if len(t) > 1]
    if not tokens:
        return search_index(query, limit)

    scored = []
    for s in index.get("symbols", []):
        blob = f"{s.get('name', '')} {s.get('file', '')} {s.get('type', '')}".lower()
        score = sum(1 for t in tokens if t in blob)
        # bonus for exact name token
        name = s.get("name", "").lower()
        if name in tokens:
            score += 3
        if score > 0:
            scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    out = []
    for score, s in scored[:limit]:
        item = dict(s)
        item["score"] = score
        out.append(item)
    return out
