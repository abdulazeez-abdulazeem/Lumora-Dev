"""
Lightweight process-wide event bus for subsystem signals.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    topic: str
    source: str = "system"
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class EventBus:
    def __init__(self, max_history: int = 1000):
        self._subs: Dict[str, List[Callable]] = defaultdict(list)
        self._history: List[Event] = []
        self._lock = threading.Lock()
        self.max_history = max_history

    def publish(self, topic: str, source: str = "system", payload: Optional[Dict] = None) -> Event:
        ev = Event(topic=topic, source=source, payload=payload or {})
        with self._lock:
            self._history.append(ev)
            if len(self._history) > self.max_history:
                self._history = self._history[-self.max_history :]
            handlers = list(self._subs.get(topic, [])) + list(self._subs.get("*", []))
        for h in handlers:
            try:
                h(ev)
            except Exception:
                pass
        return ev

    def subscribe(self, topic: str, handler: Callable) -> None:
        with self._lock:
            self._subs[topic].append(handler)

    def history(self, topic: Optional[str] = None, limit: int = 50) -> List[Event]:
        with self._lock:
            items = self._history
            if topic:
                items = [e for e in items if e.topic == topic]
            return list(items[-limit:])

    def clear(self) -> None:
        with self._lock:
            self._history.clear()


_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
