"""Bridge Router for inter-subsystem data transformation."""

from typing import Dict, Any, Callable

class BridgeRouter:
    """Routes events and RPC calls between subsystems."""
    def __init__(self) -> None:
        self._routes: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

    def register(self, topic: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self._routes[topic] = handler

    def dispatch(self, topic: str, payload: Dict[str, Any]) -> Any:
        handler = self._routes.get(topic)
        if not handler:
            raise KeyError(f"No bridge route registered for '{topic}'")
        return handler(payload)
