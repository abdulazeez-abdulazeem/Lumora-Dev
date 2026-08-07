"""
Agent-to-agent messaging bus.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    msg_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    from_agent: str
    to_agent: str  # or "broadcast"
    topic: str = "general"
    body: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    read: bool = False


class MessageBus:
    def __init__(self, max_history: int = 500):
        self._messages: List[Message] = []
        self._lock = threading.Lock()
        self.max_history = max_history

    def send(
        self,
        from_agent: str,
        to_agent: str,
        body: str,
        topic: str = "general",
        payload: Optional[Dict] = None,
    ) -> Message:
        msg = Message(
            from_agent=from_agent,
            to_agent=to_agent,
            body=body,
            topic=topic,
            payload=payload or {},
        )
        with self._lock:
            self._messages.append(msg)
            if len(self._messages) > self.max_history:
                self._messages = self._messages[-self.max_history :]
        return msg

    def inbox(self, agent: str, unread_only: bool = False) -> List[Message]:
        with self._lock:
            msgs = [
                m for m in self._messages
                if m.to_agent in (agent, "broadcast") or m.from_agent == agent
            ]
            if unread_only:
                msgs = [m for m in msgs if not m.read and m.to_agent == agent]
            return list(msgs)

    def mark_read(self, msg_id: str) -> bool:
        with self._lock:
            for m in self._messages:
                if m.msg_id == msg_id:
                    m.read = True
                    return True
        return False

    def history(self, limit: int = 50) -> List[Message]:
        with self._lock:
            return list(self._messages[-limit:])

    def clear(self) -> None:
        with self._lock:
            self._messages.clear()
