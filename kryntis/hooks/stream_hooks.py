"""Streaming token generation hooks."""

from typing import Callable, List

class StreamHooks:
    """Hooks executed during token-by-token streaming."""
    def __init__(self) -> None:
        self._on_token_hooks: List[Callable[[str], None]] = []

    def register_on_token(self, callback: Callable[[str], None]) -> None:
        self._on_token_hooks.append(callback)

    def trigger_on_token(self, token: str) -> None:
        for cb in self._on_token_hooks:
            cb(token)
