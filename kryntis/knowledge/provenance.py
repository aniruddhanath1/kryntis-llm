"""
Provenance — tracks the origin of every piece of knowledge.

Every chunk stored in Kryntis AI carries a Provenance record so
the system can always answer "where did this come from, how confident
are we, and has it been validated?"
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ProvenanceType(str, Enum):
    DOCUMENT = "document"       # Uploaded file
    INTERNET = "internet"       # Web search result
    CONVERSATION = "conversation"  # Approved conversation turn
    LEARNED = "learned"         # Continual learning batch
    MANUAL = "manual"           # Manually curated


@dataclass
class Provenance:
    """Full provenance record for a knowledge chunk."""

    chunk_id: str
    source_type: ProvenanceType
    source_url: str = ""
    source_path: str = ""
    source_name: str = ""
    domain: str = ""

    retrieved_at: float = field(default_factory=time.time)
    added_at: float = field(default_factory=time.time)

    confidence: float = 1.0          # 0.0 → 1.0
    authority_score: float = 0.5     # Domain/source authority
    validated: bool = True
    human_approved: bool = False

    # Versioning
    version: int = 1
    previous_version_id: str | None = None

    # Cross-referencing
    supporting_sources: list[str] = field(default_factory=list)
    contradicting_sources: list[str] = field(default_factory=list)

    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "source_type": self.source_type.value,
            "source_url": self.source_url,
            "source_path": self.source_path,
            "source_name": self.source_name,
            "domain": self.domain,
            "retrieved_at": self.retrieved_at,
            "added_at": self.added_at,
            "confidence": self.confidence,
            "authority_score": self.authority_score,
            "validated": self.validated,
            "human_approved": self.human_approved,
            "version": self.version,
            "previous_version_id": self.previous_version_id,
            "supporting_sources": self.supporting_sources,
            "contradicting_sources": self.contradicting_sources,
            "notes": self.notes,
        }

    @classmethod
    def for_document(cls, chunk_id: str, path: str, name: str, confidence: float = 1.0) -> "Provenance":
        return cls(
            chunk_id=chunk_id,
            source_type=ProvenanceType.DOCUMENT,
            source_path=path,
            source_name=name,
            confidence=confidence,
            validated=True,
        )

    @classmethod
    def for_internet(
        cls,
        chunk_id: str,
        url: str,
        domain: str,
        confidence: float,
        authority_score: float,
        validated: bool = False,
    ) -> "Provenance":
        return cls(
            chunk_id=chunk_id,
            source_type=ProvenanceType.INTERNET,
            source_url=url,
            domain=domain,
            confidence=confidence,
            authority_score=authority_score,
            validated=validated,
        )
