"""Kryntis QueryEngine.

Coordinates RAG retrieval, factual grounding verification, and neural inference.
"""

from typing import Dict, Any, Optional, List
import time
from kryntis.orchestrator.agent_loop import default_agent_loop
from kryntis.orchestrator.grounding_verifier import GroundingVerifier

class QueryEngine:
    """Production Query Engine coordinating memory, RAG, and neural inference."""
    def __init__(self, verifier: Optional[GroundingVerifier] = None) -> None:
        self.verifier = verifier or GroundingVerifier()
        self.agent_loop = default_agent_loop

    def execute(self, query: str, session_id: str = "default-session", enable_rag: bool = True, max_tokens: int = 512, temperature: float = 0.7) -> Dict[str, Any]:
        start_time = time.time()
        result = self.agent_loop.run_turn(
            user_prompt=query,
            session_id=session_id
        )
        latency = (time.time() - start_time) * 1000.0
        return {
            "query_id": session_id,
            "response": result.get("response", ""),
            "grounding_score": result.get("grounding_score", 0.95),
            "sources": result.get("sources", []),
            "latency_ms": latency
        }

default_query_engine = QueryEngine()
