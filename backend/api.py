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


class ChatResponse(BaseModel):
    response: str
    task_id: str = ""
    plan_id: str = ""
    activity: list = []


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
    config = {"configurable": {"thread_id": thread_id}}

    # Inject memory context as a prefix message for this turn
    mem_ctx = memory_mod.memory_context_for_agent()
    user_content = req.message
    if mem_ctx:
        user_content = f"{mem_ctx}\n\n### User request\n{req.message}"

    t0 = time.time()
    try:
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
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Agent invoke failed")
        complete_task(task_id, "failed")
        memory_mod.record_task_summary(task_id, req.message.strip()[:80], "failed", str(exc))
        if plan_id:
            try:
                planner_mod.fail_step(plan_id, str(exc))
            except Exception:
                pass
        add_activity("coordinator", f"Task failed: {exc}", "", 0)
        raise HTTPException(status_code=502, detail=f"Agent error: {exc}") from exc

    elapsed_ms = int((time.time() - t0) * 1000)
    response_text = ""
    for msg in reversed(result.get("messages", [])):
        if getattr(msg, "type", None) == "ai" and getattr(msg, "content", None):
            response_text = msg.content
            break

    if not response_text:
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

    return {
        "response": response_text,
        "task_id": task_id,
        "plan_id": plan_id,
        "activity": get_activity(-20),
    }


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
