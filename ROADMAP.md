# Lumora Dev — Roadmap to World-Class Autonomous AI Software Engineering Agent

**Goal:** Evolve Lumora Dev from a capable local AI coding workbench into a reliable, secure, autonomous software engineering agent that can plan, implement, test, review, and ship changes with minimal human supervision.

**Principle:** Ship security and correctness first; autonomy second; polish third.

---

## Phase 0 — Stabilize (1–2 weeks) ✅ partial

*Outcome: trustworthy local single-user tool*

- [x] Fix terminal request schema crash
- [x] Fix git untracked classification
- [x] Fix agent stage-all
- [x] Harden SQL identifiers on path params
- [x] Add pytest suite: path traversal, terminal policy, git porcelain, chat mock
- [x] Unify path safety helper used by agent tools and files_router
- [x] Enforce max file read size on backend + agent
- [ ] requirements.lock / pinned versions
- [x] Structured logging (module loggers: api, files, git, db, indexer)

---

## Phase 1 — Security hard floor (2–3 weeks) — **v3 Phase 1 delivered (core)**

*Outcome: safe to run on a shared machine / private network*

1. **AuthN for API**
   - Local session token or Replit user binding
   - All mutating routes require auth
2. **Terminal policy**
   - Allowlist modes: `safe` (npm/pip/pytest/git read) vs `full` (explicit opt-in)
   - Deny `rm -rf /`, curl|sh, privilege escalation patterns
   - Never `shell=True` without shlex + allowlist; prefer argv lists
3. **Secret store**
   - Encrypt API keys at rest (OS keychain or Fernet with machine key)
   - Never return raw keys from `/settings`
4. **Destructive op gates**
   - Confirm for delete, git push, drop table, force checkout
5. **CORS / bind**
   - Default bind 127.0.0.1; explicit opt-in for 0.0.0.0
6. **Rate limits**
   - Per-IP and per-session LLM and terminal quotas

---

## Phase 2 — Agent reliability (3–4 weeks)

*Outcome: agent completes multi-step tasks without losing the plot*

1. **Per-session memory**
   - Unique `thread_id` per chat/workspace
   - Optional summary compaction for long threads
2. **Async execution**
   - Run graph in thread/process pool; SSE or WebSocket progress stream
3. **Structured tool telemetry**
   - Tools return JSON envelopes; orchestrator records real file/cmd ops (not regex)
4. **Approval modes**
   - `auto` | `confirm-writes` | `confirm-all` for file/git/terminal
5. **Provider single source of truth**
   - Agent `get_llm()` consumes `providers.py` + settings only
6. **Retrieval upgrade**
   - Codebase index: content chunks + symbols; optional embeddings later

---

## Phase 3 — Autonomous engineering loop (4–6 weeks)

*Outcome: plan → edit → test → fix without babysitting*

1. **Task graph**
   - Explicit plan nodes, checklist state, resume after interrupt
2. **Patch engine**
   - Multi-file diffs with apply/rollback; avoid blind full-file overwrites when possible
3. **Test runner integration**
   - Detect pytest/jest/vitest; run, parse failures, feed back into agent
4. **Self-review pass**
   - Dedicated reviewer node before “done”
5. **Repo maps**
   - Dependency graph + “impacted tests” hints
6. **Workspace isolation**
   - Optional per-task git worktree or branch

---

## Phase 4 — Product surface (3–4 weeks)

*Outcome: feels like a serious SE product*

1. Modular frontend (split script.js; optional Vite)
2. Virtualized file tree & editor performance
3. Conflict-aware Git UI (merge state, diff viewer)
4. DB console: read-only mode default; write requires toggle
5. Onboarding wizard (provider key, first index, sample task)
6. OpenAPI-generated TS client for UI

---

## Phase 5 — Multi-user / cloud path (optional, 6+ weeks)

*Only after Phase 1 is solid*

1. Real user accounts, workspace ACLs
2. Sandboxed execution (containers / gVisor / Firecracker)
3. Horizontal API workers + Redis/Postgres for memory & tasks
4. Billing-aware LLM proxy
5. Audit log of every tool invocation

---

## Priority order (next 30 days)

| Priority | Item | Why |
|----------|------|-----|
| P0 | Auth + bind localhost by default | Stops accidental exposure |
| P0 | Terminal allowlist / safer exec | Removes RCE footgun |
| P0 | Basic pytest suite | Prevents regressions |
| P1 | Per-chat thread_id + async chat | Correctness under load |
| P1 | Encrypted/secret-safe settings | Key hygiene |
| P1 | Unified path security in agent | Close bypass |
| P2 | SSE progress for long agent runs | UX |
| P2 | Structured tool results → orchestrator | Real task tracking |
| P2 | Confirm gates for push/delete | Safety |
| P3 | Indexer content search | Better coding agent |
| P3 | Test-runner feedback loop | Autonomy |

---

## Definition of “world-class” for Lumora Dev

An agent that can, on a real repo:

1. Understand the codebase (index + retrieval)
2. Plan a change and get approval when required
3. Edit multiple files safely
4. Run tests and fix failures iteratively
5. Commit on a branch with a clear message
6. Never exfiltrate secrets or run unconstrained shell on a shared host
7. Leave an audit trail of what it did

Everything in this roadmap ladders to that bar without throwing away the current architecture.

---

## Non-goals (near term)

- Rewriting the stack in another language
- Building a full cloud IDE competitor before security is fixed
- Removing local CLI mode
- Mandatory multi-agent process topology before single-agent reliability

---

*Living document — update as phases complete.*

## Phase 2C – Vision & UI Intelligence (done)
- Screenshot analysis, OCR, layout, validation, comparison, annotation
- Agent tools + /vision/* API + Vision panel
- Execution UI-validation hook for automatic repair loops

## Phase 3A – Knowledge Engine (done)
- Document ingestion (MD/TXT/PDF/HTML/JSON/code)
- Semantic search + citations
- Project auto-index (README, CHANGELOG, ROADMAP, docs)
- Agent + Execution integration

## Phase 3B – Multi-Agent Collaboration (done)
- Specialized agent team + shared queue/messaging/context


## Phase 3C – System Integration & Reliability (done)
- Health, telemetry, diagnostics, event bus, System panel


## v4.0 – Deployment & DevOps (done)
- Multi-platform deploy, build, rollback, monitoring

