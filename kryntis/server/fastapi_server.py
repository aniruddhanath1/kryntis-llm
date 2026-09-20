"""FastAPI Server wrapper."""

import uvicorn
from kryntis.service.app import app

class FastAPIServer:
    """Server runner for FastAPI application."""
    def __init__(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self.app = app

    def start(self) -> None:
        uvicorn.run(self.app, host=self.host, port=self.port)
