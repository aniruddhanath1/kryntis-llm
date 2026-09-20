"""Execution Context model."""

from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ExecutionContext:
    trace_id: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    stream: bool = False
    attributes: Dict[str, Any] = field(default_factory=dict)
