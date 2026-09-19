"""
FastAPI application entry point with comprehensive OpenAPI / Swagger specification.

All routes are Spring Boot and enterprise-gateway compatible:
  - JSON request/response bodies
  - Standard HTTP status codes
  - SSE streaming for chat
  - Multipart file upload for ingestion
  - Voice TTS/STT and conversational endpoints
  - Interactive OpenAPI Swagger UI (/docs) and ReDoc (/redoc)

The frontend (React) and backend (Spring Boot) proxy directly to this service.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from kryntis.service.routers import chat, ingestion, knowledge, admin, voice
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

OPENAPI_TAGS = [
    {
        "name": "Chat",
        "description": "Conversational inference endpoints with 5B virtual context streaming, hybrid RAG, EQ empathy, and tool execution.",
    },
    {
        "name": "Voice",
        "description": "Speech-to-Text (STT), Text-to-Speech (TTS) audio synthesis, and end-to-end conversational voice interaction.",
    },
    {
        "name": "Ingestion",
        "description": "Universal chunked document, code, audio, and video ingestion pipeline (≤100MB docs, ≤10MB media).",
    },
    {
        "name": "Knowledge",
        "description": "Vector store and document database management, query semantic search, and provenance inspection.",
    },
    {
        "name": "Admin",
        "description": "System health checks, provider status, continual learning approval queues, and user-interactive model training.",
    },
    {
        "name": "MCP",
        "description": "Model Context Protocol JSON-RPC 2.0 endpoints for IDE and agent interoperability.",
    },
    {
        "name": "A2A",
        "description": "Google Agent-to-Agent federated discovery protocol and Agent Card specification.",
    },
    {
        "name": "Health",
        "description": "Service heartbeat and readiness probes.",
    },
]


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
        title="Kryntis AI — Sovereign Autonomous LLM API",
        description=(
            "### Sovereign Multi-Domain Autonomous LLM & AI Platform\n\n"
            "Kryntis AI provides a complete local intelligence ecosystem featuring:\n"
            "- **Tokenizer-Free Byte Direct Transformer Engine** (Vocab size 260)\n"
            "- **Virtual 5B Single-Session Context Streaming**\n"
            "- **Voice Audio Ingestion & Formant Wave Speech Synthesis**\n"
            "- **Multimodal Document, Audio, and Video Analysis** (≤10MB Media)\n"
            "- **Extensible AI Tool Registry** (Python REPL, SQL, Web Scraper, Calc)\n"
            "- **Hybrid RAG** (BM25 + Dense Vector RRF + Reranker)\n"
            "- **Continual Learning & User Feedback Fine-Tuning**\n"
            "- **Model Context Protocol (MCP)** & **Agent-to-Agent (A2A)** Interoperability\n"
        ),
        version="1.0.0",
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 1,
            "docExpansion": "list",
            "filter": True,
            "syntaxHighlight.theme": "monokai",
        },
        contact={
            "name": "Kryntis AI Engineering Team",
            "url": "https://github.com/kryntis-ai/kryntis-llm",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        lifespan=lifespan,
    )

    # ── Middleware (outermost first) ─────────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AuthMiddleware)

    # ── CORS (React frontend + Spring Boot gateway) ──────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.service.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Core API routers ─────────────────────────────────────────────────────
    app.include_router(chat.router,       prefix="/api/v1/chat",       tags=["Chat"])
    app.include_router(voice.router,      prefix="/api/v1/voice",      tags=["Voice"])
    app.include_router(ingestion.router,  prefix="/api/v1/ingestion",  tags=["Ingestion"])
    app.include_router(knowledge.router,  prefix="/api/v1/knowledge",  tags=["Knowledge"])
    app.include_router(admin.router,      prefix="/api/v1/admin",      tags=["Admin"])

    # ── MCP server (Model Context Protocol) ──────────────────────────────────
    if cfg.mcp.enabled:
        app.include_router(mcp_router.router, prefix="/mcp", tags=["MCP"])
        log.info("mcp_server_enabled", path="/mcp")

    # ── A2A protocol (Agent-to-Agent) ────────────────────────────────────────
    if cfg.a2a.enabled:
        app.include_router(a2a_router.router, prefix="", tags=["A2A"])
        log.info("a2a_server_enabled", agent_card="/.well-known/agent.json")

    @app.get("/health", tags=["Health"], summary="Service health probe")
    async def health() -> dict:
        """Health check endpoint confirming service status and operational readiness."""
        return {"status": "ok", "service": "kryntis-llm", "version": "1.0.0"}

    return app


app = build_app()
