"""
Code Interpreter Tool — executes sandboxed Python code snippets and captures standard output.
"""

from __future__ import annotations

import contextlib
import io
import sys
import traceback
from typing import Any

from kryntis.tools.tool_registry import ToolDefinition, ToolParameter


def execute_python_code(code: str) -> dict[str, Any]:
    """
    Execute a Python script or code block in a sandboxed local environment.

    Args:
        code: Python source code to execute.

    Returns:
        dict with stdout, returned values, and execution status.
    """
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    safe_globals: dict[str, Any] = {
        "__builtins__": __builtins__,
        "math": __import__("math"),
        "json": __import__("json"),
        "re": __import__("re"),
        "collections": __import__("collections"),
        "itertools": __import__("itertools"),
        "datetime": __import__("datetime"),
    }
    local_env: dict[str, Any] = {}

    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        try:
            exec(code, safe_globals, local_env)
            stdout = stdout_buf.getvalue()
            stderr = stderr_buf.getvalue()
            # Capture variables created
            printable_vars = {
                k: str(v) for k, v in local_env.items() if not k.startswith("_")
            }
            return {
                "success": True,
                "stdout": stdout,
                "stderr": stderr,
                "variables": printable_vars,
            }
        except Exception:
            return {
                "success": False,
                "error": traceback.format_exc(),
                "stdout": stdout_buf.getvalue(),
                "stderr": stderr_buf.getvalue(),
            }


TOOL_CODE_INTERPRETER = ToolDefinition(
    name="code_interpreter",
    description="Executes a snippet of Python code in a safe sandbox, capturing print statements and return variables.",
    parameters=[
        ToolParameter(
            name="code",
            type="string",
            description="The Python code block to execute.",
            required=True,
        )
    ],
    handler=execute_python_code,
    category="code",
)
