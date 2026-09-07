"""
FastAPI application entry point.

All routes are Spring Boot-compatible:
  - JSON request/response bodies
  - Standard HTTP status codes
  - SSE streaming for chat
  - Multipart file upload for ingestion

The frontend (React) and backend (Spring Boot) will proxy to this service.
"""

from __future__ import annotations

import asyncio

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kryntis.service.routers import chat, ingestion, knowledge, admin
from kryntis.service.routers import mcp as mcp_router
from kryntis.service.routers import a2a as a2a_router
from kryntis.service.dependencies import init_services, shutdown_services
from kryntis.service.middleware import (
    AuthMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
)
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """App lifecycle: startup → serve → shutdown."""
    log.info("kryntis_startup")
    await init_services()
    yield
    log.info("kryntis_shutdown")
    await shutdown_services()


def build_app() -> FastAPI:
    cfg = get_config()

    app = FastAPI(
        title="Kryntis AI",
        description=(
            "Self-hosted LLM platform with RAG, semantic memory, internet research, "
            "continual learning, MCP server, and A2A agent protocol."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware (outermost first) ───────────────────────────────────────
    # Order matters: logging wraps everything, then rate limit, then auth.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)

    # ── CORS (React frontend + Spring Boot gateway) ───────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.service.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Core API routers ──────────────────────────────────────────────────
    app.include_router(chat.router,       prefix="/api/v1/chat",       tags=["Chat"])
    app.include_router(ingestion.router,  prefix="/api/v1/ingestion",  tags=["Ingestion"])
    app.include_router(knowledge.router,  prefix="/api/v1/knowledge",  tags=["Knowledge"])
    app.include_router(admin.router,      prefix="/api/v1/admin",      tags=["Admin"])

    # ── MCP server (Model Context Protocol) ──────────────────────────────
    if cfg.mcp.enabled:
        app.include_router(mcp_router.router, prefix="/mcp", tags=["MCP"])
        log.info("mcp_server_enabled", path="/mcp")

    # ── A2A protocol (Agent-to-Agent) ─────────────────────────────────────
    if cfg.a2a.enabled:
        app.include_router(a2a_router.router, prefix="", tags=["A2A"])
        log.info("a2a_server_enabled", agent_card="/.well-known/agent.json")

    @app.get("/health", tags=["Health"])
    async def health() -> dict:
        return {"status": "ok", "service": "kryntis-llm"}

    return app


app = build_app()
