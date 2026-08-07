# Lumora Dev — Complete Project Audit Report

**Auditor role:** Principal Software Architect & Senior Code Auditor  
**Scope:** Entire application source tree (excluding `.local` skill bundles and `.git` objects as third-party/vendor content)  
**Date:** 2026-08-06  
**Codebase under review:** In-place merged Lumora-Dev (Project B + Project A features)

---

## Executive Summary

Lumora Dev is a **local-first AI software engineering workbench**: LangGraph agent + FastAPI backend + static web UI + reverse proxy. It already exposes file CRUD, terminal, git/GitHub, SQLite console, multi-provider LLM settings, codebase indexing, and task activity.

**It is not production-ready.** It is a strong **developer prototype / local agent IDE** with serious security and operational gaps that are acceptable on a trusted laptop/Replit instance but unsafe for multi-user or internet exposure.

| Dimension | Score (0–100) |
|-----------|---------------|
| **Overall health** | **62** |
| Architecture | 68 |
| Backend | 65 |
| Frontend | 70 |
| AI Agent | 64 |
| Security | 38 |
| Performance | 58 |
| Maintainability | 66 |
| **Production readiness** | **32** |

---

## 1. Architecture

### Current shape

```
Browser  →  server.py (static + HTTP proxy :5000)
                ↓
            FastAPI (uvicorn :8000)
                ├── api.py          /chat, /activity, /codebase/*
                ├── files_router    /files, /file, /folder, /terminal, /settings, /workspaces
                ├── git_router      /git/*, /github/*
                ├── db_router       /db/*
                ├── orchestrator    tasks + activity (in-memory + JSON file)
                ├── providers       static provider registry
                └── codebase_indexer  symbol index → .codebase_index.json
            agent.py  ← LangGraph graph + tools (also CLI entrypoint)
```

### Strengths
- Clear split: agent graph, HTTP API, proxy, UI.
- Routers are modular (files / git / db).
- Provider metadata is centralized in `providers.py`.

### Weaknesses
- **Dual process model** (proxy + API) is fragile; agent HTTP tools hard-code `http://localhost:8000`.
- **God modules:** `files_router.py` mixes FS, terminal, settings, and workspaces (~580 lines).
- **No service layer** — routers talk to disk/subprocess/SQLite directly.
- **In-process singletons** (`_agent`, `_CONNECTIONS`, `ACTIVITY_LOG`) do not scale beyond one worker.
- Empty `src/` directory; no clear app vs platform boundary for the *target* Lumora Studio project.

**Architecture score: 68**

---

## 2. Backend

### FastAPI / API (`api.py`)
- Health, chat, activity, codebase routes are coherent.
- Chat is **synchronous** (`_agent.invoke`) — blocks the worker for the full agent run.
- Single fixed `thread_id` (`lumora-api-session`) → **all users share one conversation memory**.
- No request auth, rate limiting, or max body size.

### Files router
- Solid tree listing, CRUD, rename, delete.
- Path safety uses `relative_to` + IGNORE lists (good after merge).
- **Terminal:** `subprocess.run(..., shell=True)` with only a 30s timeout — arbitrary command execution.
- Settings store API keys in **plaintext** `.lumora-settings.json`.
- Workspaces stored in JSON table file (fine for local).

### Git router
- Uses argv-list `git` invocation (good — no shell injection).
- Covers status, stage, commit, branches, push/pull/fetch/merge, GitHub token connect.
- Push/pull available without extra confirmation at API level.

### DB router
- SQLite default with WAL; intentional free-form SQL console.
- Table name path params previously injectable; **identifier validation added during this audit**.
- Arbitrary SQL still possible by design (dangerous if exposed).

### Orchestrator
- File-backed task list + in-memory activity ring.
- Response parsing via regex is best-effort, not structured tool telemetry.

### Codebase indexer
- Regex extractors for Python / JS / shell.
- Full tree walk on index; cache file on disk.
- Search is substring on symbol names only (no fuzzy, no content search).

### Agent (`agent.py`)
- LangGraph: assistant ↔ tools loop with `MemorySaver`.
- Tools: FS, search, terminal (via HTTP), git, db.
- Multi-provider `get_llm()` reads settings JSON or env.
- System prompt describes multi-role autonomy (planner/coder/reviewer).

**Backend score: 65**

---

## 3. Frontend

### Structure
- Single-page: `index.html` + large `script.js` (~2100 lines) + `styles.css` + WebGL `darkveil.js`.
- Panels: Chat, Files, SCM, Activity, Codebase, DB, Terminal, Settings modal, editor tabs.

### Strengths
- Cohesive matte-dark theme; responsive sidebar patterns.
- API base = `window.location.origin` (works behind the proxy).
- Rich SCM / settings / terminal UX for a single-file app.

### Weaknesses
- Monolithic JS (no modules/bundler) — hard to test and tree-shake.
- No error boundary / offline handling beyond toasts.
- Large CSS (~1940 lines) without design tokens system.
- Accessibility: limited focus management in modals; ARIA incomplete.
- Performance: full file tree rebuild on many actions; no virtualization for large trees.

**Frontend score: 70**

---

## 4. AI Agent

| Area | Assessment |
|------|------------|
| Tool registration | Clear `TOOLS` list; LangChain `@tool` |
| Tool execution | `ToolNode`; HTTP tools fail if API down |
| Provider abstraction | Functional multi-provider; duplicated knowledge with `providers.py` |
| Task orchestration | Prompt-driven roles; orchestrator is side-channel, not true multi-agent |
| Context | Single thread memory; no sliding window / summarization |
| Error recovery | Tools return strings; no structured retry policy |

**Gaps toward “autonomous SE agent”:**
- No plan persistence / approval gates for destructive ops.
- No test-run → fix loop with structured state.
- No PR / multi-file patch engine.
- `run_terminal` + unrestricted write is full remote code execution when the API is reachable.

**AI Agent score: 64**

---

## 5. File System

- Backend path checks: **good** (`relative_to` + IGNORE).
- Agent tools: **weaker** (`str.startswith` root check — edge-case prefix attacks; no IGNORE for `.env`).
- Large file read truncated at 15k chars in agent (good); backend `get_file` should enforce size limits too.
- Indexer skips IGNORE dirs; good.

---

## 6. Git Integration

- Repo detection via `.git` directory.
- Branch CRUD, stage/commit, remote GitHub ops present.
- **Bug fixed:** porcelain `??` untracked files were classified as staged.
- **Bug fixed:** agent `git_stage("all")` called `/git/stage` with file name `"all"` instead of `/git/stage-all`.
- Safety: no branch protection; push is open; merge has no conflict UI beyond raw output.

---

## 7. Database

- Local SQLite only in practice; connection framework stubs for other engines.
- Free-form SQL is a power tool, not a multi-tenant DB layer.
- Connections held in process dict — not production pooling.
- Future scale needs real multi-engine drivers, migrations, and auth.

---

## 8. Security

| Risk | Severity | Notes |
|------|----------|-------|
| Unauthenticated API | **Critical** | Any client on the network can chat, write files, run shell, push git |
| `shell=True` terminal | **Critical** | Full OS command execution as the server user |
| Arbitrary SQL | **High** | Intentional console; dangerous if exposed |
| API keys in JSON on disk | **High** | `.lumora-settings.json` not encrypted |
| CORS `allow_origins=["*"]` + credentials | **High** | Over-permissive |
| Agent FS ignores weaker than API | **Medium** | Can write sensitive paths agent-side |
| Path prefix (`startswith`) in agent | **Medium** | Prefer `relative_to` everywhere |
| Fixed conversation thread_id | **Medium** | Cross-session leakage in multi-user host |
| No rate limits | **Medium** | LLM cost / DoS |
| Secrets in env | **Low** | `.env` gitignored; good baseline |

**Security score: 38**

---

## 9. Performance

- Full recursive tree on every `/files` list — O(n) disk, no pagination.
- Indexer full walk; re-index on many search paths.
- Sync agent invoke blocks event loop (use threadpool or async).
- Frontend rebuilds large DOM lists without virtualization.
- Activity log unbounded in memory until process restart.

**Performance score: 58**

---

## 10. Code Quality

### Bugs fixed during this audit
1. **Critical:** `TerminalExecRequest` referenced but never defined → terminal endpoint broken at runtime.
2. **High:** Git status treated untracked (`??`) as staged.
3. **Medium:** Agent `git_stage("all")` did not call stage-all endpoint.
4. **Medium:** DB table/`order` path params lacked identifier validation (SQL injection surface).

### Remaining quality issues
- Long functions (`get_llm`, terminal_exec, frontend script).
- Duplicate provider URL/key logic (agent vs providers vs settings).
- `files_router` responsibility overload.
- No type-checked frontend; no shared OpenAPI client.
- Dead/empty `src/` directory.
- Minimal tests (`test_openrouter.py` only connectivity smoke).

**Maintainability score: 66**

---

## 11. Dependencies

```
langgraph, langchain-core, langchain-openai, python-dotenv, rich,
langgraph-checkpoint, fastapi, uvicorn[standard], httpx
```

- **Adequate** for current features.
- Missing for production: auth lib, structured logging, pytest, slowapi/rate-limit, cryptography for secret store.
- No lockfile (`requirements.txt` is lower-bounds only) → reproducibility risk.
- `rich` only needed for CLI.

---

## 12. API

- Routes largely align with frontend (proxy path prefixes cover all).
- Response models partial (many routers return ad-hoc dicts).
- Error handling: HTTPException widely used; some bare `except` paths.
- No OpenAPI tags/grouping polish; version field is static `1.0.0`.

---

## 13. Frontend Integration

- Buttons/panels generally wired to matching endpoints.
- Terminal was **broken** until `TerminalExecRequest` fix.
- SCM untracked counts were wrong until porcelain fix.
- Settings/provider flows depend on live `/settings` and key storage.

---

## 14. Testing

| Area | Coverage |
|------|----------|
| Unit tests | Essentially none |
| API tests | None |
| Agent tool tests | None |
| Frontend tests | None |
| E2E | None |
| Smoke | `test_openrouter.py` only |

**Highest-value missing tests:** path traversal cases, terminal allowlist, git porcelain parser, chat happy path with mocked LLM.

---

## 15. Production Readiness

**Verdict: Not production-ready (score 32).**

Safe today as:
- Local single-user Replit / laptop tool with trusted network.

Unsafe as:
- Public SaaS, multi-tenant host, or any internet-facing deployment without a hard security redesign.

### Issue register

#### Critical
1. No authentication / authorization on any API route.
2. Unrestricted shell execution (`shell=True`) via `/terminal/exec` and agent `run_terminal`.
3. ~~Missing `TerminalExecRequest` model (runtime failure)~~ — **fixed**.

#### High
4. Plaintext API key storage on disk.
5. Shared single agent memory thread for all requests.
6. Sync LLM invoke blocks server workers.
7. Arbitrary SQL execution without role separation.
8. CORS allow-all.
9. Git push exposed without confirmation gate at API layer.
10. ~~Untracked files misclassified in git status~~ — **fixed**.

#### Medium
11. Agent path checks weaker than backend; can touch ignored secrets.
12. No rate limiting / cost controls for LLM.
13. Full tree listing and index rebuild cost on large repos.
14. Monolithic frontend; no automated tests.
15. ~~git_stage("all") bug~~ — **fixed**.
16. ~~SQL identifier injection on table routes~~ — **mitigated**.

#### Low
17. Empty `src/` clutter.
18. README still describes earlier “Stage 1” partially.
19. No structured logging / metrics.
20. Dependency lower-bounds without lockfile.

---

## Scorecard (detail)

| Area | Score | Rationale |
|------|------:|-----------|
| Overall | 62 | Feature-rich prototype; security holds it back |
| Architecture | 68 | Clear modules; process/coupling issues |
| Backend | 65 | Complete routers; sync & auth gaps |
| Frontend | 70 | Usable IDE shell; monolithic |
| AI Agent | 64 | Solid tool loop; not yet autonomous SE |
| Security | 38 | Local-trust model only |
| Performance | 58 | Fine for small projects |
| Maintainability | 66 | Readable; needs modularization & tests |
| Production readiness | 32 | Must not expose publicly as-is |

---

## Bugs fixed in this audit (no redesign)

| File | Fix |
|------|-----|
| `backend/files_router.py` | Defined `TerminalExecRequest` |
| `backend/git_router.py` | Correct porcelain classification for `??` untracked |
| `backend/db_router.py` | `_safe_ident()` for table/order path params |
| `agent.py` | `git_stage("all")` → `/git/stage-all` |

Intended behavior preserved; no features removed.


---

## Post-audit update — Lumora Dev v2.5 (2026-08-06)

Phase 0 foundation freeze applied on the same repository:

- All critical/high *code* bugs from this report that could be fixed without redesign are fixed.
- Test suite added (29 passing).
- Logging, error recovery, path safety, and read limits improved.

**Revised readiness for local single-user use:** ~55 (up from 32 production / still not public-internet ready).  
Security items requiring auth, terminal allowlist, and secret encryption remain for v3 (see ROADMAP Phase 1).
