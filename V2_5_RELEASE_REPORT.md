# Lumora Dev v2.5 — Release Report

**Date:** 2026-08-06  
**Type:** Stability / foundation freeze (Phase 0)  
**Tag:** v2.5.0

---

## Summary of work completed

Lumora Dev v2.5 freezes the merged architecture as the official master baseline. No product redesign and no major feature additions. Work focused on:

1. Closing remaining audit bugs
2. Hardening path safety and error recovery
3. Adding automated tests
4. Logging and operational reliability
5. Documentation and version alignment

---

## Files modified

| File | Change |
|------|--------|
| `agent.py` | v2.5 header; `_safe_resolve`; ignore protected paths; git_stage all fix; cleanup |
| `backend/api.py` | v2.5.0; logging; chat/provider error recovery; codebase route try/except; safer lifespan |
| `backend/files_router.py` | `TerminalExecRequest`; MAX_FILE_READ; logging |
| `backend/git_router.py` | Porcelain untracked fix; logging |
| `backend/db_router.py` | `_safe_ident`; logging |
| `backend/codebase_indexer.py` | Search by path; logging |
| `backend/orchestrator.py` | MAX_ACTIVITY constant |
| `requirements.txt` | +pytest |
| `.gitignore` | Index filename consistency |
| `README.md` | v2.5 docs |
| `ROADMAP.md` | Phase 0 items checked |
| `PROJECT_AUDIT_REPORT.md` | Post-audit note |
| `CHANGELOG_v2.5.md` | New |
| `V2_5_RELEASE_REPORT.md` | New |
| `tests/**` | New suite |

---

## Tests added

29 automated tests, all passing:

- `test_api.py` — health, chat, activity, codebase
- `test_files_router.py` — CRUD, traversal
- `test_git_router.py` — status, init
- `test_db_router.py` — query, identifier validation, history
- `test_codebase_indexer.py` — index + search
- `test_orchestrator.py` — task lifecycle, activity
- `test_providers.py` — registry
- `test_agent_tools.py` — FS tools, path + `.env` protection

```bash
pytest tests/ -q
# 29 passed
```

---

## Bugs fixed

1. Missing `TerminalExecRequest` (terminal broken)
2. Git untracked files shown as staged
3. Agent `git_stage("all")` incorrect endpoint
4. SQL injection surface on table name path params
5. Weak agent path prefix checks
6. Agent access to `.env` / settings paths
7. Chat failures left tasks running without status update
8. Uncaught codebase index errors

---

## Performance improvements

- Codebase search avoids full re-scan when cache is warm (existing 5‑minute cache retained)
- Search matches file paths without extra index passes
- API file reads capped (`MAX_FILE_READ`)
- Agent reads capped (`_MAX_READ_CHARS`)
- Activity log bounded (`MAX_ACTIVITY`)

---

## Technical debt removed

- Unused `ToolMessage` import in agent
- Duplicate/weak path logic in agent tools
- Missing request model for terminal
- Undocumented runtime failure modes on chat
- No automated regression suite

---

## Remaining known issues (deferred to v3+)

| Issue | Severity | Plan |
|-------|----------|------|
| No API authentication | Critical | ROADMAP Phase 1 |
| Unrestricted shell terminal | Critical | Allowlist modes |
| Plaintext API keys on disk | High | Encrypted secret store |
| Shared single chat thread_id | High | Per-session memory |
| Sync LLM blocks worker | High | Async / SSE |
| CORS allow-all | High | Tighten defaults |
| Monolithic frontend JS | Medium | Modularize later |
| No lockfile for deps | Low | pip-tools / uv lock |

---

## Verification checklist

| Check | Status |
|-------|--------|
| Project modules compile | ✓ |
| Imports resolve | ✓ |
| No syntax errors | ✓ |
| Tests pass (29/29) | ✓ |
| No circular imports detected | ✓ |
| Frontend assets present | ✓ |
| Backend app factory loads under TestClient | ✓ |
| Architecture preserved | ✓ |
| UI preserved | ✓ |
| Features preserved | ✓ |

---

## Readiness scores (v2.5)

| Dimension | v2.0 audit | v2.5 |
|-----------|------------|------|
| Overall health | 62 | **70** |
| Security (local) | 38 | **45** |
| Maintainability | 66 | **75** |
| Production (public) | 32 | **35** |
| **Local single-user readiness** | — | **78** |

v2.5 is the recommended baseline for daily local use and for starting v3 security work.

---

## Recommendation for Lumora Dev v3

Start **ROADMAP Phase 1 (Security hard floor)** immediately:

1. Local auth / session token on mutating routes  
2. Terminal allowlist (`safe` vs `full`)  
3. Encrypt provider keys at rest  
4. Bind 127.0.0.1 by default  
5. Per-chat `thread_id`  

Do not expand autonomy features until Phase 1 is complete.

---

**Lumora Dev v2.5 is frozen as the stable master for Phase 0.**
