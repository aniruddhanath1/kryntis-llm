"""
Calculator Tool — performs high-precision mathematical, scientific, and algebraic evaluations using a safe AST parser.
"""

from __future__ import annotations

import ast
import math
import operator as op
from typing import Any, Callable

from kryntis.tools.tool_registry import ToolDefinition, ToolParameter

_SAFE_OPERATORS: dict[type, Callable[..., Any]] = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}

_SAFE_MATH_FUNCTIONS: dict[str, Callable[..., Any]] = {
    k: getattr(math, k)
    for k in dir(math)
    if not k.startswith("_") and callable(getattr(math, k))
}
_SAFE_MATH_FUNCTIONS.update({
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
})

_SAFE_CONSTANTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
    "nan": math.nan,
}


def _safe_eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, complex)):
            return node.value
        raise ValueError(f"Literal constants of type {type(node.value).__name__} are not permitted.")

    if isinstance(node, ast.Name):
        if node.id in _SAFE_CONSTANTS:
            return _SAFE_CONSTANTS[node.id]
        if node.id in _SAFE_MATH_FUNCTIONS:
            return _SAFE_MATH_FUNCTIONS[node.id]
        raise ValueError(f"Unknown variable or function: '{node.id}'")

    if isinstance(node, ast.UnaryOp):
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        operand = _safe_eval_node(node.operand)
        return op_func(operand)

    if isinstance(node, ast.BinOp):
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Unsupported binary operator: {type(node.op).__name__}")
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        if isinstance(node.op, ast.Pow) and isinstance(right, (int, float)) and right > 10000:
            raise ValueError("Exponent too large (> 10000) - operation aborted for safety.")
        return op_func(left, right)

    if isinstance(node, ast.Call):
        func = _safe_eval_node(node.func)
        if not callable(func):
            raise ValueError(f"Expression is not callable: {func}")
        args = [_safe_eval_node(arg) for arg in node.args]
        return func(*args)

    if isinstance(node, (ast.List, ast.Tuple)):
        return [_safe_eval_node(elt) for elt in node.elts]

    raise ValueError(f"Unsupported syntax construct: {type(node).__name__}")


def calculate_expression(expression: str) -> dict[str, Any]:
    """
    Evaluate a mathematical or scientific expression using strict AST evaluation.

    Args:
        expression: Mathematical string (e.g. 'sqrt(144) + 2**10', 'sin(pi/2) * 50').

    Returns:
        Result of calculation.
    """
    try:
        parsed = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval_node(parsed)
        return {
            "expression": expression,
            "result": result,
            "formatted": f"{result}",
        }
    except Exception as e:
        return {
            "expression": expression,
            "error": f"Evaluation error: {e}",
        }


TOOL_CALCULATOR = ToolDefinition(
    name="calculator",
    description="Evaluates mathematical expressions, trigonometry, logarithms, powers, and scientific calculations.",
    parameters=[
        ToolParameter(
            name="expression",
            type="string",
            description="The mathematical formula or expression to evaluate (e.g. 'sin(pi/4) * sqrt(2)', '1024 * 768 / 60').",
            required=True,
        )
    ],
    handler=calculate_expression,
    category="math",
)
