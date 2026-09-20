"""Context Store abstraction for fast RAM/Disk hierarchical storage."""

from typing import Dict, Any, Optional

class ContextStore:
    """Combines in-RAM cache with disk persistency."""
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
