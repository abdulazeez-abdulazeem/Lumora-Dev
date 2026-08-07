# Changelog — Lumora Dev v3

## [3.0.0-phase2a] — 2026-08-06

### Added — Browser Automation
- `backend/browser/` package (Playwright)
- REST API under `/browser/*` (lifecycle, nav, tabs, actions, inspect, screenshots, record/replay)
- Agent tools: browser_open, click, type, inspect, screenshot, close
- Sidebar Browser panel
- Tests: `tests/test_browser.py` (mocked Playwright)
- `BROWSER_AUTOMATION.md`

# Changelog — Lumora Dev v3

## [3.0.0-phase1] — 2026-08-06

Built on v2.5. Architecture preserved.

### Added
- `backend/security.py` — password sessions, Fernet key encryption, terminal policy
- `backend/memory.py` — persistent project memory across restarts
- `backend/planner.py` — subtask plans with pause/resume/retry
- `backend/edit_session.py` — multi-file edit snapshots + rollback
- API routes: `/auth/*`, `/memory/*`, `/planner/*`, `/edits/*`, `/activity/timeline`, `/codebase/architecture`, semantic search mode
- Agent tools: `remember`, `begin_edit_session`, `edit_session_write`, `edit_session_rollback`
- Chat auto-creates a plan and injects memory context
- Indexer: `architecture_overview()`, `semantic_search()`
- Tests: security, memory, planner, edit_session (41 total)

### Changed
- Default bind `127.0.0.1` for `server.py` (`LUMORA_BIND` override)
- Terminal requires allowlist in `safe` mode; destructive needs `confirm`
- Settings API keys encrypted at rest
- Agent decrypts keys when building LLM client
- API version `3.0.0-phase1`

### Security
- Optional local password gate via `X-Lumora-Token`
- Secret files gitignored (`.lumora-secret.key`, `.lumora-security.json`, memory, plans, edits)

## v3.0.0-phase2c – Vision & UI Intelligence (2026-08-06)

### Added
- `backend/vision/` module: analyze, OCR, layout, validate, compare, annotate
- REST endpoints under `/vision/*`
- Agent tools: analyze_screenshot, validate_ui, compare_ui, annotate_screenshot, inspect_layout
- Frontend Vision panel
- Execution UI-validation hook (`backend/execution/ui_loop.py`)
- Tests: tests/test_vision.py
- Docs: VISION.md, V3_PHASE2C_REPORT.md

### Changed
- API version → 3.0.0-phase2c
- requirements.txt: +Pillow

### Preserved
- All Phase 2A Browser Automation, Memory, Planner, Edit Sessions, Git, Terminal, existing agent tools

## v3.0.0-phase3a – Knowledge Engine (2026-08-06)

### Added
- `backend/knowledge/` – loader, chunker, embeddings, vector store, retrieval, summarizer, citations
- REST `/knowledge/*` (import, search, list, delete, reindex, status)
- Agent tools: search_knowledge, import_documents, summarize_document, cite_sources, search_project_docs
- Execution hook `knowledge_context_for_goal`
- Frontend Knowledge panel
- Tests: tests/test_knowledge.py
- Docs: KNOWLEDGE_ENGINE.md, V3_PHASE3A_REPORT.md

### Changed
- API version → 3.0.0-phase3a

### Preserved
- All Phase 2C Vision, Phase 2A Browser, Memory, Planner, Edit Sessions, Git, Terminal, Agent tools

## v3.0.0-phase3b – Multi-Agent Collaboration (2026-08-06)

### Added
- `backend/multiagent/` – coordinator, dispatcher, shared context, messaging, task queue
- Specialized roles: planner, research, coding, testing, debugging, review, documentation, deployment_advisor
- REST `/multiagent/*`
- Agent tools: assign_task, delegate_work, share_context, request_review, request_test, request_research
- Frontend Agents panel
- Tests: tests/test_multiagent.py
- Docs: MULTI_AGENT.md, V3_PHASE3B_REPORT.md, VERSION_REPORT.md

### Changed
- API version → 3.0.0-phase3b

### Preserved
- Knowledge Engine, Vision, Browser, Memory, Planner, Execution hooks, Git, Terminal

## v3.0.0-phase3c – System Integration & Reliability (2026-08-06)

### Added
- `backend/system/` – orchestrator, health, diagnostics, telemetry, metrics, event bus
- REST `/system/health|status|metrics|telemetry|diagnostics|events|warmup`
- API latency telemetry middleware
- Frontend System panel
- Tests: tests/test_system.py
- Docs: SYSTEM.md, V3_PHASE3C_REPORT.md, VERSION_REPORT.md

### Changed
- API version → 3.0.0-phase3c

### Preserved
- Multi-Agent, Knowledge, Vision, Browser, Memory, Planner, Execution, Git, Terminal

## v4.0.0 – Deployment & DevOps Automation (2026-08-06)

### Added
- `backend/deployment/` – platforms, build, environments, secrets, monitoring, rollback
- Platforms: static, docker, vercel, netlify, railway, render
- REST `/deployment/*`
- Agent tools: deploy_app, build_project, rollback_deployment
- Multi-Agent deploy workflow
- Frontend Deploy panel
- Docs: DEPLOYMENT.md, V4_DEPLOYMENT_REPORT.md

### Changed
- API version → 4.0.0

### Preserved
- All v3 subsystems (System, Multi-Agent, Knowledge, Vision, Browser, Memory, Planner)
