"""Plugin Manifest definition."""

from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class PluginManifest:
    name: str
    version: str
    description: str = ""
    author: str = ""
    capabilities: List[str] = field(default_factory=list)
