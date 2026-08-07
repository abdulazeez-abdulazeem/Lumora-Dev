"""
In-memory metrics store with simple aggregates.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional


class MetricsStore:
    def __init__(self):
        self._counters: Dict[str, float] = defaultdict(float)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        self._gauges: Dict[str, float] = {}
        self._lock = threading.Lock()
        self.started_at = time.time()

    def incr(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def timing(self, name: str, duration_ms: float) -> None:
        with self._lock:
            arr = self._timers[name]
            arr.append(duration_ms)
            if len(arr) > 500:
                self._timers[name] = arr[-500:]

    def gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            timers = {}
            for k, vals in self._timers.items():
                if not vals:
                    continue
                timers[k] = {
                    "count": len(vals),
                    "avg_ms": round(sum(vals) / len(vals), 2),
                    "p95_ms": round(sorted(vals)[int(len(vals) * 0.95) - 1] if len(vals) > 1 else vals[0], 2),
                    "last_ms": round(vals[-1], 2),
                }
            return {
                "uptime_s": round(time.time() - self.started_at, 1),
                "counters": dict(self._counters),
                "timers": timers,
                "gauges": dict(self._gauges),
            }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._timers.clear()
            self._gauges.clear()
