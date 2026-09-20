"""Serve command executor."""

from typing import Dict, Any

class ServeCommand:
    """Dispatches API server startup."""
    @staticmethod
    def execute(host: str = "127.0.0.1", port: int = 8000) -> Dict[str, Any]:
        return {
            "status": "ready",
            "host": host,
            "port": port,
            "url": f"http://{host}:{port}/docs"
        }
