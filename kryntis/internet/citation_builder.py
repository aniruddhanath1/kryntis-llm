"""Structured citation builder for internet research results."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Citation:
    """A citable internet source."""
    url: str
    title: str
    snippet: str
    trust_score: float
    retrieved_at: float = field(default_factory=time.time)
    domain: str = ""

    def __post_init__(self):
        from urllib.parse import urlparse
        self.domain = urlparse(self.url).netloc

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet[:300],
            "trust_score": round(self.trust_score, 3),
            "domain": self.domain,
            "retrieved_at": self.retrieved_at,
        }

    def __str__(self) -> str:
        return f"[{self.title}]({self.url}) — trust: {self.trust_score:.2f}"


class CitationBuilder:
    """Builds Citation objects from fetched web content."""

    def build(
        self,
        url: str,
        title: str,
        snippet: str,
        trust_score: float,
    ) -> Citation:
        return Citation(url=url, title=title or url, snippet=snippet, trust_score=trust_score)
