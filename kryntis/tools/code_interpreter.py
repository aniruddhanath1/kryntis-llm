"""
Code Interpreter Tool — executes sandboxed Python code snippets with strict AST validation and namespace restrictions.
"""

from __future__ import annotations

import ast
import contextlib
import io
import math
import json
import re
import collections
import itertools
import datetime
import statistics
import random
import traceback
from typing import Any

from kryntis.tools.tool_registry import ToolDefinition, ToolParameter

_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "bool": bool,
    "chr": chr,
    "complex": complex,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "format": format,
    "frozenset": frozenset,
    "hex": hex,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "True": True,
    "False": False,
    "None": None,
}

_BLOCKED_ATTRIBUTES = frozenset([
    "__class__",
    "__bases__",
    "__subclasses__",
    "__mro__",
    "__globals__",
    "__code__",
    "__builtins__",
    "__reduce__",
    "__reduce_ex__",
    "__getattribute__",
    "gi_frame",
    "cr_frame",
    "f_globals",
    "f_locals",
    "f_builtins",
    "tb_frame",
])


class SecurityVisitor(ast.NodeVisitor):
    """AST validator to detect and reject dangerous operations, imports, and dunder attribute traversal."""

    def visit_Import(self, node: ast.Import) -> None:
        raise PermissionError("Dynamic imports via 'import' statement are prohibited in sandboxed execution.")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        raise PermissionError("Dynamic imports via 'from ... import' statement are prohibited in sandboxed execution.")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _BLOCKED_ATTRIBUTES:
            raise PermissionError(f"Access to sensitive attribute '{node.attr}' is prohibited.")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in ("eval", "exec", "compile", "__import__", "open", "breakpoint"):
            raise PermissionError(f"Call to restricted builtin '{node.id}' is prohibited.")
        self.generic_visit(node)


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

    try:
        parsed = ast.parse(code)
        SecurityVisitor().visit(parsed)
    except SyntaxError as se:
        return {
            "success": False,
            "error": f"SyntaxError: {se}",
            "stdout": "",
            "stderr": "",
        }
    except PermissionError as pe:
        return {
            "success": False,
            "error": f"SecurityViolation: {pe}",
            "stdout": "",
            "stderr": "",
        }

    safe_globals: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "math": math,
        "json": json,
        "re": re,
        "collections": collections,
        "itertools": itertools,
        "datetime": datetime,
        "statistics": statistics,
        "random": random,
    }
    local_env: dict[str, Any] = {}

    with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
        try:
            compiled = compile(parsed, filename="<sandboxed_code>", mode="exec")
            exec(compiled, safe_globals, local_env)
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
