"""Subagent Definition Models."""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable

@dataclass
class SubagentDefinition:
    """Specification of an autonomous subagent."""
    name: str
    role: str
    description: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
