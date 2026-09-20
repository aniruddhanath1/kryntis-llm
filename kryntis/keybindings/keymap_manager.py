"""Keymap Manager for CLI interactive hotkeys."""

from typing import Dict, Callable

class KeymapManager:
    """Dispatches keypress actions."""
    def __init__(self) -> None:
        self._mappings: Dict[str, Callable[[], None]] = {}

    def bind(self, key: str, action: Callable[[], None]) -> None:
        self._mappings[key] = action

    def handle_key(self, key: str) -> bool:
        if key in self._mappings:
            self._mappings[key]()
            return True
        return False
