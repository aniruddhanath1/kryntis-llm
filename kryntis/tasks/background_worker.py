"""Background Worker for async daemon jobs."""

import threading
import time
from typing import Callable

class BackgroundWorker:
    """Runs periodic background maintenance tasks."""
    def __init__(self, target_fn: Callable[[], None], interval_sec: float = 60.0) -> None:
        self.target_fn = target_fn
        self.interval_sec = interval_sec
        self.running = False
        self._thread = None

    def start(self) -> None:
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        while self.running:
            try:
                self.target_fn()
            except Exception:
                pass
            time.sleep(self.interval_sec)

    def stop(self) -> None:
        self.running = False
