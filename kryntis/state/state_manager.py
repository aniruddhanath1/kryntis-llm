"""State Manager for application lifecycle state."""

from typing import Dict, Any, Callable, List

class StateManager:
    """Atomic state container with pub-sub event dispatch."""
    def __init__(self, initial_state: Dict[str, Any] = None) -> None:
        self._state = initial_state or {}
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def get_state(self) -> Dict[str, Any]:
        return self._state.copy()

    def update_state(self, updates: Dict[str, Any]) -> None:
        self._state.update(updates)
        for listener in self._listeners:
            listener(self._state)

    def subscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        self._listeners.append(listener)
