"""
Evaluation framework — automated RAG and response quality assessment.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class EvalCase:
    """A single evaluation test case."""
    case_id: str
    query: str
    expected_answer: str
    expected_sources: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result for one evaluation case."""
    case_id: str
    query: str
    actual_answer: str
    expected_answer: str
    retrieved_chunks: int
    latency_ms: float
    exact_match: bool
    keyword_overlap: float
    passed: bool


class RAGEvaluator:
    """
    Evaluates RAG pipeline quality.

    Metrics:
    - Exact match (for factual questions)
    - Keyword overlap (F1-like)
    - Retrieval success rate
    - Average latency
    """

    def __init__(self) -> None:
        self._results: list[EvalResult] = []

    async def evaluate(
        self, cases: list[EvalCase], orchestrator: Any
    ) -> dict:
        """Run evaluation suite."""
        from kryntis.orchestrator.agent_loop import OrchestratorRequest
        self._results.clear()

        for case in cases:
            t0 = time.monotonic()
            req = OrchestratorRequest(
                session_id=f"eval-{case.case_id}",
                user_message=case.query,
                enable_internet=False,  # Deterministic eval
            )
            resp = await orchestrator.chat(req)
            latency_ms = (time.monotonic() - t0) * 1000

            overlap = self._keyword_overlap(resp.response, case.expected_answer)
            exact = case.expected_answer.lower() in resp.response.lower()

            result = EvalResult(
                case_id=case.case_id,
                query=case.query,
                actual_answer=resp.response,
                expected_answer=case.expected_answer,
                retrieved_chunks=resp.rag_chunks_used,
                latency_ms=round(latency_ms, 1),
                exact_match=exact,
                keyword_overlap=overlap,
                passed=overlap > 0.4 or exact,
            )
            self._results.append(result)
            log.info("eval_case", case_id=case.case_id, passed=result.passed, overlap=overlap)

        return self._summary()

    def _keyword_overlap(self, answer: str, expected: str) -> float:
        a_words = set(answer.lower().split())
        e_words = set(expected.lower().split())
        if not e_words:
            return 0.0
        return len(a_words & e_words) / len(e_words)

    def _summary(self) -> dict:
        if not self._results:
            return {}
        passed = sum(1 for r in self._results if r.passed)
        avg_latency = sum(r.latency_ms for r in self._results) / len(self._results)
        avg_overlap = sum(r.keyword_overlap for r in self._results) / len(self._results)
        return {
            "total": len(self._results),
            "passed": passed,
            "pass_rate": round(passed / len(self._results), 3),
            "avg_latency_ms": round(avg_latency, 1),
            "avg_keyword_overlap": round(avg_overlap, 3),
        }
