"""
Chat router — non-streaming and SSE streaming endpoints.

Endpoints:
  POST /api/v1/chat/message        → non-streaming JSON
  POST /api/v1/chat/stream         → SSE streaming
  GET  /api/v1/chat/session/{id}   → session memory summary
  DELETE /api/v1/chat/session/{id} → clear session memory
"""

from __future__ import annotations

from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from kryntis.orchestrator.agent_loop import AIOrchestrator, OrchestratorRequest
from kryntis.security.rate_limiter import RateLimiter
from kryntis.service.dependencies import get_orchestrator

router = APIRouter()
_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, max_length=50000)
    enable_rag: bool = True
    enable_internet: bool = True
    enable_memory: bool = True
    source_filter: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    intent: str
    citations: list[dict]
    rag_chunks_used: int
    internet_searched: bool
    provider: str
    model: str


@router.post("/message", response_model=ChatResponse)
async def chat_message(
    req: ChatRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    """Non-streaming chat endpoint."""
    if not _rate_limiter.is_allowed(req.session_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    orch_req = OrchestratorRequest(
        session_id=req.session_id,
        user_message=req.message,
        stream=False,
        enable_rag=req.enable_rag,
        enable_internet=req.enable_internet,
        enable_memory=req.enable_memory,
        source_filter=req.source_filter,
    )
    result = await orchestrator.chat(orch_req)
    return ChatResponse(
        session_id=result.session_id,
        response=result.response,
        intent=result.intent,
        citations=result.citations,
        rag_chunks_used=result.rag_chunks_used,
        internet_searched=result.internet_searched,
        provider=result.provider,
        model=result.model,
    )


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
) -> StreamingResponse:
    """Server-Sent Events streaming chat endpoint."""
    if not _rate_limiter.is_allowed(req.session_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    orch_req = OrchestratorRequest(
        session_id=req.session_id,
        user_message=req.message,
        stream=True,
        enable_rag=req.enable_rag,
        enable_internet=req.enable_internet,
        enable_memory=req.enable_memory,
    )

    async def event_generator() -> AsyncIterator[str]:
        async for token in orchestrator.stream_chat(orch_req):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
) -> dict:
    """Return the session's conversation memory summary."""
    return orchestrator.get_session_memory(session_id)


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    orchestrator: AIOrchestrator = Depends(get_orchestrator),
) -> dict:
    """Clear a session's conversation memory."""
    orchestrator.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}
