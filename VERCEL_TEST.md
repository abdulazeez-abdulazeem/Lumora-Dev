# Vercel temporary test deployment

**Purpose:** Temporary serverless smoke-test of Lumora Dev on Vercel.
**Not** a permanent architecture change. Docker / Procfile / server.py remain primary for full deployments.

## Entrypoints (additive only)

| File | Role |
|------|------|
| `api/index.py` | Vercel Python function → imports `backend.api:app` |
| `app.py` | Alternate root entry for Vercel FastAPI preset |
| `vercel.json` | Routes traffic to `api/index.py` |

Nothing was deleted. Dockerfile, Procfile, server.py, browser, Playwright remain.

## Environment variables

| Variable | Required |
|----------|----------|
| `OPENROUTER_API_KEY` | Yes for chat |
| `PROVIDER` | No (default openrouter) |
| `MODEL` | No |
| `LUMORA_PASSWORD` | No |

## Health

`GET /health` → `{"status":"ok",...}`
