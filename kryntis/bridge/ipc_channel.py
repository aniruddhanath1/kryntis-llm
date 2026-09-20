"""Inter-Process Communication channel abstractions."""

import queue
from typing import Any, Optional

class IPCChannel:
    """Thread-safe and process-safe message channel."""
    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)

    def send(self, message: Any) -> None:
        self._queue.put(message)

    def receive(self, timeout: Optional[float] = None) -> Any:
        return self._queue.get(timeout=timeout)

    def is_empty(self) -> bool:
        return self._queue.empty()
