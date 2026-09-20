"""Message Type definitions."""

from typing import TypedDict, Optional

class MessageDict(TypedDict):
    role: str
    content: str
    timestamp: Optional[float]
