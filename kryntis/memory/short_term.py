"""
Short-term conversational memory — 5B-capable virtual session context buffer.

Stores active conversation history and delegates to the disk-backed
5B SessionContextManager for unlimited prompt history per session.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field

from kryntis.core.providers.base import Message
from kryntis.memory.session_context_manager import SessionContextManager
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
    Session conversation manager backed by 5B virtual context store.

    Supports up to 5,000,000,000 tokens per session while providing
    active sliding windows for model context.
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
        self._context_mgr = SessionContextManager(
            session_id=session_id,
            max_active_tokens=self._max_tokens,
        )

    def add(self, role: str, content: str) -> None:
        """Append a turn to active cache and persistent 5B session store."""
        turn = Turn(role=role, content=content)
        self._turns.append(turn)
        self._total_tokens += turn.token_count
        self._context_mgr.add_turn(role=role, content=content)
        self._enforce_limits()
        log.debug(
            "short_term_memory_add",
            session=self._session_id,
            role=role,
            turns=len(self._turns),
            tokens=self._total_tokens,
            total_session_5b_tokens=self._context_mgr.total_tokens,
        )

    def _enforce_limits(self) -> None:
        while len(self._turns) > self._max_turns:
            dropped = self._turns.popleft()
            self._total_tokens -= dropped.token_count

        while self._total_tokens > self._max_tokens and self._turns:
            dropped = self._turns.popleft()
            self._total_tokens -= dropped.token_count

    def get_messages(self) -> list[Message]:
        """Return active conversation history as Message objects."""
        return [Message(role=t.role, content=t.content) for t in self._turns]

    def get_session_context(self, max_tokens: int | None = None) -> list[Message]:
        """Retrieve sliding context window from 5B session manager."""
        return self._context_mgr.get_context_window(max_tokens=max_tokens)

    def search_context(self, query: str, top_k: int = 5) -> list[str]:
        """Search historical turns across the 5B session memory."""
        return self._context_mgr.search_session_context(query, top_k=top_k)

    def get_turns(self) -> list[Turn]:
        return list(self._turns)

    def clear(self) -> None:
        self._turns.clear()
        self._total_tokens = 0
        self._context_mgr.clear()
        log.info("short_term_memory_cleared", session=self._session_id)

    @property
    def turn_count(self) -> int:
        return len(self._turns)

    @property
    def token_count(self) -> int:
        return self._total_tokens

    @property
    def total_session_tokens(self) -> int:
        return self._context_mgr.total_tokens

    def to_dict(self) -> dict:
        return {
            "session_id": self._session_id,
            "turns": [
                {"role": t.role, "content": t.content, "timestamp": t.timestamp}
                for t in self._turns
            ],
            "active_tokens": self._total_tokens,
            "session_5b_total_tokens": self._context_mgr.total_tokens,
        }
