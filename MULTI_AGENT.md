# Lumora Dev Multi-Agent Collaboration (v3 Phase 3B)

## Overview

Coordinated team of specialized agents that share Memory, Knowledge Engine,
Planner state, Vision findings, and Execution history.

## Roles

| Role | Responsibility |
|------|----------------|
| planner | Decompose goals, set dependencies |
| research | Query Knowledge Engine / docs before coding |
| coding | Implementation guidance |
| testing | Test plans and validation |
| debugging | Failure analysis |
| review | Quality / security review |
| documentation | Docs and changelog updates |
| deployment_advisor | Deployment readiness advice (no live deploy) |

## Module layout

```
backend/multiagent/
  agent_manager.py    # registry + high-level API
  coordinator.py      # goal → pipeline of dependent tasks
  dispatcher.py       # assign ready tasks to role handlers
  shared_context.py   # goal, notes, vision, execution, knowledge snippets
  messaging.py        # agent-to-agent message bus
  task_queue.py       # tasks, deps, conflicts, status
  multiagent_router.py
```

## Pipeline

Planner → Research → Coding → Testing → Debugging → Review → Documentation

Dependencies ensure order; conflicts are detected when two in-progress tasks touch the same file.

## API

- `POST /multiagent/start` – start goal (optional auto-run)
- `GET /multiagent/status|agents|tasks|messages|history`
- `POST /multiagent/assign|delegate|share|run-ready`

## Agent tools

`assign_task`, `delegate_work`, `share_context`, `request_review`, `request_test`, `request_research`

## Frontend

**Agents** sidebar panel: start goal, status, tasks timeline, messages, active agents.
