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
