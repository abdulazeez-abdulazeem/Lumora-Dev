# Lumora Dev v4.0

**Autonomous software engineering agent — local-first, safety-aware**

Evolution of v2.5. Same architecture. New: local security, persistent memory, task planner, edit rollback, richer codebase intelligence.

---

### Quick Start

```bash
cp .env.example .env   # add OPENROUTER_API_KEY
pip install -r requirements.txt
# API (prefer localhost)
uvicorn backend.api:app --host 127.0.0.1 --port 8000
# UI proxy (localhost by default; LUMORA_BIND=0.0.0.0 to expose)
python server.py
```

Open http://127.0.0.1:5000

Optional local password:

```bash
curl -X POST http://127.0.0.1:8000/auth/set-password -H 'Content-Type: application/json' -d '{"password":"yourpass"}'
# send header X-Lumora-Token: <token> on subsequent requests
```

CLI: `python agent.py`

Tests: `pytest tests/ -q`

---

### Phase 2A — Browser Automation

Playwright-based browsing for the agent and UI. See `BROWSER_AUTOMATION.md`.

```bash
pip install playwright && playwright install chromium
```

### Phase 1 capabilities

| Area | What you get |
|------|----------------|
| **Local security** | Bind 127.0.0.1 by default; optional password; encrypted API keys; terminal allowlist + destructive confirm |
| **Memory** | Architecture, preferences, decisions, completed/pending work — persists in `.lumora-memory.json` |
| **Planner** | Auto-decompose chat into steps; pause / resume / retry |
| **Codebase intelligence** | Symbol search, semantic token search, architecture overview, dependency hubs |
| **Edit sessions** | Multi-file writes with rollback |
| **Observability** | `/activity/timeline` — tasks, plans, tool activity |

---

### Architecture (unchanged shape)

```
Browser → server.py (:5000, localhost default)
            → FastAPI backend.api (:8000)
                 files | git | db | chat | memory | planner | edits | auth
            agent.py (LangGraph + tools)
```

---

### Security notes (local single-user)

- Do **not** set `LUMORA_BIND=0.0.0.0` on untrusted networks without enabling password auth.
- Terminal defaults to **safe** mode (allowlist). Destructive commands need `confirm=true`.
- API keys in settings are encrypted with a local Fernet key (`.lumora-secret.key`).

---

### Version

**Lumora Dev v3.0.0-phase2a**

See `CHANGELOG_v3.md` and `V3_PHASE1_REPORT.md`.
