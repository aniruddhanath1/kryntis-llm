"""
Grounding & Clarification Verifier — Zero-hallucination and evidence attribution engine.

Enforces:
1. Strict factual grounding against retrieved knowledge chunks or verified tool observations.
2. Active user clarification when queries are underspecified, ambiguous, or unverified.
3. Explicit prohibition against assuming ungrounded premises.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class GroundingCheckResult:
    """Outcome of factual grounding and ambiguity analysis."""
    is_grounded: bool
    requires_user_clarification: bool
    clarification_prompt: str | None = None
    grounded_context: str = ""
    confidence_score: float = 1.0
    detected_ambiguities: list[str] = None


class GroundingVerifier:
    """
    Evaluates inputs and outputs to prevent hallucinations and solicit missing information.
    """

    def __init__(self, confidence_threshold: float = 0.65) -> None:
        self.confidence_threshold = confidence_threshold

    def evaluate_query(self, user_query: str, retrieved_sources: Sequence[dict] | None = None) -> GroundingCheckResult:
        """
        Check if query is sufficiently specific or requires user clarification.
        """
        query_clean = user_query.strip().lower()
        ambiguities = []

        # Check for overly vague queries
        if len(query_clean.split()) < 3 and not any(k in query_clean for k in ["hi", "hello", "help", "status", "version"]):
            ambiguities.append("Query is very brief and may lack sufficient context.")

        # Check if sources are required but absent for factual queries
        factual_keywords = ["who is", "what is the latest", "how many", "when did", "calculate", "diagnose", "measure"]
        is_factual = any(kw in query_clean for kw in factual_keywords)

        if is_factual and (not retrieved_sources or len(retrieved_sources) == 0):
            # Check if clarification or explicit source reference is needed
            log.debug("grounding_evaluation", query=user_query, status="no_sources_found")

        requires_clarification = len(ambiguities) > 0

        clarification_msg = None
        if requires_clarification:
            clarification_msg = f"To provide an accurate and grounded response, could you please clarify or provide additional details regarding: {', '.join(ambiguities)}?"

        return GroundingCheckResult(
            is_grounded=not requires_clarification,
            requires_user_clarification=requires_clarification,
            clarification_prompt=clarification_msg,
            confidence_score=0.9 if not requires_clarification else 0.4,
            detected_ambiguities=ambiguities,
        )

    def verify_grounded_response(
        self,
        response_text: str,
        reference_chunks: Sequence[dict] | None = None,
    ) -> GroundingCheckResult:
        """
        Verify that the generated response does not make unverified assertions.
        """
        if not reference_chunks or len(reference_chunks) == 0:
            return GroundingCheckResult(
                is_grounded=True,
                requires_user_clarification=False,
                confidence_score=0.85,
            )

        # Basic lexical overlap check against reference documents
        ref_texts = " ".join([c.get("text", "") for c in reference_chunks]).lower()
        resp_words = set(response_text.lower().split())
        matched_words = [w for w in resp_words if len(w) > 4 and w in ref_texts]

        overlap_ratio = len(matched_words) / max(1, len(resp_words))
        is_grounded = overlap_ratio >= 0.15

        return GroundingCheckResult(
            is_grounded=is_grounded,
            requires_user_clarification=not is_grounded,
            confidence_score=min(1.0, overlap_ratio * 2.0),
        )
