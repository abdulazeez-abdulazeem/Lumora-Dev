"""
Dispatcher – assign ready tasks to specialized agents and record results.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from .task_queue import Task, TaskQueue, TaskStatus
from .messaging import MessageBus
from .shared_context import SharedContext

logger = logging.getLogger("lumora.multiagent.dispatcher")


# Lightweight role handlers (deterministic stubs that integrate real subsystems)
def _handle_planner(task: Task, ctx: SharedContext, bus: MessageBus) -> str:
    ctx.add_note("planner", f"Planned: {task.title}")
    bus.send("planner", "research", f"Please research: {task.title}", topic="delegate")
    return f"Plan created for: {task.title}. Subtasks suggested: research → code → test → review."


def _handle_research(task: Task, ctx: SharedContext, bus: MessageBus) -> str:
    kb = ctx.knowledge_snippet(task.title or task.description or "project")
    snippet = kb[:500] if kb else "No knowledge hits; using general practices."
    ctx.add_note("research", f"Research for '{task.title}': {snippet[:200]}")
    bus.send("research", "coding", f"Research complete for: {task.title}", topic="handoff")
    return f"Research summary:\n{snippet}"


def _handle_coding(task: Task, ctx: SharedContext, bus: MessageBus) -> str:
    ctx.add_note("coding", f"Coding task: {task.title}")
    # surface knowledge context for coding
    kb = ctx.knowledge_snippet(task.description or task.title or "")
    bus.send("coding", "testing", f"Code ready for test: {task.title}", topic="handoff")
    return f"Coding guidance prepared for '{task.title}'. Knowledge context length={len(kb)}."


def _handle_testing(task: Task, ctx: SharedContext, bus: MessageBus) -> str:
    ctx.add_note("testing", f"Test plan for: {task.title}")
    bus.send("testing", "review", f"Tests planned for: {task.title}", topic="handoff")
    return f"Test plan: unit tests + integration checks for '{task.title}'."


def _handle_debugging(task: Task, ctx: SharedContext, bus: MessageBus) -> str:
    ctx.add_note("debugging", f"Debug: {task.title}")
    return f"Debug analysis for '{task.title}': check logs, reproduce, isolate, fix, retest."


def _handle_review(task: Task, ctx: SharedContext, bus: MessageBus) -> str:
    ctx.add_note("review", f"Review: {task.title}")
    bus.send("review", "documentation", f"Review done: {task.title}", topic="handoff")
    return f"Review checklist for '{task.title}': correctness, style, tests, security, docs."


def _handle_documentation(task: Task, ctx: SharedContext, bus: MessageBus) -> str:
    ctx.add_note("documentation", f"Docs for: {task.title}")
    return f"Documentation outline for '{task.title}': README section, API notes, changelog entry."


def _handle_deployment_advisor(task: Task, ctx: SharedContext, bus: MessageBus) -> str:
    ctx.add_note("deployment_advisor", f"Deploy advice: {task.title}")
    return (
        f"Deployment advice for '{task.title}' (planning only):\n"
        "- Verify tests green\n- Review env config\n- Staged rollout plan\n- Rollback checklist"
    )


ROLE_HANDLERS: Dict[str, Callable] = {
    "planner": _handle_planner,
    "research": _handle_research,
    "coding": _handle_coding,
    "testing": _handle_testing,
    "debugging": _handle_debugging,
    "review": _handle_review,
    "documentation": _handle_documentation,
    "deployment_advisor": _handle_deployment_advisor,
}


class Dispatcher:
    def __init__(self, queue: TaskQueue, bus: MessageBus, context: SharedContext):
        self.queue = queue
        self.bus = bus
        self.context = context

    def dispatch_one(self, task: Optional[Task] = None) -> Dict[str, Any]:
        if task is None:
            ready = self.queue.ready_tasks()
            if not ready:
                return {"dispatched": False, "reason": "no ready tasks"}
            task = ready[0]

        role = (task.role or "coding").lower()
        handler = ROLE_HANDLERS.get(role)
        if not handler:
            self.queue.update(task.task_id, status=TaskStatus.FAILED, error=f"Unknown role: {role}")
            return {"dispatched": False, "task_id": task.task_id, "error": f"Unknown role: {role}"}

        self.queue.update(task.task_id, status=TaskStatus.IN_PROGRESS, assigned_to=role)
        self.bus.send("dispatcher", role, f"Assigned task {task.task_id}: {task.title}", topic="assign")
        try:
            result = handler(task, self.context, self.bus)
            self.queue.update(task.task_id, status=TaskStatus.COMPLETED, result=result)
            self.context.add_execution_event({
                "task_id": task.task_id,
                "role": role,
                "title": task.title,
                "result_preview": (result or "")[:200],
            })
            return {"dispatched": True, "task_id": task.task_id, "role": role, "result": result}
        except Exception as e:
            logger.exception("dispatch failed")
            self.queue.update(task.task_id, status=TaskStatus.FAILED, error=str(e))
            return {"dispatched": False, "task_id": task.task_id, "error": str(e)}

    def dispatch_ready(self, max_tasks: int = 5) -> list:
        results = []
        for _ in range(max_tasks):
            r = self.dispatch_one()
            if not r.get("dispatched"):
                break
            results.append(r)
        return results
