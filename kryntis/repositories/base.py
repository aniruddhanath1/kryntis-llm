"""
Repository Pattern Base Interfaces — SOLID data persistence abstraction layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Sequence, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class IRepository(ABC, Generic[T, ID]):
    """Generic Repository Interface (Interface Segregation Principle)."""

    @abstractmethod
    async def get_by_id(self, entity_id: ID) -> T | None:
        """Retrieve an entity by its unique ID."""
        ...

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[T]:
        """List entities with pagination."""
        ...

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Persist or update an entity."""
        ...

    @abstractmethod
    async def delete(self, entity_id: ID) -> bool:
        """Delete an entity by its unique ID."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Return total count of entities."""
        ...


class IDocumentRepository(IRepository[dict, str]):
    """Document metadata and chunk persistence interface."""

    @abstractmethod
    async def search_by_text(self, query: str, limit: int = 10) -> list[dict]:
        """Search documents matching text query."""
        ...

    @abstractmethod
    async def get_by_source_id(self, source_id: str) -> list[dict]:
        """Retrieve all document chunks belonging to a source document."""
        ...


class ISessionRepository(IRepository[dict, str]):
    """Session dialogue and context persistence interface."""

    @abstractmethod
    async def append_turn(self, session_id: str, role: str, content: str, metadata: dict | None = None) -> dict:
        """Append a conversational turn to the session."""
        ...

    @abstractmethod
    async def get_recent_turns(self, session_id: str, limit: int = 50) -> list[dict]:
        """Retrieve recent conversation turns for a session."""
        ...

    @abstractmethod
    async def search_turns(self, session_id: str, query: str, limit: int = 10) -> list[dict]:
        """Search conversation turns within a session."""
        ...


class IKnowledgeRepository(IRepository[dict, str]):
    """Vector and semantic knowledge persistence interface."""

    @abstractmethod
    async def find_similar(self, query_embedding: list[float], top_k: int = 5, score_threshold: float = 0.0) -> list[dict]:
        """Find knowledge records by vector similarity."""
        ...
