"""
Calculator Tool — performs high-precision mathematical, scientific, and algebraic evaluations.
"""

from __future__ import annotations

import math
from typing import Any

from kryntis.tools.tool_registry import ToolDefinition, ToolParameter


def calculate_expression(expression: str) -> dict[str, Any]:
    """
    Evaluate a mathematical or scientific expression.

    Args:
        expression: Mathematical string (e.g. 'sqrt(144) + 2**10', 'sin(pi/2) * 50').

    Returns:
        Result of calculation.
    """
    allowed_names = {
        k: getattr(math, k) for k in dir(math) if not k.startswith("_")
    }
    allowed_names.update({
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
    })

    try:
        # Safe eval using limited namespace and no builtins
        result = eval(expression, {"__builtins__": None}, allowed_names)
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
