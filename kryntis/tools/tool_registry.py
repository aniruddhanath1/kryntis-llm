"""
Tool Registry — Central hub for registering, discovering, and executing AI model tools.

Supports standard Function Calling format (OpenAI / Anthropic / MCP compatible).
"""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    enum: list[str] | None = None
    default: Any = None


@dataclass
class ToolDefinition:
    """Metadata describing an AI tool."""
    name: str
    description: str
    parameters: list[ToolParameter]
    handler: Callable[..., Any]
    category: str = "general"

    def to_openai_schema(self) -> dict:
        """Export tool definition in OpenAI function-calling schema."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for p in self.parameters:
            prop: dict[str, Any] = {
                "type": p.type,
                "description": p.description,
            }
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_mcp_schema(self) -> dict:
        """Export tool definition in MCP (Model Context Protocol) format."""
        schema = self.to_openai_schema()
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": schema["function"]["parameters"],
        }


class ToolRegistry:
    """
    Registry for managing and executing AI tools.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool
        log.info("tool_registered", name=tool.name, category=tool.category)

    def register_function(
        self,
        name: str,
        description: str,
        parameters: list[ToolParameter],
        category: str = "general",
    ) -> Callable:
        """Decorator to register a function as an AI tool."""
        def decorator(func: Callable) -> Callable:
            tool = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                handler=func,
                category=category,
            )
            self.register(tool)
            return func
        return decorator

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self, category: str | None = None) -> list[ToolDefinition]:
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def get_schemas(self) -> list[dict]:
        """Return all tool schemas in OpenAI / LLM function calling format."""
        return [t.to_openai_schema() for t in self._tools.values()]

    async def execute(self, tool_name: str, arguments: dict[str, Any] | str) -> dict[str, Any]:
        """
        Execute a tool by name with arguments.

        Args:
            tool_name: Name of the registered tool.
            arguments: Dictionary or JSON string of arguments.

        Returns:
            Dictionary containing 'status', 'output', or 'error'.
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "status": "error",
                "error": f"Tool '{tool_name}' not found. Available: {list(self._tools.keys())}",
            }

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except Exception as e:
                return {"status": "error", "error": f"Invalid JSON arguments: {e}"}

        try:
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(**arguments)
            else:
                result = tool.handler(**arguments)

            return {
                "status": "success",
                "tool": tool_name,
                "output": result,
            }
        except Exception as e:
            log.error("tool_execution_error", tool=tool_name, error=str(e))
            return {
                "status": "error",
                "tool": tool_name,
                "error": str(e),
            }
