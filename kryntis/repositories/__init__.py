"""
Kryntis Repositories — SOLID Persistence Layer.
"""

from __future__ import annotations

from kryntis.repositories.base import (
    IDocumentRepository,
    IKnowledgeRepository,
    IRepository,
    ISessionRepository,
)
from kryntis.repositories.document_repository import SQLiteDocumentRepository
from kryntis.repositories.knowledge_repository import InMemoryKnowledgeRepository
from kryntis.repositories.session_repository import SQLiteSessionRepository

__all__ = [
    "IRepository",
    "IDocumentRepository",
    "ISessionRepository",
    "IKnowledgeRepository",
    "SQLiteDocumentRepository",
    "SQLiteSessionRepository",
    "InMemoryKnowledgeRepository",
]
