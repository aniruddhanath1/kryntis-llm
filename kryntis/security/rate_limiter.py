"""
Rate Limiter — SOLID multi-strategy rate limiting module.

Strategies:
1. Token Bucket Rate Limiter (with burst tolerance & continuous refill)
2. Sliding Window Log Rate Limiter
3. Multi-Tier Hierarchical Rate Limiter (Client IP + Session + Global)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass


class IRateLimiter(ABC):
    """Abstract Rate Limiter Interface (SOLID: Interface Segregation)."""

    @abstractmethod
    def is_allowed(self, client_key: str) -> bool:
        """Check if request for client_key is permitted under current rate limit."""
        ...

    @abstractmethod
    def reset(self, client_key: str | None = None) -> None:
        """Reset limits for a specific client_key or all clients."""
        ...


class TokenBucketRateLimiter(IRateLimiter):
    """
    Token Bucket Rate Limiter with burst capacity and smooth token refill.

    Args:
        capacity: Maximum burst capacity of tokens.
        refill_rate: Tokens added per second.
    """

    def __init__(self, capacity: int = 60, refill_rate: float = 1.0) -> None:
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._tokens: dict[str, float] = defaultdict(lambda: self.capacity)
        self._last_refill: dict[str, float] = defaultdict(time.monotonic)

    def is_allowed(self, client_key: str) -> bool:
        now = time.monotonic()
        last = self._last_refill[client_key]
        elapsed = now - last
        self._last_refill[client_key] = now

        # Refill tokens
        current = min(self.capacity, self._tokens[client_key] + elapsed * self.refill_rate)

        if current >= 1.0:
            self._tokens[client_key] = current - 1.0
            return True
        else:
            self._tokens[client_key] = current
            return False

    def reset(self, client_key: str | None = None) -> None:
        if client_key:
            self._tokens[client_key] = self.capacity
            self._last_refill[client_key] = time.monotonic()
        else:
            self._tokens.clear()
            self._last_refill.clear()


class SlidingWindowRateLimiter(IRateLimiter):
    """
    In-process sliding window log rate limiter.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, client_key: str) -> bool:
        now = time.monotonic()
        window = self._windows[client_key]

        # Remove expired timestamps
        cutoff = now - self._window
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= self._max:
            return False

        window.append(now)
        return True

    def reset(self, client_key: str | None = None) -> None:
        if client_key:
            self._windows[client_key].clear()
        else:
            self._windows.clear()


class MultiTierRateLimiter(IRateLimiter):
    """
    Combines multiple rate limiters hierarchically (e.g. per-second burst + per-minute ceiling).
    """

    def __init__(self, limiters: list[IRateLimiter]) -> None:
        self._limiters = limiters

    def is_allowed(self, client_key: str) -> bool:
        return all(limiter.is_allowed(client_key) for limiter in self._limiters)

    def reset(self, client_key: str | None = None) -> None:
        for limiter in self._limiters:
            limiter.reset(client_key)


# Backward-compatible alias
RateLimiter = SlidingWindowRateLimiter
