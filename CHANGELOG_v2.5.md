# Changelog — Lumora Dev v2.5

## [2.5.0] — 2026-08-06

Stability / foundation-freeze release. No major new features. Focus: reliability, safety fixes, tests, maintainability.

### Fixed
- `TerminalExecRequest` model missing (terminal endpoint runtime failure)
- Git status porcelain: untracked (`??`) files misclassified as staged
- Agent `git_stage("all")` did not call `/git/stage-all`
- SQL identifier validation for DB table/`order` path params
- Agent path checks used weak `startswith`; now use `relative_to` + protected path list
- Agent could read/write `.env` / settings; now blocked
- API chat had no recovery on agent/provider failures; now marks task failed and returns 502/503
- Codebase routes lacked error handling
- `.gitignore` index filename mismatch (`.codebase-index.json`)

### Improved
- Structured logging across API, files, git, db, indexer
- Agent init failure no longer crashes lifespan silently
- File read size limits (agent + API)
- Codebase search matches file paths as well as symbol names
- Indexer logs progress; activity log size constant
- API version string set to `2.5.0`
- Docstrings / module headers updated for v2.5

### Testing
- New `tests/` suite (29 tests): API, files, git, db, indexer, orchestrator, providers, agent tools
- `pytest` added to requirements

### Documentation
- README.md updated for v2.5
- CHANGELOG_v2.5.md (this file)
- V2_5_RELEASE_REPORT.md
- ROADMAP.md / PROJECT_AUDIT_REPORT.md retained with Phase 0 progress

### Not changed (by design)
- Architecture and UI
- Feature set (no new product features)
- Auth model (still local-trust; planned for v3)
