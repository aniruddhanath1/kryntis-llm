"""WebSocket Server handler for real-time streaming."""

from typing import List, Any

class WebSocketServerHandler:
    """Manages active WebSocket connections."""
    def __init__(self) -> None:
        self.active_connections: List[Any] = []

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: Any) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        for connection in self.active_connections:
            await connection.send_text(message)
