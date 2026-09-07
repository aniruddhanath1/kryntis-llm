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

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)
router = APIRouter(tags=["A2A"])

# ── Agent Card (returned at /.well-known/agent.json) ─────────────────────────

def _build_agent_card() -> dict:
    cfg = get_config()
    host = cfg.a2a.public_base_url.rstrip("/")
    return {
        "name":         "Kryntis AI",
        "description":  (
            "Self-hosted AI assistant with RAG over a private knowledge base, "
            "hybrid BM25 + dense retrieval, three-tier memory, internet research, "
            "emotional intelligence, and continual learning."
        ),
        "url":          f"{host}/a2a",
        "version":      "1.0.0",
        "provider": {
            "organization": "Kryntis",
            "url":          host,
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
                "outputModes": ["text/plain"],
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


# ── In-memory task store (replace with Redis/DB for production) ───────────────

_tasks: dict[str, dict] = {}


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


def _text_part(text: str) -> dict:
    return {"type": "TextPart", "text": text}


def _data_part(data: Any) -> dict:
    return {"type": "DataPart", "data": data}


# ── Task execution ────────────────────────────────────────────────────────────

async def _execute_task(task: dict) -> None:
    """Run the requested skill and update task state."""
    task_id  = task["id"]
    skill_id = task.get("skill_id", "kryntis.chat")

    task["status"] = {"state": "working", "timestamp": _iso_now()}

    try:
        parts = task.get("input", [])
        # Extract text from the first TextPart
        text = next(
            (p["text"] for p in parts if p.get("type") == "TextPart"),
            "",
        )
        data = next(
            (p.get("data", {}) for p in parts if p.get("type") == "DataPart"),
            {},
        )

        if skill_id == "kryntis.chat":
            from kryntis.service.dependencies import get_orchestrator
            session_id = data.get("session_id") or str(uuid.uuid4())
            orch   = get_orchestrator()
            result = await orch.chat(message=text, session_id=session_id)
            response_text = result.get("response", "")
            task["artifacts"] = [{"parts": [_text_part(response_text)]}]

        elif skill_id == "kryntis.knowledge_search":
            query = text or data.get("query", "")
            top_k = int(data.get("top_k", 5))
            from kryntis.service.dependencies import get_doc_store
            results = await get_doc_store().search(query=query, top_k=top_k)
            task["artifacts"] = [{"parts": [_data_part(results)]}]

        else:
            task["artifacts"] = [{"parts": [_text_part(f"Unknown skill: {skill_id}")]}]

        task["status"] = {"state": "completed", "timestamp": _iso_now()}
        log.info("a2a_task_completed", task_id=task_id, skill=skill_id)

    except Exception as exc:
        log.exception("a2a_task_failed", task_id=task_id)
        task["status"] = {
            "state":     "failed",
            "timestamp": _iso_now(),
            "message":   {"role": "agent", "parts": [_text_part(f"Error: {exc}")]},
        }


# ── HTTP endpoints ────────────────────────────────────────────────────────────

@router.get("/.well-known/agent.json", include_in_schema=False)
async def agent_card() -> JSONResponse:
    """Public discovery endpoint — no auth required."""
    return JSONResponse(_build_agent_card())


@router.post("")
async def a2a_task(request: Request) -> JSONResponse | StreamingResponse:
    """
    A2A task endpoint.

    Accepts tasks/send and tasks/get JSON-RPC style requests,
    or the simplified flat body format.
    """
    try:
        body: dict = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    method = body.get("method", "tasks/send")

    # ── tasks/get ─────────────────────────────────────────────────────────
    if method == "tasks/get":
        task_id = body.get("params", {}).get("id") or body.get("id", "")
        task    = _tasks.get(task_id)
        if not task:
            return JSONResponse({"error": f"Task not found: {task_id}"}, status_code=404)
        return JSONResponse(task)

    # ── tasks/cancel ──────────────────────────────────────────────────────
    if method == "tasks/cancel":
        task_id = body.get("params", {}).get("id") or body.get("id", "")
        task    = _tasks.get(task_id)
        if task:
            task["status"] = {"state": "canceled", "timestamp": _iso_now()}
        return JSONResponse({"canceled": True})

    # ── tasks/send (default) ──────────────────────────────────────────────
    params   = body.get("params", body)  # accept both wrapped and flat bodies
    task_id  = params.get("id") or str(uuid.uuid4())
    skill_id = params.get("skill_id", "kryntis.chat")

    # Normalise input into a list of parts
    raw_input = params.get("message", {})
    if isinstance(raw_input, str):
        parts = [_text_part(raw_input)]
    elif isinstance(raw_input, dict):
        parts = raw_input.get("parts", [_text_part(str(raw_input))])
    else:
        parts = []

    task = _new_task(task_id, skill_id, parts)
    _tasks[task_id] = task

    streaming = params.get("stream", False)

    if streaming:
        # SSE streaming response
        async def event_stream():
            import json
            # Notify submitted
            yield f"data: {json.dumps({'id': task_id, 'status': task['status']})}\n\n"
            await _execute_task(task)
            yield f"data: {json.dumps(task)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Non-streaming: execute synchronously and return completed task
    await _execute_task(task)
    return JSONResponse(task)
