"""
URL and domain trust validator.
"""

from __future__ import annotations

from urllib.parse import urlparse

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

# High-trust domains get a bonus score
_HIGH_TRUST_DOMAINS = {
    "wikipedia.org", "britannica.com", "nature.com", "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com", "arxiv.org", "bbc.com", "reuters.com",
    "nytimes.com", "theguardian.com", "gov", "edu",
}

_BLOCKED_SCHEMES = {"javascript", "data", "file", "ftp"}


class URLValidator:
    """Validates URLs and computes domain trust scores."""

    def __init__(self) -> None:
        cfg = get_config().internet
        self._blocked_domains: set[str] = set(cfg.blocked_domains)

    def is_allowed(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme in _BLOCKED_SCHEMES:
                return False
            if not parsed.netloc:
                return False
            domain = parsed.netloc.lower()
            for blocked in self._blocked_domains:
                if blocked in domain:
                    return False
            return True
        except Exception:
            return False

    def trust_score(self, url: str, content: str = "") -> float:
        """
        Compute a [0, 1] trust score for a URL.

        Heuristics:
        - HTTPS: +0.1
        - Known trusted domain: +0.3
        - .gov / .edu TLD: +0.2
        - Content length > 500 chars: +0.1
        - HTTPS + substantial content: baseline 0.4
        """
        try:
            parsed = urlparse(url)
            score = 0.3  # baseline

            if parsed.scheme == "https":
                score += 0.1

            domain = parsed.netloc.lower()
            for trusted in _HIGH_TRUST_DOMAINS:
                if trusted in domain:
                    score += 0.3
                    break

            tld = domain.split(".")[-1] if "." in domain else ""
            if tld in ("gov", "edu", "ac"):
                score += 0.2

            if len(content) > 500:
                score += 0.1

            return min(1.0, score)
        except Exception:
            return 0.0
