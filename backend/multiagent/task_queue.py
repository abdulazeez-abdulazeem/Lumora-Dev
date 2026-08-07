"""
Shared task queue with dependencies and status tracking.
"""

from __future__ import annotations

import threading
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str
    description: str = ""
    role: str = ""  # target agent role
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1 highest
    depends_on: List[str] = Field(default_factory=list)
    assigned_to: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = time.time()


class TaskQueue:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()

    def add(self, task: Task) -> Task:
        with self._lock:
            self._tasks[task.task_id] = task
            return task

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def update(self, task_id: str, **kwargs) -> Optional[Task]:
        with self._lock:
            t = self._tasks.get(task_id)
            if not t:
                return None
            for k, v in kwargs.items():
                if hasattr(t, k):
                    setattr(t, k, v)
            t.touch()
            return t

    def list(self, status: Optional[TaskStatus] = None, role: Optional[str] = None) -> List[Task]:
        items = list(self._tasks.values())
        if status:
            items = [t for t in items if t.status == status]
        if role:
            items = [t for t in items if t.role == role]
        return sorted(items, key=lambda t: (t.priority, t.created_at))

    def ready_tasks(self) -> List[Task]:
        """Tasks whose dependencies are all completed."""
        with self._lock:
            ready = []
            for t in self._tasks.values():
                if t.status not in (TaskStatus.PENDING, TaskStatus.ASSIGNED):
                    continue
                deps_ok = all(
                    self._tasks.get(d) and self._tasks[d].status == TaskStatus.COMPLETED
                    for d in t.depends_on
                )
                if deps_ok:
                    ready.append(t)
            return sorted(ready, key=lambda t: (t.priority, t.created_at))

    def conflicts(self) -> List[Dict[str, Any]]:
        """Detect two in-progress tasks on the same file/resource."""
        active = [t for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS]
        conflicts = []
        seen_files: Dict[str, str] = {}
        for t in active:
            f = (t.metadata or {}).get("file")
            if f and f in seen_files:
                conflicts.append({
                    "file": f,
                    "tasks": [seen_files[f], t.task_id],
                    "message": f"Concurrent edit on {f}",
                })
            elif f:
                seen_files[f] = t.task_id
        return conflicts

    def summary(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for t in self._tasks.values():
            counts[t.status.value] = counts.get(t.status.value, 0) + 1
        return {"total": len(self._tasks), "by_status": counts}
