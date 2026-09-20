"""
HTTP Client Tool — dispatches HTTP REST requests (GET, POST, PUT, DELETE) with SSRF safety validation.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from kryntis.security.ssrf import SSRFValidationError, validate_safe_url
from kryntis.tools.tool_registry import ToolDefinition, ToolParameter


def http_request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    body: str | None = None,
) -> dict[str, Any]:
    """
    Send an HTTP REST request with SSRF validation.

    Args:
        method: HTTP verb (GET, POST, PUT, DELETE, PATCH).
        url: Target URL.
        headers: Optional HTTP headers dictionary.
        body: Optional request body string.

    Returns:
        dict with status_code, headers, and response text.
    """
    method = method.upper()
    try:
        url = validate_safe_url(url)
    except SSRFValidationError as se:
        return {"status_code": 0, "error": f"SSRF Protection Error: {se}", "success": False}
    except Exception as e:
        return {"status_code": 0, "error": f"Invalid URL: {e}", "success": False}

    req_headers = headers or {}
    if "User-Agent" not in req_headers:
        req_headers["User-Agent"] = "KryntisAI/1.0 (Autonomous Agent)"

    data = body.encode("utf-8") if body else None

    try:
        req = urllib.request.Request(
            url=url,
            data=data,
            headers=req_headers,
            method=method,
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            status_code = resp.status
            resp_headers = dict(resp.headers)
            resp_data = resp.read().decode("utf-8", errors="ignore")

        return {
            "status_code": status_code,
            "headers": resp_headers,
            "body": resp_data[:5000],
            "success": 200 <= status_code < 300,
        }
    except urllib.error.HTTPError as e:
        return {
            "status_code": e.code,
            "error": str(e),
            "body": e.read().decode("utf-8", errors="ignore")[:2000],
            "success": False,
        }
    except Exception as e:
        return {"status_code": 0, "error": str(e), "success": False}


TOOL_HTTP_CLIENT = ToolDefinition(
    name="http_request",
    description="Sends HTTP REST requests (GET, POST, PUT, DELETE) to web APIs.",
    parameters=[
        ToolParameter(
            name="method",
            type="string",
            description="HTTP method (GET, POST, PUT, DELETE).",
            required=True,
            enum=["GET", "POST", "PUT", "DELETE", "PATCH"],
        ),
        ToolParameter(
            name="url",
            type="string",
            description="Target URL to request.",
            required=True,
        ),
        ToolParameter(
            name="headers",
            type="object",
            description="HTTP header key-value pairs.",
            required=False,
            default=None,
        ),
        ToolParameter(
            name="body",
            type="string",
            description="Request payload body string (JSON/text).",
            required=False,
            default=None,
        ),
    ],
    handler=http_request,
    category="web",
)
