"""
A2A (Agent-to-Agent) protocol server — Google's open multi-agent interoperability spec.

Allows other AI agents (LangGraph, Vertex AI agents, custom A2A clients)
to discover and invoke Kryntis as a peer agent.

Spec: https://google.github.io/A2A/

Mount point: /a2a  (configured in app.py)

Endpoints:
  GET  /.well-known/agent.json  — Agent Card (discovery; public, no auth)
  POST /a2a                     — Task submission and status polling

Task lifecycle:
  submitted → working → (input-required | completed | failed | canceled)

Supported input/output parts:
  TextPart    — plain text message
  DataPart    — structured JSON payload

Skills exposed:
  kryntis.chat           — conversational AI with RAG + memory
  kryntis.knowledge_search — knowledge base semantic search
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from cachetools import TTLCache
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)
router = APIRouter(tags=["A2A"])


# ── Agent Card (public discovery endpoint) ────────────────────────────────────

def _build_agent_card(base_url: str) -> dict:
    return {
        "name":        "Kryntis AI",
        "description": (
            "Enterprise-grade sovereign AI platform with zero external dependencies. "
            "Supports hybrid RAG retrieval, continual learning, semantic memory, "
            "and emotional intelligence (EQ) in 100% offline environments."
        ),
        "url":         base_url,
        "version":     "1.0.0",
        "protocolVersion": "1.0",
        "endpoints": {
            "tasks": f"{base_url}/a2a",
        },
        "capabilities": {
            "streaming":        True,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "authentication": {
            "schemes": ["bearer"],
            "description": "Pass the X-Kryntis-Key header value as the bearer token.",
        },
        "defaultInputModes":  ["text/plain", "application/json"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id":          "kryntis.chat",
                "name":        "Chat",
                "description": (
                    "Conversational AI with RAG retrieval, semantic memory, "
                    "internet research fallback, and EQ-aware responses."
                ),
                "tags":        ["chat", "rag", "memory", "research"],
                "examples":    [
                    "What documents have been uploaded about our Q3 roadmap?",
                    "Summarise the last five customer support tickets about billing.",
                ],
                "inputModes":  ["text/plain"],
                "outputModes": [text_plain := "text/plain"],
            },
            {
                "id":          "kryntis.knowledge_search",
                "name":        "Knowledge Search",
                "description": "Search the knowledge base using hybrid BM25 + dense vector retrieval.",
                "tags":        ["search", "rag", "knowledge"],
                "examples":    [
                    "Find all chunks about database migration in the knowledge base.",
                ],
                "inputModes":  ["application/json"],
                "outputModes": ["application/json"],
            },
        ],
    }


# ── Bounded in-memory task store (TTLCache to prevent memory exhaustion) ────────

_tasks: TTLCache[str, dict] = TTLCache(maxsize=10000, ttl=86400)


def _new_task(task_id: str, skill_id: str, parts: list[dict]) -> dict:
    return {
        "id":        task_id,
        "status":    {"state": "submitted", "timestamp": _iso_now()},
        "skill_id":  skill_id,
        "input":     parts,
        "artifacts": [],
        "history":   [],
    }


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ── Protocol Router ───────────────────────────────────────────────────────────

@router.get("/.well-known/agent.json")
async def get_agent_card(request: Request) -> JSONResponse:
    """A2A discovery endpoint — returns the Agent Card."""
    cfg = get_config().a2a
    base_url = cfg.public_base_url or str(request.base_url).rstrip("/")
    return JSONResponse(content=_build_agent_card(base_url))


@router.post("")
@router.post("/")
async def handle_a2a_task(request: Request) -> Response:
    """
    Main A2A task endpoint.

    Handles:
      - Task submission (skill invocation)
      - Task status query (poll by ID)
      - Task cancellation
    """
    try:
        body: dict = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body."}, status_code=400)

    action = body.get("action", "submit")

    if action == "submit":
        return await _handle_submit(body)
    elif action == "get":
        task_id = body.get("taskId", "")
        return _handle_get(task_id)
    elif action == "cancel":
        task_id = body.get("taskId", "")
        return _handle_cancel(task_id)
    else:
        return JSONResponse({"error": f"Unknown A2A action '{action}'."}, status_code=400)


# ── Action Handlers ───────────────────────────────────────────────────────────

async def _handle_submit(body: dict) -> Response:
    skill_id = body.get("skillId", "kryntis.chat")
    input_parts = body.get("input", [])
    stream = body.get("stream", False)

    task_id = str(uuid.uuid4())
    task = _new_task(task_id, skill_id, input_parts)
    _tasks[task_id] = task

    log.info("a2a_task_submitted", task_id=task_id, skill=skill_id, stream=stream)

    # Extract user text from input parts
    user_text = ""
    for part in input_parts:
        if part.get("type") == "text":
            user_text += part.get("text", "") + "\n"
        elif part.get("type") == "data":
            user_text += str(part.get("data", "")) + "\n"
    user_text = user_text.strip()

    if not user_text:
        task["status"] = {"state": "failed", "timestamp": _iso_now(), "error": "No input text provided."}
        return JSONResponse(task, status_code=400)

    task["status"] = {"state": "working", "timestamp": _iso_now()}

    if stream:
        return await _stream_task(task, user_text, skill_id)
    else:
        return await _run_task_sync(task, user_text, skill_id)


async def _run_task_sync(task: dict, user_text: str, skill_id: str) -> JSONResponse:
    from kryntis.orchestrator.agent_loop import AIOrchestrator, OrchestratorRequest

    try:
        orch = AIOrchestrator()
        req = OrchestratorRequest(
            session_id=task["id"],
            user_message=user_text,
            stream=False,
            enable_rag=(skill_id in ("kryntis.chat", "kryntis.knowledge_search")),
            enable_internet=False,
        )
        res = await orch.chat(req)

        task["status"] = {"state": "completed", "timestamp": _iso_now()}
        task["artifacts"] = [
            {
                "type": "text",
                "text": res.response,
                "metadata": {
                    "intent": res.intent,
                    "citations": res.citations,
                    "ragChunksUsed": res.rag_chunks_used,
                    "provider": res.provider,
                    "model": res.model,
                },
            }
        ]
        return JSONResponse(task)

    except Exception as e:
        log.error("a2a_task_failed", task_id=task["id"], error=str(e))
        task["status"] = {"state": "failed", "timestamp": _iso_now(), "error": str(e)}
        return JSONResponse(task, status_code=500)


async def _stream_task(task: dict, user_text: str, skill_id: str) -> StreamingResponse:
    import json
    from kryntis.orchestrator.agent_loop import AIOrchestrator, OrchestratorRequest

    orch = AIOrchestrator()
    req = OrchestratorRequest(
        session_id=task["id"],
        user_message=user_text,
        stream=True,
        enable_rag=(skill_id in ("kryntis.chat", "kryntis.knowledge_search")),
        enable_internet=False,
    )

    async def event_generator():
        full_text = ""
        try:
            async for token in orch.stream_chat(req):
                full_text += token
                event = {
                    "type": "token",
                    "taskId": task["id"],
                    "delta": token,
                }
                yield f"data: {json.dumps(event)}\n\n"

            task["status"] = {"state": "completed", "timestamp": _iso_now()}
            task["artifacts"] = [{"type": "text", "text": full_text}]
            done_event = {
                "type": "status",
                "taskId": task["id"],
                "status": task["status"],
            }
            yield f"data: {json.dumps(done_event)}\n\n"

        except Exception as e:
            task["status"] = {"state": "failed", "timestamp": _iso_now(), "error": str(e)}
            err_event = {"type": "error", "taskId": task["id"], "error": str(e)}
            yield f"data: {json.dumps(err_event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _handle_get(task_id: str) -> JSONResponse:
    task = _tasks.get(task_id)
    if not task:
        return JSONResponse({"error": f"Task '{task_id}' not found."}, status_code=404)
    return JSONResponse(task)


def _handle_cancel(task_id: str) -> JSONResponse:
    task = _tasks.get(task_id)
    if not task:
        return JSONResponse({"error": f"Task '{task_id}' not found."}, status_code=404)
    task["status"] = {"state": "canceled", "timestamp": _iso_now()}
    return JSONResponse(task)
