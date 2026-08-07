# Lumora Dev System Integration & Reliability (v3 Phase 3C)

## Purpose

Unify all subsystems (Memory, Planner, Knowledge, Browser, Vision, Execution,
Multi-Agent, Git, Terminal, Indexer) under health monitoring, telemetry,
diagnostics, and a shared event bus — without replacing any module.

## Module layout

```
backend/system/
  orchestrator.py   # status, health, metrics, diagnostics, warmup
  health.py         # probes every subsystem
  diagnostics.py    # full report + recovery suggestions
  telemetry.py      # tool/API/agent/knowledge/vision/browser timings
  metrics.py        # counters, timers, gauges
  event_bus.py      # process-wide events
  system_router.py  # /system/*
```

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /system/health` | Component health matrix |
| `GET /system/status` | Overall status + uptime |
| `GET /system/metrics` | Counters / timers / gauges |
| `GET /system/telemetry` | Metrics + recent events |
| `GET /system/diagnostics` | Full diagnostic report |
| `GET /system/events` | Event history |
| `POST /system/warmup` | Light subsystem warm-up |

## Frontend

**System** sidebar panel: Health, Metrics, Diagnostics, Events, Warmup.

## Design

- Probes existing modules only — no behavior changes
- API latency middleware records timings automatically
- Recovery actions suggested per degraded component
