"""Rate limiter — simple in-process sliding window."""

from __future__ import annotations

import time
from collections import deque, defaultdict


class RateLimiter:
    """
    In-process sliding window rate limiter.

    Defaults: 60 requests per minute per session.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._windows: dict[str, deque] = defaultdict(deque)

    def is_allowed(self, session_id: str) -> bool:
        now = time.monotonic()
        window = self._windows[session_id]

        # Remove expired entries
        cutoff = now - self._window
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= self._max:
            return False

        window.append(now)
        return True
