"""
Prompt Guard — injection detection and safety filtering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_INJECTION_PATTERNS = [
    r"ignore (previous|all|prior|above) instructions",
    r"you are now",
    r"forget everything",
    r"act as (if you are|a|an)",
    r"do anything now",
    r"jailbreak",
    r"disregard (your|all) (training|instructions)",
    r"system prompt",
    r"reveal (your|the) (system|hidden) prompt",
    r"write malware|create a virus|hack into",
    r"<\|.*?\|>",         # Common injection delimiters
    r"\[\[.*?\]\]",       # Another common pattern
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


@dataclass
class GuardResult:
    safe: bool
    reason: str = ""
    matched_pattern: str = ""


class PromptGuard:
    """
    Input safety filter.

    Checks for prompt injection patterns, jailbreak attempts,
    and unsafe content before passing to the LLM.
    """

    def __init__(self, strict: bool = True) -> None:
        self._strict = strict

    def check(self, text: str) -> GuardResult:
        for pattern in _COMPILED:
            if pattern.search(text):
                log.warning("prompt_injection_detected", pattern=pattern.pattern[:50])
                return GuardResult(
                    safe=False,
                    reason="Potential prompt injection detected.",
                    matched_pattern=pattern.pattern,
                )

        if len(text) > 50_000:
            return GuardResult(safe=False, reason="Input too long (>50,000 chars)")

        return GuardResult(safe=True)
