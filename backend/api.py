"""
Lumora Dev – FastAPI backend (v3 Phase 2A)
Wraps the LangGraph agent and exposes HTTP routes for chat, activity,
codebase intelligence, memory, planner, auth, and edit sessions.
"""
import sys
import os
import logging
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Logger must exist before any try/except that logs (VERCEL import-safety).
logger = logging.getLogger("lumora.api")

# Original: from langchain_core.messages import HumanMessage
try:
    from langchain_core.messages import HumanMessage
except Exception:  # VERCEL: allow API/UI boot if langchain not yet resolved
    HumanMessage = None  # type: ignore
    logger.warning("langchain_core.messages.HumanMessage unavailable")

def _safe_create_agent():
    try:
        from agent import create_agent as _ca
        return _ca()
    except Exception as e:
        logger.exception("Agent unavailable at startup: %s", e)
        return None

# Original hard imports (preferred when all subsystems resolve):
# from backend.files_router import router as files_router
# from backend.git_router import router as git_router
# from backend.db_router import router as db_router
# from backend.browser.browser_router import router as browser_router
# from backend.vision.vision_router import router as vision_router
# from backend.knowledge.knowledge_router import router as knowledge_router
# from backend.multiagent.multiagent_router import router as multiagent_router
# from backend.system.system_router import router as system_router
# from backend.deployment.deployment_router import router as deployment_router
#
# Soft-import so one optional subsystem cannot block the whole API on Vercel.
from fastapi import APIRouter as _APIRouter

def _soft_router(label: str, import_path: str):
    try:
        mod = __import__(import_path, fromlist=["router"])
        return mod.router
    except Exception as e:
        logger.warning("Router %s unavailable: %s", label, e)
        r = _APIRouter(prefix=f"/_unavailable/{label}", tags=[label])
        @r.get("")
        def _unavail():
            return {"status": "unavailable", "router": label, "detail": str(e)[:300]}
        return r

files_router = _soft_router("files", "backend.files_router")
git_router = _soft_router("git", "backend.git_router")
db_router = _soft_router("db", "backend.db_router")
browser_router = _soft_router("browser", "backend.browser.browser_router")
vision_router = _soft_router("vision", "backend.vision.vision_router")
knowledge_router = _soft_router("knowledge", "backend.knowledge.knowledge_router")
multiagent_router = _soft_router("multiagent", "backend.multiagent.multiagent_router")
system_router = _soft_router("system", "backend.system.system_router")
deployment_router = _soft_router("deployment", "backend.deployment.deployment_router")
from backend.orchestrator import (
    create_task, update_task, complete_task,
    parse_agent_response, add_activity, get_activity,
    get_recent_tasks, get_task,
)
from backend.codebase_indexer import (
    index_project, search_index, get_stats,
    architecture_overview, semantic_search,
)
from backend import memory as memory_mod
from backend import planner as planner_mod
from backend import edit_session as edit_mod
from backend import jobs as jobs_mod
from backend.security import (
    is_auth_enabled, login as security_login, set_password, clear_password,
    validate_session, create_session,
)

_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        _agent = _safe_create_agent()
        if _agent is not None:
            logger.info("Lumora Dev agent initialised.")
        else:
            logger.warning("Agent not initialised — chat returns 503 until OPENROUTER_API_KEY/config fixed")
    except Exception:
        logger.exception("Failed to initialise agent — chat will return 503 until fixed")
        _agent = None
    yield


app = FastAPI(
    title="Lumora Dev API",
    description="Autonomous software engineering agent API (local-first)",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths that never require auth (health + login)
_PUBLIC_PREFIXES = ("/", "/auth/", "/docs", "/openapi.json", "/redoc")


@app.middleware("http")
async def local_auth_middleware(request: Request, call_next):
    path = request.url.path
    if not is_auth_enabled():
        return await call_next(request)
    if path == "/" or path.startswith("/auth/") or path in (
        "/docs", "/openapi.json", "/redoc", "/health",
        "/styles.css", "/script.js", "/darkveil.js", "/favicon.ico",
    ):
        return await call_next(request)
    token = request.headers.get("X-Lumora-Token") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not validate_session(token):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})
    return await call_next(request)



@app.middleware("http")
async def _lumora_workspace_middleware(request, call_next):
    """Bind active user workspace for this request (Files / agent isolation)."""
    try:
        from backend.files_router import set_active_workspace
        ws = request.headers.get("X-Lumora-Workspace") or request.query_params.get("workspace") or ""
        set_active_workspace(ws)
        # Also export for agent tools in-process
        import os
        if ws:
            from backend.files_router import USER_WORKSPACES_ROOT
            os.environ["LUMORA_PROJECT_ROOT"] = str(USER_WORKSPACES_ROOT / ws)
        else:
            os.environ.pop("LUMORA_PROJECT_ROOT", None)
    except Exception:
        pass
    return await call_next(request)


@app.middleware("http")
async def _lumora_telemetry_middleware(request, call_next):
    import time
    t0 = time.time()
    response = await call_next(request)
    try:
        from backend.system.orchestrator import get_system_orchestrator
        get_system_orchestrator().record_api_latency(
            request.url.path, (time.time() - t0) * 1000, response.status_code
        )
    except Exception:
        pass
    return response

app.include_router(files_router)
app.include_router(git_router)
app.include_router(db_router)
app.include_router(browser_router)
app.include_router(vision_router)
app.include_router(knowledge_router)
app.include_router(multiagent_router)
app.include_router(system_router)
app.include_router(deployment_router)


# ── Schemas ────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    thread_id: str = "lumora-api-session"
    plan: bool = True
    # When true, prefer long-running budget / job tracking (website builds).
    async_mode: bool = False
    # Active user project workspace id (isolated from Lumora source tree)
    workspace_id: str = ""


class ChatResponse(BaseModel):
    response: str
    task_id: str = ""
    plan_id: str = ""
    activity: list = []
    status: str = "completed"  # completed | timed_out | failed | running | queued
    job_id: str = ""
    partial: bool = False
    workspace_id: str = ""


class ActivityResponse(BaseModel):
    activity: list
    tasks: list


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str = "3.0.0-phase2a"


class LoginRequest(BaseModel):
    password: str = ""


class SetPasswordRequest(BaseModel):
    password: str


class MemoryUpdate(BaseModel):
    architecture: str | None = None
    coding_preferences: list | None = None
    user_preferences: dict | None = None
    notes: list | None = None


class PlanCreateRequest(BaseModel):
    title: str
    steps: list[str] = Field(default_factory=list)
    message: str = ""
    parent_task_id: str = ""


class EditBeginRequest(BaseModel):
    label: str = ""


class EditWriteRequest(BaseModel):
    session_id: str
    path: str
    content: str


# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Platform health probes (Pxxl/Render/Railway/Koyeb/Northflank/Vercel)."""
    return {
        "status": "ok",
        "service": "Lumora Dev",
        "version": "4.0.0",
        "backend_api_loaded": True,
        "agent_ready": _agent is not None,
        "chat": "/chat",
    }


@app.get("/")
def root():
    """Serve UI index when present; otherwise JSON service info."""
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
    index = os.path.join(frontend_dir, "index.html")
    if os.path.isfile(index):
        return FileResponse(index, media_type="text/html; charset=utf-8")
    return {"status": "ok", "service": "Lumora Dev", "version": "4.0.0"}


@app.post("/auth/login")
def auth_login(req: LoginRequest):
    try:
        token = security_login(req.password)
        return {"token": token, "auth_enabled": is_auth_enabled()}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@app.post("/auth/set-password")
def auth_set_password(req: SetPasswordRequest):
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    set_password(req.password)
    token = create_session()
    return {"ok": True, "token": token, "auth_enabled": True}


@app.post("/auth/disable")
def auth_disable():
    clear_password()
    return {"ok": True, "auth_enabled": False}


@app.get("/auth/status")
def auth_status():
    return {"auth_enabled": is_auth_enabled()}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent is not initialised yet")

    # Bind user workspace so tools write into the project, not Lumora source
    try:
        from backend.files_router import set_active_workspace, USER_WORKSPACES_ROOT, effective_root
        import os
        if req.workspace_id:
            set_active_workspace(req.workspace_id)
            os.environ["LUMORA_PROJECT_ROOT"] = str(USER_WORKSPACES_ROOT / req.workspace_id)
            # Refresh agent module root for this process when possible
            try:
                import agent as _agent_mod
                _agent_mod.PROJECT_ROOT = effective_root()
            except Exception:
                pass
    except Exception:
        pass

    task_id = create_task(req.message.strip()[:80])
    add_activity("coordinator", f"New task: {req.message.strip()[:100]}", "", 0)
    memory_mod.record_task_summary(task_id, req.message.strip()[:80], "running")

    plan_id = ""
    if req.plan:
        steps = planner_mod.simple_decompose(req.message)
        plan = planner_mod.create_plan(req.message.strip()[:80], steps, parent_task_id=task_id)
        plan_id = plan["id"]
        planner_mod.start_step(plan_id, 0)
        add_activity("planner", f"Plan {plan_id}: {len(steps)} steps", steps[0] if steps else "", 5)

    thread_id = req.thread_id or "lumora-api-session"
    long_task = req.async_mode or jobs_mod.is_long_running_request(req.message)

    # Long builds: queue job and return immediately (frontend drives /tick).
    if long_task:
        gen = projects_generate(req)
        job_id = gen["job_id"]
        return {
            "response": (
                "Starting project generation…\n\n"
                f"**Job:** `{job_id}`\n"
                f"**Workspace:** `{gen.get('workspace_id') or req.workspace_id or 'pending'}`\n\n"
                "I'll build this in stages (plan → generate files → review). "
                "Progress updates will appear here; Files and Preview refresh when each stage completes."
            ),
            "task_id": task_id,
            "plan_id": plan_id,
            "activity": get_activity(-20),
            "status": "queued",
            "job_id": job_id,
            "partial": True,
            "workspace_id": gen.get("workspace_id") or req.workspace_id or "",
        }

    # Short chat path (sync)
    time_budget_s = 50
    recursion_limit = 12
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }

    job = jobs_mod.create_job(req.message, thread_id=thread_id, task_id=task_id, workspace_id=req.workspace_id or "")
    job["status"] = "running"
    jobs_mod.save_job(job)
    job_id = job["id"]

    # Inject memory context as a prefix message for this turn
    mem_ctx = memory_mod.memory_context_for_agent()
    user_content = req.message
    if mem_ctx:
        user_content = f"{mem_ctx}\n\n### User request\n{req.message}"
    if long_task:
        user_content += (
            "\n\n### Runtime constraints\n"
            "You are running on a time-limited serverless host. "
            "Complete the website with a small set of focused files "
            "(e.g. index.html, styles.css, script.js). "
            "Prefer write_file over long exploration. Avoid browser tools unless required."
        )

    t0 = time.time()
    result = {"messages": []}
    timed_out = False

    def _state_messages():
        try:
            st = _agent.get_state(config)
            if st and getattr(st, "values", None):
                return st.values.get("messages") or []
        except Exception:
            pass
        return []

    try:
        # Short tasks: classic invoke. Long tasks: stream with wall-clock budget
        # so we can return partial output before Vercel hard-kills at maxDuration.
        deadline = t0 + time_budget_s
        if long_task and hasattr(_agent, "stream"):
            for event in _agent.stream(
                {"messages": [HumanMessage(content=user_content)]},
                config=config,
                stream_mode="values",
            ):
                if isinstance(event, dict) and event.get("messages"):
                    result = event
                if time.time() >= deadline:
                    timed_out = True
                    add_activity(
                        "coordinator",
                        f"Time budget {time_budget_s}s reached — returning partial result",
                        "",
                        80,
                    )
                    break
        else:
            result = _agent.invoke(
                {"messages": [HumanMessage(content=user_content)]},
                config=config,
            )
    except ValueError as exc:
        logger.warning("Agent configuration error: %s", exc)
        complete_task(task_id, "failed")
        memory_mod.record_task_summary(task_id, req.message.strip()[:80], "failed", str(exc))
        if plan_id:
            try:
                planner_mod.fail_step(plan_id, str(exc))
            except Exception:
                pass
        add_activity("coordinator", f"Task failed: {exc}", "", 0)
        try:
            job["status"] = "failed"
            job["error"] = str(exc)
            jobs_mod.save_job(job)
        except Exception:
            pass
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        name = type(exc).__name__
        # Agent tool loops (GraphRecursionError): return best-effort partial text instead of 502.
        if name == "GraphRecursionError" or "Recursion limit" in str(exc):
            logger.warning("Agent recursion limit hit — returning partial: %s", exc)
            timed_out = True
            msgs = result.get("messages") if isinstance(result, dict) else None
            if not msgs:
                msgs = _state_messages()
            result = {"messages": msgs or []}
            add_activity("coordinator", "Agent step limit reached — partial result", "", 80)
        else:
            logger.exception("Agent invoke failed")
            complete_task(task_id, "failed")
            memory_mod.record_task_summary(task_id, req.message.strip()[:80], "failed", str(exc))
            if plan_id:
                try:
                    planner_mod.fail_step(plan_id, str(exc))
                except Exception:
                    pass
            add_activity("coordinator", f"Task failed: {exc}", "", 0)
            try:
                job["status"] = "failed"
                job["error"] = str(exc)
                jobs_mod.save_job(job)
            except Exception:
                pass
            detail = str(exc)
            code = 502
            if "429" in detail or "Rate limit" in detail or "rate limit" in detail.lower():
                code = 503
                detail = (
                    "OpenRouter rate limit exceeded (free-tier daily quota). "
                    "Wait for reset or add credits / switch MODEL. "
                    f"Original: {exc}"
                )
            raise HTTPException(status_code=code, detail=detail) from exc

    elapsed_ms = int((time.time() - t0) * 1000)
    response_text = ""
    for msg in reversed(result.get("messages", [])):
        if getattr(msg, "type", None) == "ai" and getattr(msg, "content", None):
            response_text = msg.content
            break

    if not response_text:
        if timed_out:
            response_text = (
                "Work started but no final assistant message was produced before the "
                "serverless time budget. Send a follow-up message to continue."
            )
        else:
            complete_task(task_id, "failed")
            raise HTTPException(status_code=502, detail="Agent returned no response")

    try:
        parse_agent_response(response_text, task_id)
    except Exception:
        logger.exception("Failed to parse agent response for task %s", task_id)

    if "Progress: 100%" in response_text or "Complete!" in response_text:
        complete_task(task_id, "completed")
        memory_mod.record_task_summary(task_id, req.message.strip()[:80], "completed")
        if plan_id:
            plan = planner_mod.get_plan(plan_id)
            if plan:
                for i, step in enumerate(plan["steps"]):
                    if step["status"] != "done":
                        planner_mod.complete_step(plan_id, i)
        add_activity("coordinator", f"Task completed in {elapsed_ms}ms", "", 100)
    else:
        add_activity("coordinator", f"Agent responded ({elapsed_ms}ms)", "", 50)
        if plan_id:
            try:
                planner_mod.complete_step(plan_id)
            except Exception:
                pass

    status = "timed_out" if timed_out else "completed"
    job["status"] = status
    job["response"] = response_text
    job["elapsed_ms"] = elapsed_ms
    job["progress"] = 80 if timed_out else 100
    job["partial"] = timed_out
    jobs_mod.save_job(job)

    if timed_out:
        complete_task(task_id, "completed")
        response_text = (
            response_text
            + "\n\n---\n_Note: Generation hit the serverless time budget. "
            "Partial work above is preserved. Re-send a follow-up like "
            "\"continue the Midnight Brew site\" to resume on the same thread._"
        )

    return {
        "response": response_text,
        "task_id": task_id,
        "plan_id": plan_id,
        "activity": get_activity(-20),
        "status": status,
        "job_id": job_id,
        "partial": timed_out,
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs_mod.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Strip heavy message payload for light polls
    return {
        "id": job.get("id"),
        "status": job.get("status"),
        "stage": job.get("stage"),
        "progress": job.get("progress", 0),
        "message": job.get("response") or job.get("message") or "",
        "response": job.get("response") or "",
        "error": job.get("error") or "",
        "reason": job.get("reason") or "",
        "user_message": job.get("user_message") or "",
        "retryable": bool(job.get("retryable", True)),
        "error_category": job.get("error_category") or "",
        "files_created": job.get("files_created") or [],
        "workspace_id": job.get("workspace_id") or "",
        "tick_count": job.get("tick_count") or 0,
        "elapsed_ms": job.get("elapsed_ms") or 0,
        "partial": bool(job.get("partial")),
        "task_id": job.get("task_id") or "",
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }


@app.get("/jobs")
def list_jobs(limit: int = 20):
    return {"jobs": jobs_mod.list_recent_jobs(limit)}


@app.post("/projects/generate")
def projects_generate(req: ChatRequest):
    """
    Queue a long-running project generation job and return immediately.
    Frontend must drive work via POST /jobs/{id}/tick.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    workspace_id = req.workspace_id or ""
    # Auto-create workspace when missing
    if not workspace_id:
        try:
            from backend import files_router as fr
            import re
            m = re.search(r"(?:called|named|for)\s+([A-Za-z0-9][A-Za-z0-9 \-]{1,40})", req.message, re.I)
            name = (m.group(1) if m else "Generated Project").strip()[:40]
            created = fr.create_workspace(
                fr.WorkspaceCreateRequest(
                    name=name,
                    description=req.message[:120],
                    template="html",
                    framework="html",
                )
            )
            workspace_id = created.get("id") or name.lower().replace(" ", "-")
        except Exception as exc:
            logger.warning("Auto workspace create failed: %s", exc)

    thread_id = req.thread_id or (f"ws-{workspace_id}" if workspace_id else "lumora-api-session")
    job = jobs_mod.create_job(
        req.message,
        thread_id=thread_id,
        workspace_id=workspace_id,
    )
    job["status"] = "queued"
    job["stage"] = "queued"
    job["progress"] = 0
    jobs_mod.save_job(job)
    add_activity("coordinator", f"Queued generation job {job['id']}", workspace_id, 5)
    return {
        "job_id": job["id"],
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "workspace_id": workspace_id,
        "message": "Job queued. Poll GET /jobs/{id} and drive POST /jobs/{id}/tick.",
    }


@app.post("/jobs/{job_id}/tick")
def jobs_tick(job_id: str):
    """
    Run one bounded LangGraph slice for the job. Designed for Vercel:
    each invocation should finish well under maxDuration.
    Concurrent ticks for the same job are rejected while locked.
    """
    import time as _time

    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent is not initialised yet")
    job = jobs_mod.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") == "completed":
        return get_job(job_id)
    if job.get("status") == "failed":
        return get_job(job_id)

    # Simple lock to prevent duplicate simultaneous ticks
    now = _time.time()
    locked_until = float(job.get("locked_until") or 0)
    if locked_until > now and job.get("status") == "running":
        return get_job(job_id)

    job["locked_until"] = now + 55
    jobs_mod.save_job(job)

    try:
        updated = jobs_mod.run_job_tick(_agent, job, max_steps=4, time_budget_s=45.0)
        updated["locked_until"] = 0
        jobs_mod.save_job(updated)
    except Exception as exc:
        logger.exception("Job tick failed")
        job = jobs_mod.load_job(job_id) or job
        job = jobs_mod.apply_pause(job, exc)
        job["locked_until"] = 0
        jobs_mod.save_job(job)
        return get_job(job_id)

    add_activity(
        "coordinator",
        f"Job {job_id} tick={updated.get('tick_count')} stage={updated.get('stage')} {updated.get('progress')}%",
        ",".join((updated.get("files_created") or [])[:5]),
        int(updated.get("progress") or 0),
    )
    return get_job(job_id)


@app.post("/jobs/{job_id}/continue")
def jobs_continue(job_id: str):
    """Resume a paused job (same as tick)."""
    job = jobs_mod.load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") == "paused":
        job["status"] = "running"
        job["reason"] = ""
        job["error"] = ""
        jobs_mod.save_job(job)
    return jobs_tick(job_id)


@app.get("/activity", response_model=ActivityResponse)
def get_activity_route(since: int = 0):
    return {
        "activity": get_activity(since),
        "tasks": get_recent_tasks(10),
    }


@app.get("/activity/timeline")
def activity_timeline(limit: int = 50):
    """Observability: activity + plans + recent tasks."""
    return {
        "activity": get_activity()[-limit:],
        "tasks": get_recent_tasks(10),
        "plans": planner_mod.list_plans(10),
        "memory_updated_at": memory_mod.get_memory().get("updated_at", ""),
    }


# ── Codebase Intelligence ──────────────────────────────────────────────────
@app.post("/codebase/index")
def codebase_index():
    try:
        index = index_project(force=True)
        overview = architecture_overview()
        if overview.get("summary"):
            memory_mod.set_architecture(overview["summary"])
        return {"stats": index.get("stats", {}), "indexed_at": index.get("indexed_at", 0), "overview": overview}
    except Exception as exc:
        logger.exception("Codebase index failed")
        raise HTTPException(status_code=500, detail=f"Index failed: {exc}") from exc


@app.get("/codebase/stats")
def codebase_stats_route():
    try:
        index_project()
        return get_stats()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/codebase/search")
def codebase_search(q: str = "", type: str = "", mode: str = "symbol"):
    try:
        index_project()
        if mode == "semantic":
            results = semantic_search(q, limit=30)
        else:
            results = search_index(q, limit=30)
        if type:
            results = [r for r in results if r.get("type") == type]
        return {"results": results, "query": q, "mode": mode}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/codebase/architecture")
def codebase_architecture():
    try:
        return architecture_overview()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Memory ─────────────────────────────────────────────────────────────────
@app.get("/memory")
def memory_get():
    return memory_mod.get_memory()


@app.put("/memory")
def memory_put(req: MemoryUpdate):
    kwargs = {k: v for k, v in req.model_dump().items() if v is not None}
    return memory_mod.update_memory(**kwargs)


@app.post("/memory/decision")
def memory_decision(decision: str, context: str = ""):
    memory_mod.remember_decision(decision, context)
    return {"ok": True}


@app.post("/memory/preference")
def memory_preference(key: str, value: str):
    memory_mod.remember_preference(key, value)
    return {"ok": True}


# ── Planner ────────────────────────────────────────────────────────────────
@app.post("/planner/create")
def planner_create(req: PlanCreateRequest):
    steps = req.steps or planner_mod.simple_decompose(req.message or req.title)
    plan = planner_mod.create_plan(req.title, steps, parent_task_id=req.parent_task_id)
    return plan


@app.get("/planner/list")
def planner_list():
    return {"plans": planner_mod.list_plans()}


@app.get("/planner/{plan_id}")
def planner_get(plan_id: str):
    plan = planner_mod.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.get("/planner/{plan_id}/progress")
def planner_progress(plan_id: str):
    try:
        return planner_mod.plan_progress(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/planner/{plan_id}/pause")
def planner_pause(plan_id: str):
    try:
        return planner_mod.pause_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/planner/{plan_id}/resume")
def planner_resume(plan_id: str):
    try:
        return planner_mod.resume_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/planner/{plan_id}/retry")
def planner_retry(plan_id: str, index: int | None = None):
    try:
        return planner_mod.retry_step(plan_id, index)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/planner/{plan_id}/complete-step")
def planner_complete_step(plan_id: str, index: int | None = None):
    try:
        return planner_mod.complete_step(plan_id, index)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ── Edit sessions (multi-file + rollback) ──────────────────────────────────
@app.post("/edits/begin")
def edits_begin(req: EditBeginRequest):
    sid = edit_mod.begin_session(req.label)
    return {"session_id": sid}


@app.post("/edits/write")
def edits_write(req: EditWriteRequest):
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    try:
        return edit_mod.record_write(req.session_id, req.path, root, req.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.post("/edits/{session_id}/validate")
def edits_validate(session_id: str):
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    try:
        return {"results": edit_mod.validate_session_files(session_id, root)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/edits/{session_id}/commit")
def edits_commit(session_id: str):
    try:
        return edit_mod.commit_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.post("/edits/{session_id}/rollback")
def edits_rollback(session_id: str):
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    try:
        return edit_mod.rollback_session(session_id, root)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@app.get("/edits/{session_id}")
def edits_get(session_id: str):
    try:
        return edit_mod.get_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e





# ── Frontend static files (same PORT as API for cloud hosts) ───────────────
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


def _frontend_file(name: str):
    candidate = os.path.normpath(os.path.join(_FRONTEND_DIR, name))
    if not candidate.startswith(os.path.abspath(_FRONTEND_DIR)):
        raise HTTPException(status_code=404, detail="Not found")
    if os.path.isfile(candidate):
        return FileResponse(candidate)
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/styles.css")
def frontend_styles():
    return _frontend_file("styles.css")


@app.get("/script.js")
def frontend_script():
    return _frontend_file("script.js")


@app.get("/darkveil.js")
def frontend_darkveil():
    return _frontend_file("darkveil.js")


@app.get("/favicon.ico")
def frontend_favicon():
    return _frontend_file("favicon.ico")
