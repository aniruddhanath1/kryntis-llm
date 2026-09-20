"""Session lifecycle hooks."""

from typing import Callable, List, Dict, Any

class SessionHooks:
    """Manages event callbacks during session start, message, and termination."""
    def __init__(self) -> None:
        self._on_start_hooks: List[Callable[[str], None]] = []
        self._on_turn_hooks: List[Callable[[str, Dict[str, Any]], None]] = []

    def register_on_start(self, callback: Callable[[str], None]) -> None:
        self._on_start_hooks.append(callback)

    def trigger_on_start(self, session_id: str) -> None:
        for cb in self._on_start_hooks:
            cb(session_id)
