"""Conversation Manager for active assistant sessions."""

from typing import Dict, List, Any
import uuid

class ConversationManager:
    """Manages active conversations and message history."""
    def __init__(self) -> None:
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}

    def create_conversation(self) -> str:
        cid = str(uuid.uuid4())
        self._conversations[cid] = []
        return cid

    def add_message(self, cid: str, role: str, content: str) -> None:
        if cid not in self._conversations:
            self._conversations[cid] = []
        self._conversations[cid].append({"role": role, "content": content})

    def get_history(self, cid: str) -> List[Dict[str, Any]]:
        return self._conversations.get(cid, [])
