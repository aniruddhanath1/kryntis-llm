"""Session Pydantic Schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class MessageSchema(BaseModel):
    role: str
    content: str
    timestamp: Optional[float] = None

class SessionDetailSchema(BaseModel):
    session_id: str
    messages: List[MessageSchema] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
