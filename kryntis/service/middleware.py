"""
Service middleware: request logging, API key auth with constant-time verification, and rate limiting.
"""

from __future__ import annotations

import hmac
import time
import uuid
from collections import defaultdict, deque
from typing import Callable

from cachetools import TTLCache
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

# Paths that bypass auth entirely
_PUBLIC_PATHS = frozenset([
    "/health",
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/.well-known/agent.json",   # A2A agent card (public discovery)
])

# Paths exempt from rate limiting
_NO_RATELIMIT_PATHS = frozenset([
    "/health",
    "/api/v1/health",
    "/.well-known/agent.json",
])


# ── 1. Request logging middleware ──────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs incoming requests with timing, method, path, and response status."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.monotonic()

        response = await call_next(request)

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        log.info(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=elapsed_ms,
            client=request.client.host if request.client else "unknown",
        )
        response.headers["X-Request-Id"] = request_id
        return response


# ── 2. Auth middleware ─────────────────────────────────────────────────────────

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Validates the X-Kryntis-Key header on all /api/*, /mcp*, and /a2a* paths using constant-time comparison.

    Public paths (health, docs, A2A agent card) bypass auth.
    The key value is loaded from SecuritySettings.internal_key at startup.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        from kryntis.utils.config import get_config
        cfg = get_config()
        self._key = cfg.security.internal_key
        self._header = cfg.service.internal_key_header

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip auth for public paths
        if path in _PUBLIC_PATHS or not (path.startswith("/api/") or path.startswith("/mcp") or path.startswith("/a2a")):
            return await call_next(request)

        provided = request.headers.get(self._header, "")
        if not provided or not hmac.compare_digest(provided.strip(), self._key.strip()):
            log.warning(
                "auth_failed",
                path=path,
                client=request.client.host if request.client else "unknown",
            )
            return JSONResponse(
                {"detail": "Unauthorized — missing or invalid API key."},
                status_code=401,
            )

        return await call_next(request)


# ── 3. Rate limit middleware ──────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP sliding-window rate limiter with bounded memory footprint.

    Limit is read from SecuritySettings.rate_limit_requests_per_minute.
    Exempt paths skip the check entirely.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        from kryntis.utils.config import get_config
        cfg = get_config().security
        self._max = cfg.rate_limit_requests_per_minute
        self._window = 60
        # Bound IP tracking windows to 10,000 distinct entries with 120s TTL
        self._windows: TTLCache[str, deque] = TTLCache(maxsize=10000, ttl=120)

    def _is_allowed(self, ip: str) -> bool:
        now = time.monotonic()
        win = self._windows.get(ip)
        if win is None:
            win = deque()
            self._windows[ip] = win

        cutoff = now - self._window
        while win and win[0] < cutoff:
            win.popleft()

        if len(win) >= self._max:
            return False

        win.append(now)
        return True

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in _NO_RATELIMIT_PATHS:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        if not self._is_allowed(ip):
            log.warning("rate_limit_exceeded", ip=ip, path=path)
            return JSONResponse(
                {"detail": "Too many requests — rate limit exceeded."},
                status_code=429,
                headers={"Retry-After": str(self._window)},
            )

        return await call_next(request)
