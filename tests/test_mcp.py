"""Tests for kryntis.mcp subsystem."""

import pytest
import asyncio
from kryntis.mcp import MCPServer, MCPClient

@pytest.mark.asyncio
async def test_mcp_server_initialize_and_tools():
    server = MCPServer(name="test-server", version="1.0.0")
    server.register_tool(
        name="echo_tool",
        description="Echos back message",
        handler=lambda msg: f"Echo: {msg}"
    )

    client = MCPClient(server=server)
    tools = await client.list_tools()
    assert len(tools) == 1
    assert tools[0]["name"] == "echo_tool"

    result = await client.call_tool("echo_tool", {"msg": "hello-kryntis"})
    assert result == "Echo: hello-kryntis"
