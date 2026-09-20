"""Reverse Proxy router for upstream LLM providers."""

from typing import Dict, Any

class ReverseProxyRouter:
    """Routes requests to primary or fallback LLM providers."""
    def __init__(self, primary_url: str = "http://127.0.0.1:8000") -> None:
        self.primary_url = primary_url

    def route_request(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "routed_to": f"{self.primary_url}{path}",
            "status": "forwarded"
        }
