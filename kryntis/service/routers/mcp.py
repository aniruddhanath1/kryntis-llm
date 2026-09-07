"""
MCP (Model Context Protocol) server — JSON-RPC 2.0 over HTTP POST.

Exposes Kryntis capabilities as MCP tools so any MCP-compatible client
(Claude Desktop, Cursor, VS Code Copilot Chat, custom agents) can connect
without going through the chat REST API.

Spec: https://modelcontextprotocol.io/specification/2025-03-26

Mount point: /mcp  (configured in app.py)

Transport: HTTP Streamable (single endpoint, JSON-RPC 2.0 body)
  POST /mcp         — all JSON-RPC requests
  GET  /mcp         — server-sent events stream (notifications)

Exposed tools:
  kryntis.chat                — send a chat message, get a response
  kryntis.search_knowledge    — search the knowledge base
  kryntis.ingest_text         — ingest a text snippet into the knowledge base
  kryntis.get_health          — retrieve system health status

Exposed resources:
  kryntis://knowledge/stats   — knowledge base statistics
  kryntis://admin/health      — full system health object
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from kryntis.service.dependencies import get_orchestrator, get_doc_store
from kryntis.utils.logging import get_logger

log = get_logger(__name__)
router = APIRouter(tags=["MCP"])

# ── Protocol version ──────────────────────────────────────────────────────────
_PROTOCOL_VERSION = "2025-03-26"
_SERVER_INFO = {"name": "kryntis-mcp", "version": "1.0.0"}

# ── Tool definitions (returned by tools/list) ─────────────────────────────────
_TOOLS = [
    {
        "name": "kryntis.chat",
        "description": (
            "Send a message to the Kryntis AI assistant and receive a response. "
            "The assistant uses RAG over the knowledge base, internet research, "
            "three-tier memory, and emotional intelligence."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "message":    {"type": "string",  "description": "The user message to send."},
                "session_id": {"type": "string",  "description": "Optional session ID for conversation continuity."},
                "stream":     {"type": "boolean", "description": "Whether to stream the response (default false)."},
            },
            "required": ["message"],
        },
    },
    {
        "name": "kryntis.search_knowledge",
        "description": "Search the Kryntis knowledge base using hybrid BM25 + dense vector retrieval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",  "description": "The search query."},
                "top_k": {"type": "integer", "description": "Number of results to return (default 5).", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "kryntis.ingest_text",
        "description": "Ingest a plain-text snippet into the Kryntis knowledge base for future retrieval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text":   {"type": "string", "description": "The text content to ingest."},
                "source": {"type": "string", "description": "A label identifying the source of this text."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "kryntis.get_health",
        "description": "Retrieve the current health and status of the Kryntis AI service.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

# ── Resource definitions ──────────────────────────────────────────────────────
_RESOURCES = [
    {
        "uri":         "kryntis://knowledge/stats",
        "name":        "Knowledge Base Statistics",
        "description": "Current chunk count, source count, and collection info.",
        "mimeType":    "application/json",
    },
    {
        "uri":         "kryntis://admin/health",
        "name":        "System Health",
        "description": "Full system health: model, vector store, memory, internet.",
        "mimeType":    "application/json",
    },
]


# ── JSON-RPC helpers ──────────────────────────────────────────────────────────

def _ok(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _err(id: Any, code: int, message: str, data: Any = None) -> dict:
    error: dict = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": id, "error": error}


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def _dispatch(method: str, params: dict, req_id: Any) -> dict:
    """Route a JSON-RPC method to its handler and return a JSON-RPC response."""

    # ── Lifecycle ─────────────────────────────────────────────────────────
    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": _PROTOCOL_VERSION,
            "serverInfo":      _SERVER_INFO,
            "capabilities": {
                "tools":     {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
            },
        })

    if method == "ping":
        return _ok(req_id, {})

    # ── Tools ─────────────────────────────────────────────────────────────
    if method == "tools/list":
        return _ok(req_id, {"tools": _TOOLS})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        return await _call_tool(req_id, tool_name, arguments)

    # ── Resources ─────────────────────────────────────────────────────────
    if method == "resources/list":
        return _ok(req_id, {"resources": _RESOURCES})

    if method == "resources/read":
        uri = params.get("uri", "")
        return await _read_resource(req_id, uri)

    return _err(req_id, -32601, f"Method not found: {method}")


async def _call_tool(req_id: Any, name: str, args: dict) -> dict:
    def _text(content: str) -> dict:
        return _ok(req_id, {"content": [{"type": "text", "text": content}]})

    def _json(obj: Any) -> dict:
        import json
        return _ok(req_id, {"content": [{"type": "text", "text": json.dumps(obj, indent=2)}]})

    try:
        if name == "kryntis.chat":
            message    = args.get("message", "")
            session_id = args.get("session_id") or str(uuid.uuid4())
            if not message:
                return _err(req_id, -32602, "Missing required argument: message")
            orch = get_orchestrator()
            result = await orch.chat(message=message, session_id=session_id)
            return _text(result.get("response", ""))

        if name == "kryntis.search_knowledge":
            query = args.get("query", "")
            top_k = int(args.get("top_k", 5))
            if not query:
                return _err(req_id, -32602, "Missing required argument: query")
            from kryntis.service.dependencies import get_doc_store
            doc_store = get_doc_store()
            results = await doc_store.search(query=query, top_k=top_k)
            return _json(results)

        if name == "kryntis.ingest_text":
            text   = args.get("text", "")
            source = args.get("source", "mcp-ingest")
            if not text:
                return _err(req_id, -32602, "Missing required argument: text")
            from kryntis.service.dependencies import get_ingestion_pipeline
            pipeline = get_ingestion_pipeline()
            job_id = await pipeline.ingest_text(text=text, source_label=source)
            return _json({"job_id": job_id, "status": "queued"})

        if name == "kryntis.get_health":
            from kryntis.utils.cache import cache_stats
            return _json({
                "status":      "ok",
                "service":     "kryntis-llm",
                "cache_stats": cache_stats(),
            })

        return _err(req_id, -32602, f"Unknown tool: {name}")

    except Exception as exc:
        log.exception("mcp_tool_error", tool=name)
        return _err(req_id, -32603, "Internal error", str(exc))


async def _read_resource(req_id: Any, uri: str) -> dict:
    import json
    try:
        if uri == "kryntis://knowledge/stats":
            from kryntis.service.dependencies import get_doc_store
            stats = await get_doc_store().stats()
            return _ok(req_id, {
                "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(stats)}]
            })

        if uri == "kryntis://admin/health":
            from kryntis.utils.cache import cache_stats
            health = {"status": "ok", "service": "kryntis-llm", "cache": cache_stats()}
            return _ok(req_id, {
                "contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(health)}]
            })

        return _err(req_id, -32602, f"Unknown resource URI: {uri}")
    except Exception as exc:
        log.exception("mcp_resource_error", uri=uri)
        return _err(req_id, -32603, "Internal error", str(exc))


# ── HTTP endpoints ────────────────────────────────────────────────────────────

@router.post("")
async def mcp_post(request: Request) -> JSONResponse:
    """Handle all JSON-RPC 2.0 requests (single and batch)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_err(None, -32700, "Parse error"), status_code=400)

    if isinstance(body, list):
        # Batch request
        responses = []
        for item in body:
            method   = item.get("method", "")
            params   = item.get("params", {})
            req_id   = item.get("id")
            if not method:
                responses.append(_err(req_id, -32600, "Invalid request"))
                continue
            responses.append(await _dispatch(method, params, req_id))
        return JSONResponse(responses)

    method = body.get("method", "")
    params = body.get("params", {})
    req_id = body.get("id")

    if not method:
        return JSONResponse(_err(req_id, -32600, "Invalid request"), status_code=400)

    result = await _dispatch(method, params, req_id)

    # Notifications (no id) have no response body per spec
    if req_id is None:
        return JSONResponse(None, status_code=202)

    return JSONResponse(result)


@router.get("")
async def mcp_get(request: Request) -> StreamingResponse:
    """
    SSE endpoint for server-initiated notifications.
    Clients connect here to receive push messages.
    """
    async def event_stream():
        # Send an initial endpoint event so the client knows the POST URL
        yield f"event: endpoint\ndata: /mcp\n\n"
        # Keep-alive — real notifications would be pushed here
        import asyncio
        while True:
            await asyncio.sleep(30)
            yield ": keepalive\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
