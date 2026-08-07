# API Integration

Base URL: Settings → Backend URL (default `http://127.0.0.1:8000`).

| Area | Paths |
|------|-------|
| System | `/system/health|status|metrics|diagnostics` |
| Knowledge | `/knowledge/search|status|reindex` |
| Multi-Agent | `/multiagent/start|status|agents|tasks|messages` |
| Deployment | `/deployment/build|deploy|history|platforms` |
| Browser | `/browser/status|launch|goto|screenshot|close` |
| Vision | `/vision/analyze|status` |
| Chat | `/chat` |
| Files | `/files/list|read|write` |
| Memory | `/memory/list|remember` |

Auth header: `X-Lumora-Token` from secure storage.
