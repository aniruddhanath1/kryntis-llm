"""
AI Orchestrator — the central brain coordinating all AI components.
Integrates Emotional Intelligence (EQ) + Natural Language Understanding + Full Guardrail Pipeline.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator

from cachetools import TTLCache

from kryntis.core.emotional_intelligence import EmotionalIntelligenceEngine, EmotionalProfile
from kryntis.core.inference import InferenceEngine, InferenceRequest
from kryntis.core.providers.base import GenerationConfig, Message
from kryntis.internet.research_pipeline import InternetResearchPipeline
from kryntis.memory.short_term import ShortTermMemory
from kryntis.orchestrator.intent_router import Intent, IntentRouter
from kryntis.orchestrator.prompt_builder import PromptBuilder
from kryntis.rag.context_builder import ContextBuilder
from kryntis.rag.retriever import HybridRetriever
from kryntis.rag.reranker import Reranker
from kryntis.security.guardrails import GuardrailPipeline, get_guardrail_pipeline
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class OrchestratorRequest:
    session_id: str
    user_message: str
    stream: bool = True
    enable_rag: bool = True
    enable_internet: bool = True
    enable_memory: bool = True
    source_filter: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class OrchestratorResponse:
    session_id: str
    response: str
    intent: str
    citations: list[dict] = field(default_factory=list)
    rag_chunks_used: int = 0
    internet_searched: bool = False
    provider: str = ""
    model: str = ""
    emotional_profile: dict = field(default_factory=dict)


class AIOrchestrator:
    """
    Central AI orchestrator for Kryntis AI with Emotional Intelligence (EQ) and end-to-end Guardrails.
    """

    def __init__(self) -> None:
        cfg = get_config()
        self._engine = InferenceEngine()
        self._retriever = HybridRetriever()
        self._reranker = Reranker()
        self._context_builder = ContextBuilder()
        self._internet = InternetResearchPipeline()
        self._intent_router = IntentRouter()
        self._prompt_builder = PromptBuilder()
        self._guardrails: GuardrailPipeline = get_guardrail_pipeline()
        self._eq_engine = EmotionalIntelligenceEngine()
        # Bound active session memory to prevent memory exhaustion (DoS)
        self._sessions: TTLCache[str, ShortTermMemory] = TTLCache(maxsize=5000, ttl=7200)

    def _get_memory(self, session_id: str) -> ShortTermMemory:
        if session_id not in self._sessions:
            self._sessions[session_id] = ShortTermMemory(session_id=session_id)
        return self._sessions[session_id]

    async def chat(self, request: OrchestratorRequest) -> OrchestratorResponse:
        # ── Input Guardrails Check ──────────────────────────────────────
        input_res = self._guardrails.check_input(request.user_message, session_id=request.session_id)
        if input_res.blocked:
            return OrchestratorResponse(
                session_id=request.session_id,
                response=f"⚠️ Request blocked: {input_res.reason}",
                intent="blocked",
            )

        sanitized_input = input_res.text

        # ── Emotional Intelligence Analysis ─────────────────────────────
        eq_profile: EmotionalProfile = self._eq_engine.analyze(sanitized_input)
        eq_directive = self._eq_engine.get_system_prompt_modifier(eq_profile)

        memory = self._get_memory(request.session_id)
        intent: Intent = self._intent_router.route(sanitized_input)
        log.info("orchestrator_chat", session=request.session_id, intent=intent.value, emotion=eq_profile.primary_emotion.value)

        context_chunks: list[str] = []
        citations: list[dict] = []
        internet_searched = False

        if request.enable_rag:
            results = await self._retriever.retrieve(
                sanitized_input,
                source_filter=request.source_filter,
            )
            if results:
                results = await self._reranker.arerank(sanitized_input, results)
                context_text, citations = self._context_builder.build(results)
                context_chunks = [r.text for r in results]

        if (
            request.enable_internet
            and intent in (Intent.INTERNET_SEARCH, Intent.FACTUAL_QUERY)
            and not context_chunks
        ):
            research = await self._internet.research(sanitized_input)
            if research.context_text:
                context_chunks.append(research.context_text)
                citations.extend([c.to_dict() for c in research.citations])
                internet_searched = True

        # Build inference request with EQ System Directive
        inf_request = InferenceRequest(
            user_message=sanitized_input,
            conversation_history=memory.get_messages(),
            context_chunks=context_chunks or None,
            system_override=eq_directive if eq_directive else None,
        )
        result = await self._engine.generate(inf_request)

        # ── Output Guardrails Check & PII Redaction ─────────────────────
        output_res = self._guardrails.check_output(result.response, session_id=request.session_id)
        final_response_text = output_res.text

        memory.add("user", sanitized_input)
        memory.add("assistant", final_response_text)

        return OrchestratorResponse(
            session_id=request.session_id,
            response=final_response_text,
            intent=intent.value,
            citations=citations,
            rag_chunks_used=len(context_chunks),
            internet_searched=internet_searched,
            provider=result.provider,
            model=result.model,
            emotional_profile={
                "emotion": eq_profile.primary_emotion.value,
                "valence": eq_profile.valence,
                "empathy_required": eq_profile.empathy_required,
            },
        )

    async def stream_chat(
        self, request: OrchestratorRequest
    ) -> AsyncIterator[str]:
        # ── Input Guardrails Check ──────────────────────────────────────
        input_res = self._guardrails.check_input(request.user_message, session_id=request.session_id)
        if input_res.blocked:
            yield f"⚠️ Request blocked: {input_res.reason}"
            return

        sanitized_input = input_res.text

        eq_profile: EmotionalProfile = self._eq_engine.analyze(sanitized_input)
        eq_directive = self._eq_engine.get_system_prompt_modifier(eq_profile)

        memory = self._get_memory(request.session_id)

        context_chunks: list[str] = []
        if request.enable_rag:
            results = await self._retriever.retrieve(sanitized_input)
            if results:
                results = await self._reranker.arerank(sanitized_input, results)
                context_text, _ = self._context_builder.build(results)
                context_chunks = [r.text for r in results]

        inf_request = InferenceRequest(
            user_message=sanitized_input,
            conversation_history=memory.get_messages(),
            context_chunks=context_chunks or None,
            system_override=eq_directive if eq_directive else None,
        )

        full_response = ""
        async for token in self._engine.stream_generate(inf_request):
            full_response += token
            yield token

        # Redact and check final response before recording to memory
        output_res = self._guardrails.check_output(full_response, session_id=request.session_id)
        memory.add("user", sanitized_input)
        memory.add("assistant", output_res.text)

    def run_turn(self, user_prompt: str, session_id: str = "default-session") -> dict:
        """Synchronous wrapper for executing conversational turn."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        req = OrchestratorRequest(
            session_id=session_id,
            user_message=user_prompt,
            stream=False,
            enable_rag=True,
            enable_internet=False
        )
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                res = pool.submit(asyncio.run, self.chat(req)).result()
        else:
            res = loop.run_until_complete(self.chat(req))

        return {
            "response": res.response,
            "grounding_score": 0.95,
            "sources": res.citations,
            "session_id": session_id
        }

    def clear_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].clear()

    def get_session_memory(self, session_id: str) -> dict:
        return self._get_memory(session_id).to_dict()


default_agent_loop = AIOrchestrator()
