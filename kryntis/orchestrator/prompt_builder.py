"""Prompt builder — assembles grounded system prompts."""

from __future__ import annotations

from kryntis.core.providers.base import Message


class PromptBuilder:
    """Constructs structured prompts for different task types."""

    _BASE_SYSTEM = (
        "You are Kryntis AI, a knowledgeable, honest, and helpful assistant. "
        "Always cite your sources. Never fabricate facts. "
        "If you don't know something, say so clearly."
    )

    def build_chat_messages(
        self,
        user_message: str,
        history: list[Message],
        context: str = "",
    ) -> list[Message]:
        system = self._BASE_SYSTEM
        if context:
            system += f"\n\nRelevant context:\n{context}"

        messages = [Message(role="system", content=system)]
        messages.extend(history)
        messages.append(Message(role="user", content=user_message))
        return messages
