"""
System Info Tool — inspects host platform, memory, OS version, CPU, and runtime environment with sanitized output.
"""

from __future__ import annotations

import os
import platform
import sys
from typing import Any

from kryntis.tools.tool_registry import ToolDefinition, ToolParameter


def get_system_info() -> dict[str, Any]:
    """Retrieve host platform, OS, architecture, and Python runtime details safely."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "workspace_status": "active",
    }


TOOL_SYSTEM_INFO = ToolDefinition(
    name="system_info",
    description="Inspects host environment metrics: operating system, architecture, CPU count, and Python runtime.",
    parameters=[],
    handler=get_system_info,
    category="system",
)
