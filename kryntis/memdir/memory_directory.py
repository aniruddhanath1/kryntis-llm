"""Memory Directory subsystem for local file-backed memory caches."""

import os
import json
from typing import Dict, Any, Optional

class MemoryDirectory:
    """Manages file-backed context trees and transient scratchpads."""
    def __init__(self, base_dir: str = "data/memdir") -> None:
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def write_memory(self, key: str, data: Dict[str, Any]) -> str:
        filepath = os.path.join(self.base_dir, f"{key}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return filepath

    def read_memory(self, key: str) -> Optional[Dict[str, Any]]:
        filepath = os.path.join(self.base_dir, f"{key}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
