"""
Coordinator – break a goal into role-ordered pipeline and drive the queue.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .task_queue import Task, TaskQueue, TaskStatus
from .dispatcher import Dispatcher
from .messaging import MessageBus
from .shared_context import SharedContext

logger = logging.getLogger("lumora.multiagent.coordinator")

# Default software engineering pipeline
DEFAULT_PIPELINE = [
    ("planner", "Plan the work"),
    ("research", "Research relevant docs and APIs"),
    ("coding", "Implement the change"),
    ("testing", "Design and run tests"),
    ("debugging", "Debug failures if any"),
    ("review", "Review the change"),
    ("documentation", "Update documentation"),
]


class Coordinator:
    def __init__(
        self,
        queue: TaskQueue,
        bus: MessageBus,
        context: SharedContext,
        dispatcher: Dispatcher,
    ):
        self.queue = queue
        self.bus = bus
        self.context = context
        self.dispatcher = dispatcher
        self._run_id: Optional[str] = None

    def start_goal(
        self,
        goal: str,
        pipeline: Optional[List[tuple]] = None,
        skip_roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create dependent tasks for a goal and optionally run them."""
        self.context.set_goal(goal)
        self.bus.send("coordinator", "broadcast", f"Starting goal: {goal}", topic="goal")
        pipeline = pipeline or DEFAULT_PIPELINE
        skip = set(skip_roles or [])
        prev_id = None
        created: List[str] = []
        for role, label in pipeline:
            if role in skip:
                continue
            task = Task(
                title=f"{label}: {goal}",
                description=goal,
                role=role,
                depends_on=[prev_id] if prev_id else [],
                priority=3,
            )
            self.queue.add(task)
            created.append(task.task_id)
            prev_id = task.task_id

        self._run_id = created[0] if created else None
        return {
            "goal": goal,
            "task_ids": created,
            "count": len(created),
            "run_id": self._run_id,
        }

    def run_until_idle(self, max_steps: int = 20) -> Dict[str, Any]:
        steps = []
        for _ in range(max_steps):
            conflicts = self.queue.conflicts()
            if conflicts:
                self.bus.send("coordinator", "broadcast", f"Conflict detected: {conflicts}", topic="conflict")
            ready = self.queue.ready_tasks()
            if not ready:
                break
            result = self.dispatcher.dispatch_one(ready[0])
            steps.append(result)
            if not result.get("dispatched"):
                break
        return {
            "steps": steps,
            "queue": self.queue.summary(),
            "context": self.context.snapshot(),
        }

    def status(self) -> Dict[str, Any]:
        return {
            "run_id": self._run_id,
            "goal": self.context._goal,
            "queue": self.queue.summary(),
            "conflicts": self.queue.conflicts(),
            "agents_active": list({t.assigned_to for t in self.queue.list() if t.assigned_to}),
        }
