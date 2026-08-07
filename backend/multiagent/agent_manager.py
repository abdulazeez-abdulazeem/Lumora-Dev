"""
Agent Manager – registry of specialized agents and high-level multi-agent API.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional

from .task_queue import Task, TaskQueue, TaskStatus
from .messaging import MessageBus
from .shared_context import SharedContext
from .dispatcher import Dispatcher, ROLE_HANDLERS
from .coordinator import Coordinator, DEFAULT_PIPELINE

logger = logging.getLogger("lumora.multiagent")


class AgentRole(str, Enum):
    PLANNER = "planner"
    RESEARCH = "research"
    CODING = "coding"
    TESTING = "testing"
    DEBUGGING = "debugging"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    DEPLOYMENT_ADVISOR = "deployment_advisor"


AGENT_DESCRIPTIONS = {
    AgentRole.PLANNER: "Decomposes goals into subtasks and defines dependencies.",
    AgentRole.RESEARCH: "Searches Knowledge Engine and project docs before coding.",
    AgentRole.CODING: "Implements code changes using file/git tools guidance.",
    AgentRole.TESTING: "Plans and validates tests (pytest / terminal).",
    AgentRole.DEBUGGING: "Diagnoses failures and proposes fixes.",
    AgentRole.REVIEW: "Reviews quality, style, security, and completeness.",
    AgentRole.DOCUMENTATION: "Updates README, changelog, and API docs.",
    AgentRole.DEPLOYMENT_ADVISOR: "Advises on deployment readiness (no live deploy).",
}

# Tools each role is conceptually allowed to use (for documentation / policy)
ROLE_TOOLS = {
    "planner": ["search_knowledge", "search_project_docs", "remember"],
    "research": ["search_knowledge", "search_project_docs", "cite_sources", "browser_open"],
    "coding": ["read_file", "write_file", "search_codebase", "search_knowledge", "git_stage"],
    "testing": ["run_terminal", "read_file", "search_codebase"],
    "debugging": ["run_terminal", "read_file", "analyze_screenshot", "search_knowledge"],
    "review": ["read_file", "search_codebase", "search_knowledge", "validate_ui"],
    "documentation": ["read_file", "write_file", "search_project_docs", "summarize_document"],
    "deployment_advisor": ["search_knowledge", "search_project_docs", "run_terminal"],
}


class AgentManager:
    def __init__(self):
        self.queue = TaskQueue()
        self.bus = MessageBus()
        self.context = SharedContext()
        self.dispatcher = Dispatcher(self.queue, self.bus, self.context)
        self.coordinator = Coordinator(self.queue, self.bus, self.context, self.dispatcher)
        self._history: List[Dict[str, Any]] = []

    def list_agents(self) -> List[Dict[str, Any]]:
        agents = []
        for role in AgentRole:
            agents.append({
                "role": role.value,
                "description": AGENT_DESCRIPTIONS[role],
                "tools": ROLE_TOOLS.get(role.value, []),
                "active": any(
                    t.assigned_to == role.value and t.status == TaskStatus.IN_PROGRESS
                    for t in self.queue.list()
                ),
            })
        return agents

    def start(self, goal: str, auto_run: bool = True, max_steps: int = 20) -> Dict[str, Any]:
        plan = self.coordinator.start_goal(goal)
        result: Dict[str, Any] = {"plan": plan}
        if auto_run:
            result["run"] = self.coordinator.run_until_idle(max_steps=max_steps)
        self._history.append({"goal": goal, "plan": plan})
        return result

    def assign_task(
        self,
        title: str,
        role: str,
        description: str = "",
        depends_on: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            role=role,
            depends_on=depends_on or [],
            metadata=metadata or {},
        )
        self.queue.add(task)
        self.bus.send("manager", role, f"New task: {title}", topic="assign")
        return task

    def delegate(self, from_role: str, to_role: str, title: str, description: str = "") -> Task:
        self.bus.send(from_role, to_role, f"Delegating: {title}", topic="delegate")
        return self.assign_task(title=title, role=to_role, description=description)

    def request_review(self, subject: str) -> Task:
        return self.delegate("coding", "review", f"Review: {subject}", subject)

    def request_test(self, subject: str) -> Task:
        return self.delegate("coding", "testing", f"Test: {subject}", subject)

    def request_research(self, subject: str) -> Task:
        return self.delegate("planner", "research", f"Research: {subject}", subject)

    def share_context(self, author: str, text: str) -> None:
        self.context.add_note(author, text, kind="shared")
        self.bus.send(author, "broadcast", text, topic="context")

    def status(self) -> Dict[str, Any]:
        return {
            "version": "3.0.0-phase3b",
            "agents": self.list_agents(),
            "coordinator": self.coordinator.status(),
            "queue": self.queue.summary(),
            "messages": len(self.bus.history()),
            "context_goal": self.context._goal,
        }

    def tasks(self, status: Optional[str] = None) -> List[Dict]:
        st = TaskStatus(status) if status else None
        return [t.model_dump() for t in self.queue.list(status=st)]

    def messages(self, limit: int = 50) -> List[Dict]:
        return [m.model_dump() for m in self.bus.history(limit=limit)]

    def history(self, limit: int = 20) -> List[Dict]:
        return self._history[-limit:]

    def run_ready(self, max_tasks: int = 5) -> list:
        return self.dispatcher.dispatch_ready(max_tasks=max_tasks)


_mgr: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    global _mgr
    if _mgr is None:
        _mgr = AgentManager()
    return _mgr
