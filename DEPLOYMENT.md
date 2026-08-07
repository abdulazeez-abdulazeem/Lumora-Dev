# Lumora Dev Deployment & DevOps (v4.0)

## Platforms

| Platform | Mode without token | Live |
|----------|-------------------|------|
| static | Local export to `dist/` | file:// |
| docker | Dry-run if docker missing | `docker build` |
| vercel | Dry-run | `VERCEL_TOKEN` |
| netlify | Dry-run | `NETLIFY_AUTH_TOKEN` |
| railway | Dry-run | `RAILWAY_TOKEN` |
| render | Dry-run | `RENDER_API_KEY` |

## Module

```
backend/deployment/
  deployment_manager.py  # build → deploy → monitor → rollback
  platform_router.py     # adapters (extensible)
  build_manager.py
  environment_manager.py # development / staging / production
  secrets_manager.py     # Fernet-encrypted tokens
  monitoring.py
  rollback.py
  deployment_router.py
```

## API

`POST /deployment/build|deploy|rollback|workflow`  
`GET /deployment/status|history|logs|platforms|snapshots|environments`

## Multi-Agent workflow

`multiagent_deploy_workflow(goal)` runs:
Planner → Research → Testing → Review → Deployment Advisor → Build → Deploy → Health verify

## Agent tools

`deploy_app`, `build_project`, `rollback_deployment`

---

## Container & free-host deploy (v4.0)

### Files

| File | Purpose |
|------|---------|
| `Dockerfile` | API (`uvicorn backend.api:app`) + `server.py` UI proxy |
| `docker-compose.yml` | Local multi-port run (`8000` API, `5000` UI) |
| `render.yaml` | Render free web service blueprint |
| `railway.toml` | Railway Docker deploy hints |
| `scripts/docker-entrypoint.sh` | Process supervisor entrypoint |

### Local Docker

```bash
cp .env.example .env   # set OPENROUTER_API_KEY
docker compose up --build
# API:  http://localhost:8000
# UI:   http://localhost:5000
```

### Render (recommended free tier)

1. New → Web Service → connect this GitHub repo
2. Runtime: **Docker** (uses root `Dockerfile`)
3. Set env: `OPENROUTER_API_KEY`, `LUMORA_BIND=0.0.0.0`
4. Health check path: `/system/health`
5. Free plan cold-starts after idle; fine for demos

### Railway

1. New project → Deploy from GitHub
2. Uses `Dockerfile` / `railway.toml`
3. Set `OPENROUTER_API_KEY`
4. Public URL maps to `PORT` (uvicorn)

### Notes

- Playwright/Chromium is **not** installed in the default image (keeps size small). Uncomment the Playwright lines in `Dockerfile` if browser automation is required in the cloud.
- Lumora is local-first; cloud deploy is best for API demos. Full agent filesystem/git workflows work best on a persistent VM or local machine.

---

## Playwright / browser dependency (Pxxl & cloud)

`playwright` publishes **platform-specific binary wheels only** (manylinux x86_64/aarch64, macOS, Windows). There is **no** Alpine/`musllinux` wheel and no usable pure-Python sdist for arbitrary platforms.

Cloud builders that are Alpine-based, use a restricted package index, or cannot match those tags fail with:

```text
ERROR: No matching distribution found for playwright>=1.40.0
```

**Fix used by this repo:**

| File | Purpose |
|------|---------|
| `requirements.txt` | Core API deps (no Playwright) — use on Pxxl / free cloud |
| `requirements-browser.txt` | Includes Playwright — local dev or Debian/Ubuntu Docker only |

Browser routes already import Playwright **lazily**; the API starts without it. Browser features return an install hint until `requirements-browser.txt` is installed and Chromium is present.
