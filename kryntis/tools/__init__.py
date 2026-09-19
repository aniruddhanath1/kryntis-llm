"""
AI Tooling Ecosystem — Sandboxed code execution, math calculation, file system,
web browser, database, HTTP client, system information, media analyzer, and biometric telemetry tools.
"""

from __future__ import annotations

from kryntis.tools.biometric_analyzer import TOOL_BIOMETRIC_ANALYZER
from kryntis.tools.calculator import TOOL_CALCULATOR
from kryntis.tools.code_interpreter import TOOL_CODE_INTERPRETER
from kryntis.tools.database import TOOL_DATABASE_SQL
from kryntis.tools.file_system import TOOL_FS_LIST, TOOL_FS_READ
from kryntis.tools.http_client import TOOL_HTTP_CLIENT
from kryntis.tools.media_analyzer import TOOL_MEDIA_ANALYZER
from kryntis.tools.system_info import TOOL_SYSTEM_INFO
from kryntis.tools.tool_registry import ToolDefinition, ToolParameter, ToolRegistry
from kryntis.tools.web_browser import TOOL_WEB_BROWSER


def get_default_tool_registry() -> ToolRegistry:
    """Return a pre-configured ToolRegistry with all standard AI tools registered."""
    registry = ToolRegistry()
    registry.register(TOOL_CODE_INTERPRETER)
    registry.register(TOOL_CALCULATOR)
    registry.register(TOOL_FS_READ)
    registry.register(TOOL_FS_LIST)
    registry.register(TOOL_WEB_BROWSER)
    registry.register(TOOL_DATABASE_SQL)
    registry.register(TOOL_HTTP_CLIENT)
    registry.register(TOOL_SYSTEM_INFO)
    registry.register(TOOL_MEDIA_ANALYZER)
    registry.register(TOOL_BIOMETRIC_ANALYZER)
    return registry


__all__ = [
    "ToolRegistry",
    "ToolDefinition",
    "ToolParameter",
    "get_default_tool_registry",
    "TOOL_CODE_INTERPRETER",
    "TOOL_CALCULATOR",
    "TOOL_FS_READ",
    "TOOL_FS_LIST",
    "TOOL_WEB_BROWSER",
    "TOOL_DATABASE_SQL",
    "TOOL_HTTP_CLIENT",
    "TOOL_SYSTEM_INFO",
    "TOOL_MEDIA_ANALYZER",
    "TOOL_BIOMETRIC_ANALYZER",
]
