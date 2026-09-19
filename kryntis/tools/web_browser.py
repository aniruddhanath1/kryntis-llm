"""
Web Browser Tool — fetch webpages, scrape readable text, and query the web.
"""

from __future__ import annotations

import re
from typing import Any
import urllib.request
import urllib.parse

from kryntis.tools.tool_registry import ToolDefinition, ToolParameter


def fetch_webpage(url: str, max_chars: int = 8000) -> dict[str, Any]:
    """Fetch URL and extract clean text without HTML tags."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "KryntisAI/1.0 (Autonomous Tool Agent)"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Strip scripts, styles, and HTML tags
        text = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        return {
            "url": url,
            "status": "success",
            "content": text[:max_chars],
            "total_length": len(text),
        }
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


TOOL_WEB_BROWSER = ToolDefinition(
    name="web_fetch",
    description="Fetches a public web page URL and extracts readable text content.",
    parameters=[
        ToolParameter(
            name="url",
            type="string",
            description="The HTTP or HTTPS URL to fetch and read.",
            required=True,
        ),
        ToolParameter(
            name="max_chars",
            type="integer",
            description="Maximum text characters to return (default 8000).",
            required=False,
            default=8000,
        ),
    ],
    handler=fetch_webpage,
    category="web",
)
