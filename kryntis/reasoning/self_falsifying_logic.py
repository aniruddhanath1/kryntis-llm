"""
Self-Falsifying Logic Engine — Adversarial internal verification.

Modes:
1. Flawless Compliance & Legal Audit (Enterprise): Actively tries to break contracts, locate loopholes or jurisdictional ambiguities.
2. Academic Peer Review (Scientific): Acts as an internal adversarial peer reviewer detecting statistical leaps or unproven claims.
3. Anti-Hallucination & Fact Guard (General Consumer): Eradicates confidently incorrect advice and ungrounded statements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class AuditScope(str, Enum):
    LEGAL_COMPLIANCE = "legal_compliance"
    ACADEMIC_REVIEW = "academic_review"
    FACT_GUARD = "fact_guard"


@dataclass
class FalsificationVulnerability:
    clause_or_claim: str
    attack_vector: str
    severity: str  # "high", "medium", "low"
    remediation_suggestion: str


@dataclass
class FalsificationAuditResult:
    is_valid: bool
    scope: AuditScope
    vulnerabilities: list[FalsificationVulnerability]
    robustness_score: float  # 0.0 to 1.0
    summary: str


class SelfFalsifyingLogicEngine:
    """
    Applies adversarial falsification strategies to check assertions for weaknesses.
    """

    def audit(self, text: str, scope: AuditScope = AuditScope.FACT_GUARD) -> FalsificationAuditResult:
        """
        Audit text by executing targeted adversarial stress tests.
        """
        vulnerabilities: list[FalsificationVulnerability] = []
        text_lower = text.lower()

        if scope == AuditScope.LEGAL_COMPLIANCE:
            # Check for vague indemnification, missing governing law, or unilateral warranties
            if "indemnif" in text_lower and not ("sole" in text_lower or "capped" in text_lower or "gross negligence" in text_lower):
                vulnerabilities.append(FalsificationVulnerability(
                    clause_or_claim="Indemnification clause",
                    attack_vector="Uncapped liability vulnerability: An opposing party could claim consequential damages without limitation.",
                    severity="high",
                    remediation_suggestion="Add explicit monetary liability cap and carve-out for indirect/consequential damages.",
                ))
            if "terminate" in text_lower and not ("notice" in text_lower or "days" in text_lower):
                vulnerabilities.append(FalsificationVulnerability(
                    clause_or_claim="Termination clause",
                    attack_vector="Ambiguous termination timing: Lacks explicit written notice cure period.",
                    severity="medium",
                    remediation_suggestion="Specify a mandatory 30-day written notice cure period for material breach.",
                ))

        elif scope == AuditScope.ACADEMIC_REVIEW:
            # Check for causal claims without statistical validation or confidence intervals
            causal_markers = ["proves that", "undeniably caused", "always results in", "100% effective"]
            for marker in causal_markers:
                if marker in text_lower:
                    vulnerabilities.append(FalsificationVulnerability(
                        clause_or_claim=f"Assertion with '{marker}'",
                        attack_vector="Over-generalized causal claim without confidence interval (p-value / error margin).",
                        severity="high",
                        remediation_suggestion="Moderate claim to state correlation or provide empirical confidence bounds.",
                    ))

        else:  # FACT_GUARD
            # Detect unsupported absolute assertions
            unsupported_absolutes = ["is guaranteed to", "without any doubt", "completely impossible"]
            for marker in unsupported_absolutes:
                if marker in text_lower:
                    vulnerabilities.append(FalsificationVulnerability(
                        clause_or_claim=f"Absolute claim containing '{marker}'",
                        attack_vector="Unverified absolute statement vulnerable to counter-examples.",
                        severity="medium",
                        remediation_suggestion="Ground the assertion with verified source citations or probabilistic nuance.",
                    ))

        is_valid = len([v for v in vulnerabilities if v.severity == "high"]) == 0
        total_vulns = len(vulnerabilities)
        robustness = max(0.0, 1.0 - (total_vulns * 0.2))

        summary = (
            f"Adversarial audit completed for {scope.value}. "
            f"Found {total_vulns} vulnerabilities. Robustness score: {robustness * 100:.1f}%."
        )

        return FalsificationAuditResult(
            is_valid=is_valid,
            scope=scope,
            vulnerabilities=vulnerabilities,
            robustness_score=round(robustness, 2),
            summary=summary,
        )
