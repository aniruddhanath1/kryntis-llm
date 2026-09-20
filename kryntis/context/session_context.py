"""Session Context model."""

from dataclasses import dataclass, field
from typing import Dict, Any, List
import time

@dataclass
class SessionContext:
    session_id: str
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    active_tools: List[str] = field(default_factory=list)
    total_tokens_processed: int = 0
