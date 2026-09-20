"""Assistant Core implementation for multi-turn cognitive conversations."""

from typing import Dict, Any, List, Optional
from kryntis.orchestrator.agent_loop import default_agent_loop

class AssistantCore:
    """Core autonomous cognitive assistant."""
    def __init__(self, system_persona: str = "Kryntis Sovereign Intelligence") -> None:
        self.system_persona = system_persona
        self.agent_loop = default_agent_loop

    def handle_message(self, user_text: str, session_id: str = "assistant-session") -> Dict[str, Any]:
        return self.agent_loop.run_turn(user_prompt=user_text, session_id=session_id)
