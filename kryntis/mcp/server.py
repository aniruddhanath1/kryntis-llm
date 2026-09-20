"""MCP Server Implementation."""

from typing import Dict, Any, Callable, Optional, List
import inspect
from kryntis.mcp.protocol import MCPToolDefinition, MCPResourceDefinition

class MCPServer:
    """JSON-RPC 2.0 compliant MCP Server for tools and resources."""
    def __init__(self, name: str = "kryntis-mcp-server", version: str = "4.0.0") -> None:
        self.name = name
        self.version = version
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, MCPResourceDefinition] = {}

    def register_tool(self, name: str, description: str, handler: Callable[..., Any], input_schema: Optional[Dict[str, Any]] = None) -> None:
        self._tools[name] = {
            "definition": MCPToolDefinition(name=name, description=description, input_schema=input_schema or {}),
            "handler": handler
        }

    def register_resource(self, uri: str, name: str, description: str, mime_type: str = "text/plain") -> None:
        self._resources[uri] = MCPResourceDefinition(uri=uri, name=name, description=description, mime_type=mime_type)

    async def handle_jsonrpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "serverInfo": {"name": self.name, "version": self.version},
                    "capabilities": {"tools": {}, "resources": {}}
                }
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {"name": item["definition"].name, "description": item["definition"].description, "inputSchema": item["definition"].input_schema}
                        for item in self._tools.values()
                    ]
                }
            }
        elif method == "tools/call":
            tool_name = params.get("name", "")
            args = params.get("arguments", {})
            if tool_name not in self._tools:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}
                }
            handler = self._tools[tool_name]["handler"]
            if inspect.iscoroutinefunction(handler):
                res = await handler(**args)
            else:
                res = handler(**args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": str(res)}]}
            }
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "resources": [
                        {"uri": r.uri, "name": r.name, "description": r.description, "mimeType": r.mime_type}
                        for r in self._resources.values()
                    ]
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"}
        }

default_mcp_server = MCPServer()
