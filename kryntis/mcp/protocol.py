"""Kryntis Model Context Protocol (MCP) Protocol Specifications."""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

@dataclass
class MCPToolDefinition:
    """MCP standard tool schema."""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MCPResourceDefinition:
    """MCP standard resource schema."""
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
