"""
Prompt Guard — multi-tier injection detection, semantic normalization, and safety filtering.
"""

from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import dataclass

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

# Zero-width / invisible characters commonly used in obfuscation
_INVISIBLE_CHARS_RE = re.compile(r"[\u200B-\u200D\uFEFF\u00AD\u202A-\u202E]")

_INJECTION_PATTERNS = [
    r"ignore (previous|all|prior|above) instructions",
    r"you are now\b",
    r"forget (everything|all previous)",
    r"act as (if you are|a|an)\b",
    r"do anything now\b",
    r"\bjailbreak\b",
    r"disregard (your|all) (training|instructions)",
    r"system prompt",
    r"reveal (your|the) (system|hidden) prompt",
    r"print (your|the) (system|initial) (message|prompt)",
    r"write malware|create a (virus|trojan|worm)",
    r"exploit (this|the) (system|server|api)",
    r"<\s*\|\s*.*?\s*\|\s*>",                # Control token variations e.g. <|system|>
    r"\[\s*\[\s*.*?\s*\]\s*\]",              # Template tag injection
    r"<!--\s*.*?\s*-->",                      # Hidden HTML comment injection
    r"(?:^|\n)\s*(?:system|developer|assistant|human)\s*:\s*(?:ignore|forget|disregard)",  # Role simulation
    r"\[\/?(?:INST|SYS)\]",                   # Llama-style instruction delimiters
    r"!\[.*?\]\(https?:\/\/[^\s\)]+[\?&](?:q|data|leak|token|secret)=", # Markdown exfiltration
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS]


@dataclass
class GuardResult:
    safe: bool
    reason: str = ""
    matched_pattern: str = ""


def normalize_prompt_text(text: str) -> str:
    """
    Normalize text by stripping invisible zero-width characters,
    normalizing unicode homoglyphs via NFKC, and collapsing redundant whitespace.
    """
    # 1. Strip invisible / directional characters
    cleaned = _INVISIBLE_CHARS_RE.sub("", text)
    # 2. NFKC unicode decomposition and normalization
    cleaned = unicodedata.normalize("NFKC", cleaned)
    return cleaned


def detect_base64_payload(text: str) -> str | None:
    """Inspect embedded base64 blocks to detect obfuscated prompt injection."""
    b64_candidates = re.findall(r"(?:[A-Za-z0-9+/]{4}){8,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?", text)
    for candidate in b64_candidates:
        try:
            decoded = base64.b64decode(candidate).decode("utf-8", errors="ignore")
            for pattern in _COMPILED:
                if pattern.search(decoded):
                    return f"Obfuscated base64 injection payload: {pattern.pattern}"
        except Exception:
            continue
    return None


class PromptGuard:
    """
    Multi-tier input safety filter.

    Normalizes Unicode, checks for direct/indirect prompt injection,
    role-spoofing markers, obfuscated payloads, and length violations.
    """

    def __init__(self, strict: bool = True) -> None:
        self._strict = strict

    def check(self, text: str) -> GuardResult:
        if len(text) > 50_000:
            return GuardResult(safe=False, reason="Input too long (>50,000 chars)")

        normalized = normalize_prompt_text(text)

        # 1. Direct regex rule scanning over normalized text
        for pattern in _COMPILED:
            if pattern.search(normalized):
                log.warning("prompt_injection_detected", pattern=pattern.pattern[:50])
                return GuardResult(
                    safe=False,
                    reason="Potential prompt injection or instruction override detected.",
                    matched_pattern=pattern.pattern,
                )

        # 2. Obfuscated Base64 scan
        b64_detected = detect_base64_payload(normalized)
        if b64_detected:
            log.warning("b64_injection_detected", detail=b64_detected)
            return GuardResult(
                safe=False,
                reason="Obfuscated instruction payload detected.",
                matched_pattern=b64_detected,
            )

        return GuardResult(safe=True)
