"""MCP Transport Adapters (Stdio & SSE)."""

import json
from typing import Dict, Any
from kryntis.mcp.server import MCPServer

class StdioTransport:
    """Stdio transport for local process communication."""
    def __init__(self, server: MCPServer) -> None:
        self.server = server

    async def process_line(self, line: str) -> str:
        try:
            req = json.loads(line)
            resp = await self.server.handle_jsonrpc(req)
            return json.dumps(resp)
        except Exception as e:
            return json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}})
