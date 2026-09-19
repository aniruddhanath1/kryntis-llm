"""
Dynamic Privacy Masking — Zero-leak latent space, double-blind research, and PII anonymization.

Modes:
- Enterprise Security & Privacy (Zero-Leak Data Processing): Masks financial figures, M&A deals, proprietary secrets.
- Scientific Reasoning (Double-Blind Research Safety): Masks clinical trial records, patient IDs, proprietary formulas.
- General Consumer Chat (Everyday Privacy Safeguard): Sanitizes credit cards, phone numbers, home addresses, personal rants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class PrivacyScope(str, Enum):
    ENTERPRISE = "enterprise"
    SCIENTIFIC = "scientific"
    CONSUMER = "consumer"
    ALL = "all"


@dataclass
class MaskingResult:
    original_text: str
    masked_text: str
    redactions_count: int
    entity_map: dict[str, str] = field(default_factory=dict)
    scope: PrivacyScope = PrivacyScope.ALL


class DynamicPrivacyMasker:
    """
    Sanitizes sensitive information before processing or persistence.
    Supports two-way de-anonymization via entity mapping.
    """

    def __init__(self, default_scope: PrivacyScope = PrivacyScope.ALL) -> None:
        self.default_scope = default_scope

        # Consumer PII patterns
        self._credit_card_re = re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")
        self._email_re = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        self._phone_re = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
        self._ssn_re = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
        self._address_re = re.compile(r"\b\d{1,5}\s+([A-Za-z0-9.\s]+)\s+(Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Way|Lane|Ln)\b", re.IGNORECASE)

        # Enterprise patterns
        self._financial_deal_re = re.compile(r"\b(?:\$|USD|EUR|GBP|₹)\s?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:million|billion|trillion|M|B|k)?\b", re.IGNORECASE)
        self._ma_keyword_re = re.compile(r"\b(Project\s+[A-Z][a-z]+|merger\s+with\s+[A-Z][a-zA-Z]+|acquisition\s+target\s+[A-Z][a-zA-Z]+)\b")
        self._api_key_re = re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16})\b")

        # Scientific & Healthcare patterns
        self._patient_id_re = re.compile(r"\b(?:MRN|PATIENT[-_]?ID|DOB|SUBJECT[-_]?\d+)\s*[:#]?\s*[A-Za-z0-9-]+\b", re.IGNORECASE)
        self._chemical_formula_re = re.compile(r"\b(?:[A-Z][a-z]?\d*){3,}\s*(?:proprietary|compound|inhibitor)\b", re.IGNORECASE)

    def mask(self, text: str, scope: PrivacyScope | None = None) -> MaskingResult:
        """
        Mask sensitive entities according to target scope.
        """
        active_scope = scope or self.default_scope
        masked = text
        entity_map: dict[str, str] = {}
        counter = 1

        def replace_match(pattern: re.Pattern, tag_prefix: str, content: str) -> str:
            nonlocal counter
            def _repl(m: re.Match) -> str:
                nonlocal counter
                val = m.group(0)
                placeholder = f"[REDACTED_{tag_prefix}_{counter}]"
                entity_map[placeholder] = val
                counter += 1
                return placeholder
            return pattern.sub(_repl, content)

        # 1. Consumer Scope
        if active_scope in (PrivacyScope.CONSUMER, PrivacyScope.ALL):
            masked = replace_match(self._credit_card_re, "CREDIT_CARD", masked)
            masked = replace_match(self._ssn_re, "SSN", masked)
            masked = replace_match(self._email_re, "EMAIL", masked)
            masked = replace_match(self._phone_re, "PHONE", masked)
            masked = replace_match(self._address_re, "ADDRESS", masked)

        # 2. Enterprise Scope
        if active_scope in (PrivacyScope.ENTERPRISE, PrivacyScope.ALL):
            masked = replace_match(self._api_key_re, "SECRET_KEY", masked)
            masked = replace_match(self._financial_deal_re, "FINANCIAL_VAL", masked)
            masked = replace_match(self._ma_keyword_re, "CONFIDENTIAL_DEAL", masked)

        # 3. Scientific Scope
        if active_scope in (PrivacyScope.SCIENTIFIC, PrivacyScope.ALL):
            masked = replace_match(self._patient_id_re, "PATIENT_RECORD", masked)
            masked = replace_match(self._chemical_formula_re, "CHEMICAL_FORMULA", masked)

        return MaskingResult(
            original_text=text,
            masked_text=masked,
            redactions_count=len(entity_map),
            entity_map=entity_map,
            scope=active_scope,
        )

    def unmask(self, masked_text: str, entity_map: dict[str, str]) -> str:
        """Restore redacted placeholders to original content."""
        restored = masked_text
        for placeholder, original in entity_map.items():
            restored = restored.replace(placeholder, original)
        return restored
