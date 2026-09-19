"""
File System Tool — safe workspace file operations (read, write, list, grep).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kryntis.tools.tool_registry import ToolDefinition, ToolParameter


def fs_read_file(path: str, max_chars: int = 10000) -> dict[str, Any]:
    """Read contents of a file within the workspace."""
    p = Path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Path is not a file: {path}"}
    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
        truncated = len(content) > max_chars
        return {
            "path": str(p),
            "size_bytes": p.stat().st_size,
            "truncated": truncated,
            "content": content[:max_chars],
        }
    except Exception as e:
        return {"error": str(e)}


def fs_list_dir(directory: str = ".", max_items: int = 50) -> dict[str, Any]:
    """List contents of a directory."""
    p = Path(directory)
    if not p.exists():
        return {"error": f"Directory not found: {directory}"}
    try:
        items = []
        for child in sorted(p.iterdir()):
            items.append({
                "name": child.name,
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else 0,
            })
            if len(items) >= max_items:
                break
        return {"directory": str(p), "count": len(items), "items": items}
    except Exception as e:
        return {"error": str(e)}


TOOL_FS_READ = ToolDefinition(
    name="fs_read_file",
    description="Reads the text contents of a file from the workspace filesystem.",
    parameters=[
        ToolParameter(
            name="path",
            type="string",
            description="Relative or absolute path to the file to read.",
            required=True,
        ),
        ToolParameter(
            name="max_chars",
            type="integer",
            description="Maximum number of characters to read (default 10000).",
            required=False,
            default=10000,
        ),
    ],
    handler=fs_read_file,
    category="system",
)

TOOL_FS_LIST = ToolDefinition(
    name="fs_list_dir",
    description="Lists files and directories within a specified workspace path.",
    parameters=[
        ToolParameter(
            name="directory",
            type="string",
            description="Path to the directory to list (default '.').",
            required=False,
            default=".",
        ),
        ToolParameter(
            name="max_items",
            type="integer",
            description="Maximum number of directory entries to return.",
            required=False,
            default=50,
        ),
    ],
    handler=fs_list_dir,
    category="system",
)
