"""
FastAPI middleware stack.

Middleware executes in registration order (outermost first on request,
outermost last on response):

  1. RequestLoggingMiddleware  — structured request/response logging
  2. AuthMiddleware            — validates X-Kryntis-Key header on /api/* paths
  3. RateLimitMiddleware       — per-IP sliding-window rate limit

Guardrail checks (prompt injection, PII, etc.) are handled inside the
chat router dependency because they need the parsed request body.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

# Paths that do NOT require the internal auth key
_PUBLIC_PATHS = frozenset([
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/.well-known/agent.json",   # A2A agent card
])

# Paths that skip rate limiting (health probes, MCP handshake)
_NO_RATELIMIT_PATHS = frozenset(["/health", "/docs", "/redoc", "/openapi.json"])


# ── 1. Request logging ────────────────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status, and latency for every request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
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


# ── 2. Auth middleware ────────────────────────────────────────────────────────

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Validates the X-Kryntis-Key header on all /api/* and /mcp* paths.

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
        if not provided or provided != self._key:
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
    Per-IP sliding-window rate limiter.

    Limit is read from SecuritySettings.rate_limit_requests_per_minute.
    Exempt paths skip the check entirely.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        from kryntis.utils.config import get_config
        cfg = get_config().security
        self._max = cfg.rate_limit_requests_per_minute
        self._window = 60
        self._windows: dict[str, deque] = defaultdict(deque)

    def _is_allowed(self, ip: str) -> bool:
        now = time.monotonic()
        win = self._windows[ip]
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
