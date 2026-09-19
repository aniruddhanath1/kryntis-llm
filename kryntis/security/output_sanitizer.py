"""Output sanitizer — removes leaked credentials, PII, and unsafe content."""

from __future__ import annotations

import re

_PII_PATTERNS = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),        # Email
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),     # Phone
    re.compile(r"\b4[0-9]{12}(?:[0-9]{3})?\b"),                                   # Visa
    re.compile(r"\b(?:sk|pk|api)[-_][a-zA-Z0-9]{20,}\b", re.IGNORECASE),         # API keys
    re.compile(r"\b[A-Z0-9]{20,}\b"),                                              # Generic secret
]


class OutputSanitizer:
    """Redacts sensitive information from LLM outputs."""

    def sanitize(self, text: str) -> str:
        for pattern in _PII_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text
