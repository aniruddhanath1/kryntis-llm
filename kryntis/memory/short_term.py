"""
Short-term conversational memory — rolling token-bounded buffer.

Stores the active conversation history for a session and provides
token-aware truncation to keep context within model limits.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from kryntis.core.providers.base import Message
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class Turn:
    """A single conversation turn."""
    role: str           # "user" | "assistant" | "system"
    content: str
    timestamp: float = field(default_factory=time.time)
    token_count: int = 0

    def __post_init__(self):
        if not self.token_count:
            self.token_count = max(1, len(self.content) // 4)


class ShortTermMemory:
    """
    In-memory rolling conversation buffer.

    Enforces:
    - Maximum number of turns (default 20)
    - Maximum total token budget (default 2048)

    When limits are exceeded, oldest turns are dropped (FIFO).
    """

    def __init__(
        self,
        max_turns: int | None = None,
        max_tokens: int | None = None,
        session_id: str = "default",
    ) -> None:
        cfg = get_config().memory
        self._max_turns = max_turns or cfg.short_term_max_turns
        self._max_tokens = max_tokens or cfg.short_term_max_tokens
        self._session_id = session_id
        self._turns: deque[Turn] = deque()
        self._total_tokens = 0

    def add(self, role: str, content: str) -> None:
        """Append a turn and enforce limits."""
        turn = Turn(role=role, content=content)
        self._turns.append(turn)
        self._total_tokens += turn.token_count
        self._enforce_limits()
        log.debug(
            "short_term_memory_add",
            session=self._session_id,
            role=role,
            turns=len(self._turns),
            tokens=self._total_tokens,
        )

    def _enforce_limits(self) -> None:
        while len(self._turns) > self._max_turns:
            dropped = self._turns.popleft()
            self._total_tokens -= dropped.token_count

        while self._total_tokens > self._max_tokens and self._turns:
            dropped = self._turns.popleft()
            self._total_tokens -= dropped.token_count

    def get_messages(self) -> list[Message]:
        """Return the conversation history as Message objects."""
        return [Message(role=t.role, content=t.content) for t in self._turns]

    def get_turns(self) -> list[Turn]:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()
        self._total_tokens = 0
        log.info("short_term_memory_cleared", session=self._session_id)

    @property
    def turn_count(self) -> int:
        return len(self._turns)

    @property
    def token_count(self) -> int:
        return self._total_tokens

    def to_dict(self) -> dict:
        return {
            "session_id": self._session_id,
            "turns": [
                {"role": t.role, "content": t.content, "timestamp": t.timestamp}
                for t in self._turns
            ],
            "total_tokens": self._total_tokens,
        }
