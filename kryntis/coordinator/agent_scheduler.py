"""Agent Scheduler for scheduling background agent tasks."""

import time
from typing import List, Dict, Any, Callable

class AgentScheduler:
    """Manages scheduled tasks and cron-like jobs."""
    def __init__(self) -> None:
        self._jobs: List[Dict[str, Any]] = []

    def schedule(self, interval_sec: float, job: Callable[[], None], name: str = "job") -> None:
        self._jobs.append({
            "name": name,
            "interval_sec": interval_sec,
            "job": job,
            "last_run": 0.0
        })

    def run_pending(self) -> int:
        now = time.time()
        executed = 0
        for j in self._jobs:
            if now - j["last_run"] >= j["interval_sec"]:
                j["job"]()
                j["last_run"] = now
                executed += 1
        return executed
