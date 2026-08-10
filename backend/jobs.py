"""
Lumora Dev – Long-running job store + tick runner (serverless-safe).

Vercel functions are ephemeral: work must resume via repeated bounded
HTTP "ticks", not BackgroundTasks/threads after the response returns.

Job state (messages, progress, files) is persisted under a writable dir.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

def _jobs_dir() -> Path:
    preferred = Path(__file__).resolve().parent.parent / ".lumora-jobs"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        probe = preferred / ".probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return preferred
    except OSError:
        p = Path("/tmp/lumora-jobs")
        p.mkdir(parents=True, exist_ok=True)
        return p


JOBS_DIR = _jobs_dir()

_LONG_KEYWORDS = (
    "build me", "create a website", "create a landing", "landing page",
    "full stack", "generate a project", "scaffold", "build a website",
    "build an app", "create an app", "make a website", "develop a",
    "coffee shop", "ecommerce", "e-commerce", "dashboard app",
    "complete modern", "hero section", "responsive mobile",
)


def is_long_running_request(message: str) -> bool:
    m = (message or "").lower()
    if len(m) > 280:
        return True
    return any(k in m for k in _LONG_KEYWORDS)


def classify_provider_error(exc) -> dict:
    """Map provider/agent exceptions to safe, user-facing recovery info (no secrets)."""
    detail = str(exc) if not isinstance(exc, str) else exc
    low = detail.lower()
    category = "agent_error"
    http_status = None
    retryable = True
    if "429" in detail or "rate limit" in low:
        category = "rate_limit"
        http_status = 429
    elif "504" in detail or "timeout" in low or "timed out" in low:
        category = "timeout"
        http_status = 504
    elif "502" in detail or "503" in detail or "service unavailable" in low or "bad gateway" in low:
        category = "provider_unavailable"
        http_status = 503 if "503" in detail else 502
    elif "401" in detail or "403" in detail or "auth" in low and "api" in low:
        category = "auth"
        http_status = 401
        retryable = False
    elif "400" in detail or "provider returned error" in low or "invalid" in low:
        category = "model_rejected"
        http_status = 400
        retryable = True  # often transient model glitch; allow Continue
    elif "recursion" in low:
        category = "step_limit"
        retryable = True

    messages = {
        "rate_limit": "AI provider rate limit reached. Your project files are safe. Try Continue shortly.",
        "timeout": "The generation step timed out. Your existing files are safe.",
        "provider_unavailable": "The AI provider is temporarily unavailable. Your existing files are safe.",
        "auth": "AI provider authentication failed. Check your API key in Settings. Existing files are safe.",
        "model_rejected": "The selected AI model rejected this request. Your existing files are safe.",
        "step_limit": "This build step hit the step budget. Your files are safe — Continue to resume.",
        "agent_error": "A generation step failed. Your existing files are safe. You can Continue or edit files manually.",
    }
    return {
        "category": category,
        "http_status": http_status,
        "retryable": retryable,
        "user_message": messages.get(category, messages["agent_error"]),
        # Truncated technical detail for logs/UI secondary line (no keys)
        "detail": detail[:280].replace("\n", " "),
    }


def apply_pause(job: dict, exc, *, result_messages=None) -> dict:
    info = classify_provider_error(exc)
    job["status"] = "paused"
    job["stage"] = "paused"
    job["reason"] = info["category"]
    job["error"] = info["detail"]
    job["user_message"] = info["user_message"]
    job["retryable"] = info["retryable"]
    job["error_category"] = info["category"]
    if result_messages is not None:
        job["messages"] = serialize_messages(result_messages)
    job["locked_until"] = 0
    return job


def _path(job_id: str) -> Path:
    safe = "".join(c for c in job_id if c.isalnum() or c in "-_")
    return JOBS_DIR / f"{safe}.json"


def save_job(job: dict) -> None:
    job = dict(job)
    job["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    p = _path(job["id"])
    try:
        p.write_text(json.dumps(job, indent=2), encoding="utf-8")
    except OSError:
        alt = Path("/tmp/lumora-jobs") / p.name
        alt.parent.mkdir(parents=True, exist_ok=True)
        alt.write_text(json.dumps(job, indent=2), encoding="utf-8")


def load_job(job_id: str) -> Optional[dict]:
    for base in (JOBS_DIR, Path("/tmp/lumora-jobs")):
        p = base / f"{''.join(c for c in job_id if c.isalnum() or c in '-_')}.json"
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                return None
    return None


def create_job(
    message: str,
    thread_id: str = "",
    task_id: str = "",
    workspace_id: str = "",
) -> dict:
    jid = f"job-{uuid.uuid4().hex[:12]}"
    job = {
        "id": jid,
        "task_id": task_id or jid,
        "thread_id": thread_id or jid,
        "workspace_id": workspace_id or "",
        "message": message,
        "status": "queued",  # queued|planning|generating|reviewing|running|paused|completed|failed
        "stage": "queued",
        "response": "",
        "error": "",
        "reason": "",
        "progress": 0,
        "tick_count": 0,
        "files_created": [],
        "messages": [],  # serialized LangChain-ish messages for resume
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_ms": 0,
        "partial": False,
        "user_message": "",
        "retryable": True,
        "error_category": "",
        "provider_retries": 0,
        "locked_until": 0,
    }
    save_job(job)
    return job


def list_recent_jobs(limit: int = 20) -> list[dict]:
    jobs = []
    seen = set()
    for base in (JOBS_DIR, Path("/tmp/lumora-jobs")):
        if not base.exists():
            continue
        for p in sorted(base.glob("job-*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.name in seen:
                continue
            seen.add(p.name)
            try:
                jobs.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass
            if len(jobs) >= limit:
                return jobs
    return jobs


# ── Message serialization (cross-invocation resume without MemorySaver) ──

def serialize_messages(messages: list) -> list[dict]:
    out = []
    for msg in messages or []:
        t = getattr(msg, "type", None) or getattr(msg, "role", None) or type(msg).__name__
        t = str(t).lower()
        if t in ("human", "humanmessage"):
            role = "human"
        elif t in ("ai", "aimessage"):
            role = "ai"
        elif t in ("tool", "toolmessage"):
            role = "tool"
        elif t in ("system", "systemmessage"):
            role = "system"
        else:
            role = t
        item: dict[str, Any] = {
            "role": role,
            "content": getattr(msg, "content", "") or "",
        }
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            # ensure JSON-serializable
            try:
                item["tool_calls"] = json.loads(json.dumps(tool_calls, default=str))
            except Exception:
                item["tool_calls"] = []
        if role == "tool":
            item["name"] = getattr(msg, "name", "") or ""
            item["tool_call_id"] = getattr(msg, "tool_call_id", "") or ""
        out.append(item)
    return out


def deserialize_messages(raw: list[dict]):
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

    msgs = []
    for item in raw or []:
        role = (item.get("role") or "human").lower()
        content = item.get("content") or ""
        if role == "human":
            msgs.append(HumanMessage(content=content))
        elif role == "ai":
            kwargs = {"content": content}
            if item.get("tool_calls"):
                kwargs["tool_calls"] = item["tool_calls"]
            msgs.append(AIMessage(**kwargs))
        elif role == "tool":
            msgs.append(
                ToolMessage(
                    content=content,
                    name=item.get("name") or "tool",
                    tool_call_id=item.get("tool_call_id") or "call_0",
                )
            )
        elif role == "system":
            msgs.append(SystemMessage(content=content))
        else:
            msgs.append(HumanMessage(content=content))
    return msgs


def _list_workspace_files(workspace_id: str) -> list[str]:
    if not workspace_id:
        return []
    try:
        from backend.files_router import USER_WORKSPACES_ROOT

        root = USER_WORKSPACES_ROOT / workspace_id
        if not root.exists():
            return []
        files = []
        for p in sorted(root.rglob("*")):
            if p.is_file() and not any(part.startswith(".") for part in p.parts):
                try:
                    files.append(str(p.relative_to(root)))
                except ValueError:
                    files.append(p.name)
        return files
    except Exception:
        return []


def _stage_for(progress: int, status: str) -> str:
    if status in ("completed", "failed", "paused", "queued"):
        return status if status != "queued" else "queued"
    if progress < 15:
        return "planning"
    if progress < 75:
        return "generating"
    if progress < 95:
        return "reviewing"
    return "finishing"


def run_job_tick(agent, job: dict, *, max_steps: int = 4, time_budget_s: float = 45.0) -> dict:
    """
    Execute a bounded slice of the LangGraph agent for this job.
    Persists message checkpoint + progress. Safe for Vercel maxDuration slices.
    """
    from langchain_core.messages import HumanMessage

    job = dict(job)
    job_id = job["id"]
    t0 = time.time()

    # Bind workspace so tools write into user project
    ws_id = job.get("workspace_id") or ""
    if ws_id:
        try:
            from backend.files_router import set_active_workspace, USER_WORKSPACES_ROOT, effective_root
            import agent as agent_mod

            set_active_workspace(ws_id)
            os.environ["LUMORA_PROJECT_ROOT"] = str(USER_WORKSPACES_ROOT / ws_id)
            agent_mod.PROJECT_ROOT = effective_root()
        except Exception:
            pass

    files_before = set(_list_workspace_files(ws_id))

    # Reconstruct messages
    raw_msgs = job.get("messages") or []
    if not raw_msgs:
        user_content = job.get("message") or ""
        user_content += (
            "\n\n### Runtime constraints (serverless ticks)\n"
            "You are generating files into the active project workspace. "
            "Prefer write_file / create_directory. Keep files focused "
            "(index.html, styles.css, script.js, assets). "
            "After core pages exist, stop and summarize what you created."
        )
        messages = [HumanMessage(content=user_content)]
    else:
        messages = deserialize_messages(raw_msgs)

    config = {
        "configurable": {"thread_id": job.get("thread_id") or job_id},
        "recursion_limit": max(2, max_steps * 2),
    }

    job["status"] = "running"
    job["stage"] = _stage_for(job.get("progress", 0), "running")
    job["tick_count"] = int(job.get("tick_count") or 0) + 1
    save_job(job)

    result_messages = messages
    timed_out = False
    hit_limit = False
    error = ""

    try:
        deadline = t0 + time_budget_s
        step = 0
        if hasattr(agent, "stream"):
            for event in agent.stream(
                {"messages": messages},
                config=config,
                stream_mode="values",
            ):
                if isinstance(event, dict) and event.get("messages"):
                    result_messages = event["messages"]
                    step += 1
                if step >= max_steps * 2:
                    hit_limit = True
                    break
                if time.time() >= deadline:
                    timed_out = True
                    break
        else:
            out = agent.invoke({"messages": messages}, config=config)
            result_messages = out.get("messages") or messages
    except Exception as exc:
        name = type(exc).__name__
        detail = str(exc)
        if name == "GraphRecursionError" or "Recursion limit" in detail:
            hit_limit = True
            try:
                st = agent.get_state(config)
                if st and getattr(st, "values", None):
                    result_messages = st.values.get("messages") or result_messages
            except Exception:
                pass
        else:
            # Transient provider errors: small bounded retry inside this tick
            info = classify_provider_error(exc)
            attempts = int(job.get("provider_retries") or 0)
            if info["retryable"] and info["category"] in (
                "rate_limit", "provider_unavailable", "timeout"
            ) and attempts < 2:
                job["provider_retries"] = attempts + 1
                time.sleep(min(2.5 * (attempts + 1), 6.0))
                try:
                    out = agent.invoke({"messages": messages}, config=config)
                    result_messages = out.get("messages") or result_messages
                    # fall through to normal persist
                except Exception as exc2:
                    job = apply_pause(job, exc2, result_messages=result_messages)
                    job["files_created"] = sorted(_list_workspace_files(ws_id))
                    job["elapsed_ms"] = int(job.get("elapsed_ms") or 0) + int((time.time() - t0) * 1000)
                    save_job(job)
                    return job
            else:
                job = apply_pause(job, exc, result_messages=result_messages)
                job["files_created"] = sorted(_list_workspace_files(ws_id))
                job["elapsed_ms"] = int(job.get("elapsed_ms") or 0) + int((time.time() - t0) * 1000)
                save_job(job)
                return job

    # Persist checkpoint
    job["messages"] = serialize_messages(result_messages)
    files_after = set(_list_workspace_files(ws_id))
    new_files = sorted(files_after - files_before)
    all_files = sorted(files_after)
    job["files_created"] = all_files

    # Extract last AI text
    response_text = ""
    for msg in reversed(list(result_messages)):
        if getattr(msg, "type", None) == "ai" and getattr(msg, "content", None):
            response_text = msg.content
            break
    if response_text:
        job["response"] = response_text

    # Progress heuristic
    progress = int(job.get("progress") or 0)
    progress = min(95, progress + 8 + min(20, len(new_files) * 10))
    if all_files and any(f.endswith(".html") for f in all_files):
        progress = max(progress, 40)
    if all_files and any(f.endswith(".css") for f in all_files):
        progress = max(progress, 55)
    if all_files and any(f.endswith(".js") for f in all_files):
        progress = max(progress, 70)

    # Completion: agent produced final AI without pending tool_calls + has files
    last_ai = None
    for msg in reversed(list(result_messages)):
        if getattr(msg, "type", None) == "ai":
            last_ai = msg
            break
    pending_tools = bool(getattr(last_ai, "tool_calls", None)) if last_ai else False
    done_phrases = ("complete", "completed", "finished", "done", "ready to preview")
    text_done = any(p in (response_text or "").lower() for p in done_phrases)
    has_site = any(f.endswith(".html") for f in all_files)

    completed = False
    if has_site and text_done and not pending_tools:
        completed = True
    if has_site and not pending_tools and progress >= 85 and not timed_out and not hit_limit:
        # Enough structure and agent stopped tool use
        completed = True
    if job.get("tick_count", 0) >= 24 and has_site and not pending_tools:
        completed = True

    if completed:
        job["status"] = "completed"
        job["stage"] = "completed"
        job["progress"] = 100
        job["partial"] = False
    else:
        job["status"] = "running"
        job["progress"] = progress
        job["stage"] = _stage_for(progress, "running")
        job["partial"] = True
        if timed_out or hit_limit:
            job["reason"] = "tick_budget"

    job["elapsed_ms"] = int(job.get("elapsed_ms") or 0) + int((time.time() - t0) * 1000)
    save_job(job)
    return job
