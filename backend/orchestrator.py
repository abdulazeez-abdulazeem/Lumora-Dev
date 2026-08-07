"""
Lumora Dev – Task Orchestrator
Manages task lifecycle, activity logging, and agent coordination.
"""
import json
import time
import uuid
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
TASKS_FILE = ROOT / ".tasks.table"
ACTIVITY_LOG: list[dict] = []  # in-memory activity stream
MAX_ACTIVITY = 500


def _read_tasks() -> dict:
    if not TASKS_FILE.exists():
        return {"fields": [], "data": []}
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {"fields": [], "data": []}


def _write_tasks(data: dict):
    TASKS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_task(title: str) -> str:
    """Create a new task and return its ID."""
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    tasks = _read_tasks()
    tasks["data"].append({
        "id": task_id,
        "title": title,
        "status": "running",
        "progress": 0,
        "current_step": "",
        "steps": json.dumps([]),
        "files_modified": json.dumps([]),
        "commands_executed": json.dumps([]),
        "logs": json.dumps([]),
        "started_at": now,
        "ended_at": "",
    })
    _write_tasks(tasks)
    return task_id


def update_task(task_id: str, **kwargs):
    """Update task fields."""
    tasks = _read_tasks()
    for row in tasks["data"]:
        if row["id"] == task_id:
            for key, val in kwargs.items():
                if key in row:
                    row[key] = val
            break
    _write_tasks(tasks)


def complete_task(task_id: str, status: str = "completed"):
    """Mark task as done."""
    update_task(task_id, status=status, progress=100, ended_at=time.strftime("%Y-%m-%dT%H:%M:%S"))


def add_activity(agent: str, message: str, step: str = "", progress: int = 0):
    """Push an activity event. Agents: planner, coder, reviewer, terminal, git, coordinator."""
    event = {
        "agent": agent,
        "message": message,
        "step": step,
        "progress": progress,
        "time": time.strftime("%H:%M:%S"),
    }
    ACTIVITY_LOG.append(event)
    if len(ACTIVITY_LOG) > MAX_ACTIVITY:
        ACTIVITY_LOG.pop(0)


def get_activity(since: int = 0) -> list[dict]:
    """Return activity log from index `since`."""
    return ACTIVITY_LOG[since:]


def parse_agent_response(response_text: str, task_id: str):
    """Parse the LLM response for structured activity markers and update task tracking."""
    # Detect agent sections like [PLANNER] [CODER] [REVIEWER] [TERMINAL] [GIT]
    agent_pattern = re.compile(r'\[(PLANNER|CODER|REVIEWER|TERMINAL|GIT|COORDINATOR)\]\s*(.*?)(?=\n\[|$)', re.DOTALL)
    found_any = False

    for match in agent_pattern.finditer(response_text):
        agent = match.group(1).lower()
        msg = match.group(2).strip()[:200]
        add_activity(agent, msg, "", 0)
        found_any = True

    # If no structured sections, treat whole response as coordinator reply
    if not found_any and response_text.strip():
        add_activity("coordinator", response_text.strip()[:300], "", 0)

    # Try to extract progress percentage
    progress_match = re.search(r'Progress:\s*(\d+)%', response_text, re.IGNORECASE)
    if progress_match:
        progress = int(progress_match.group(1))
        update_task(task_id, progress=min(progress, 99))

    # Detect file operations from the response
    file_ops = []
    for pattern, label in [
        (r'(?:created|wrote|edited|modified)\s+(?:file\s+)?([^\s,;]+\.\w+)', 'modified'),
        (r'write_file\(["\']([^"\']+)', 'modified'),
        (r'list_files\(', 'listed'),
    ]:
        for f_match in re.finditer(pattern, response_text, re.IGNORECASE):
            if f_match.lastindex and f_match.group(1) not in file_ops:
                file_ops.append(f_match.group(1))

    if file_ops:
        tasks = _read_tasks()
        for row in tasks["data"]:
            if row["id"] == task_id:
                existing = json.loads(row.get("files_modified", "[]"))
                for f in file_ops:
                    if f not in existing:
                        existing.append(f)
                row["files_modified"] = json.dumps(existing)
                break
        _write_tasks(tasks)

    # Detect terminal commands
    cmd_pattern = re.findall(r'(?:Running|Executed|Run)\s+(?:command\s+)?`([^`]+)`', response_text)
    if cmd_pattern:
        tasks = _read_tasks()
        for row in tasks["data"]:
            if row["id"] == task_id:
                existing = json.loads(row.get("commands_executed", "[]"))
                for c in cmd_pattern:
                    if c not in existing:
                        existing.append(c)
                row["commands_executed"] = json.dumps(existing)
                break
        _write_tasks(tasks)


def get_task(task_id: str) -> Optional[dict]:
    """Return a single task by ID."""
    tasks = _read_tasks()
    for row in tasks["data"]:
        if row["id"] == task_id:
            return row
    return None


def get_recent_tasks(limit: int = 10) -> list[dict]:
    """Return most recent tasks."""
    tasks = _read_tasks()
    return sorted(tasks["data"], key=lambda t: t.get("started_at", ""), reverse=True)[:limit]


def get_memory_context() -> dict:
    """Return current working memory for the agent."""
    tasks = get_recent_tasks(5)
    return {
        "recent_tasks": [{"id": t["id"], "title": t["title"], "status": t["status"]} for t in tasks],
        "active_files": [],  # populated by frontend
        "current_branch": "unknown",
        "activity_count": len(ACTIVITY_LOG),
    }
