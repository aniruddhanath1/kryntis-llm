"""
Intent Router — classifies user messages into intent categories.
"""

from __future__ import annotations

import re
from enum import Enum


class Intent(str, Enum):
    CHAT = "chat"
    DOCUMENT_QA = "document_qa"
    INTERNET_SEARCH = "internet_search"
    FACTUAL_QUERY = "factual_query"
    KNOWLEDGE_QUERY = "knowledge_query"
    ADMIN = "admin"
    LEARN = "learn"
    UNKNOWN = "unknown"


_INTERNET_PATTERNS = [
    r"\b(search|look up|find|browse|google|check online|latest news)\b",
    r"\b(current|today|recent|now|2024|2025|2026)\b",
    r"\b(what happened|who won|weather|stock price|live)\b",
]

_DOC_PATTERNS = [
    r"\b(in the document|in the file|in my pdf|in the report|uploaded)\b",
    r"\b(page \d+|section|chapter|slide|spreadsheet|table)\b",
]

_ADMIN_PATTERNS = [
    r"\b(list sources|show knowledge|delete|clear memory|rollback|snapshot)\b",
]


class IntentRouter:
    """Lightweight rule-based intent classifier."""

    def route(self, message: str) -> Intent:
        lower = message.lower()

        for pat in _ADMIN_PATTERNS:
            if re.search(pat, lower):
                return Intent.ADMIN

        for pat in _DOC_PATTERNS:
            if re.search(pat, lower):
                return Intent.DOCUMENT_QA

        for pat in _INTERNET_PATTERNS:
            if re.search(pat, lower):
                return Intent.INTERNET_SEARCH

        if "?" in message and len(message.split()) > 4:
            return Intent.FACTUAL_QUERY

        return Intent.CHAT
