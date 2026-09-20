"""Agent Card and Schema definitions."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class AgentSkillSchema(BaseModel):
    id: str
    name: str
    description: str

class AgentCardSchema(BaseModel):
    agent_id: str
    name: str
    version: str
    description: str
    endpoint: str
    skills: List[AgentSkillSchema] = Field(default_factory=list)
