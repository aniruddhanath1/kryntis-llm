"""MCP Client Implementation."""

from typing import Dict, Any, List
from kryntis.mcp.server import MCPServer

class MCPClient:
    """Client interacting with in-memory or remote MCP Servers."""
    def __init__(self, server: MCPServer) -> None:
        self.server = server

    async def list_tools(self) -> List[Dict[str, Any]]:
        req = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        resp = await self.server.handle_jsonrpc(req)
        return resp.get("result", {}).get("tools", [])

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        resp = await self.server.handle_jsonrpc(req)
        if "error" in resp:
            raise RuntimeError(resp["error"]["message"])
        return resp.get("result", {}).get("content", [{}])[0].get("text")
