"""Agent Type definitions."""

from typing import TypedDict, List, Dict, Any, Optional

class AgentConfigDict(TypedDict):
    agent_id: str
    name: str
    version: str
    model_size: str
    capabilities: List[str]

class TurnResultDict(TypedDict):
    response: str
    grounding_score: float
    session_id: str
    sources: List[Dict[str, Any]]
