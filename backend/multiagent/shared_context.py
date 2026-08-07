"""
Shared project context visible to all specialized agents.
Pulls from Memory, Knowledge Engine, Planner, Vision, Execution history.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("lumora.multiagent.context")


class SharedContext:
    def __init__(self):
        self._notes: List[Dict[str, Any]] = []
        self._vision_findings: List[Dict[str, Any]] = []
        self._execution_log: List[Dict[str, Any]] = []
        self._goal: Optional[str] = None
        self._extra: Dict[str, Any] = {}

    def set_goal(self, goal: str) -> None:
        self._goal = goal
        self.add_note("system", f"Goal set: {goal}")

    def add_note(self, author: str, text: str, kind: str = "note") -> None:
        self._notes.append({
            "author": author,
            "text": text,
            "kind": kind,
            "ts": time.time(),
        })
        # also try persistent memory
        try:
            from backend.memory import get_memory  # type: ignore
            mem = get_memory()
            if hasattr(mem, "remember"):
                mem.remember(f"[{author}] {text}", kind=kind)
        except Exception:
            pass

    def add_vision_finding(self, finding: Dict[str, Any]) -> None:
        self._vision_findings.append({**finding, "ts": time.time()})

    def add_execution_event(self, event: Dict[str, Any]) -> None:
        self._execution_log.append({**event, "ts": time.time()})

    def knowledge_snippet(self, query: str, top_k: int = 4) -> str:
        try:
            from backend.knowledge.knowledge_manager import get_knowledge_manager
            res = get_knowledge_manager().search(query, top_k=top_k)
            return res.get("context_block") or ""
        except Exception as e:
            logger.debug("knowledge snippet failed: %s", e)
            return ""

    def snapshot(self) -> Dict[str, Any]:
        return {
            "goal": self._goal,
            "notes": self._notes[-30:],
            "vision_findings": self._vision_findings[-10:],
            "execution_log": self._execution_log[-20:],
            "extra": dict(self._extra),
        }

    def context_block_for_agent(self, role: str, query: Optional[str] = None) -> str:
        parts = [f"# Shared context for {role}"]
        if self._goal:
            parts.append(f"## Goal\n{self._goal}")
        if query:
            kb = self.knowledge_snippet(query)
            if kb:
                parts.append(kb)
        if self._notes:
            parts.append("## Recent notes")
            for n in self._notes[-8:]:
                parts.append(f"- [{n['author']}] {n['text']}")
        if self._vision_findings:
            parts.append("## Vision findings")
            for v in self._vision_findings[-5:]:
                parts.append(f"- {v}")
        return "\n".join(parts)
