"""
File System Tool — safe workspace file operations with directory boundary confinement.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from kryntis.tools.tool_registry import ToolDefinition, ToolParameter


def get_workspace_root() -> Path:
    """Return the absolute Path to the allowed workspace root."""
    ws_env = os.environ.get("KRYNTIS_WORKSPACE_DIR")
    if ws_env:
        return Path(ws_env).resolve()
    return Path.cwd().resolve()


_SENSITIVE_PATTERNS = frozenset([
    ".env",
    ".env-encryption.key",
    ".env-develop",
    ".env-stage",
    ".env-qa",
    ".env-prod",
])


def _resolve_safe_workspace_path(path_str: str) -> Path:
    """
    Resolve and validate that a path is strictly inside the allowed workspace root
    and does not access sensitive system/key files.
    """
    root = get_workspace_root()
    p = Path(path_str)
    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()

    try:
        p.relative_to(root)
    except ValueError:
        raise PermissionError(f"Access denied: Path '{path_str}' is outside the authorized workspace '{root}'.")

    if p.name in _SENSITIVE_PATTERNS or p.suffix in (".key", ".pem", ".cert", ".crt"):
        raise PermissionError(f"Access denied: Reading secret or key file '{p.name}' is prohibited.")

    return p


def fs_read_file(path: str, max_chars: int = 10000) -> dict[str, Any]:
    """Read contents of a file within the workspace with safety bounds."""
    try:
        p = _resolve_safe_workspace_path(path)
    except PermissionError as pe:
        return {"error": str(pe)}
    except Exception as e:
        return {"error": f"Invalid path: {e}"}

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
    """List contents of a directory within the workspace."""
    try:
        p = _resolve_safe_workspace_path(directory)
    except PermissionError as pe:
        return {"error": str(pe)}
    except Exception as e:
        return {"error": f"Invalid directory path: {e}"}

    if not p.exists():
        return {"error": f"Directory not found: {directory}"}
    if not p.is_dir():
        return {"error": f"Path is not a directory: {directory}"}
    try:
        items = []
        for child in sorted(p.iterdir()):
            if child.name.startswith(".env") or child.suffix in (".key", ".pem"):
                continue
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
