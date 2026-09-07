"""
AI Orchestrator — the central brain coordinating all AI components.
Integrates Emotional Intelligence (EQ) + Natural Language Understanding.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncIterator

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
from kryntis.security.prompt_guard import PromptGuard
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
    Central AI orchestrator for Kryntis AI with Emotional Intelligence (EQ).
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
        self._prompt_guard = PromptGuard()
        self._eq_engine = EmotionalIntelligenceEngine()
        self._sessions: dict[str, ShortTermMemory] = {}

    def _get_memory(self, session_id: str) -> ShortTermMemory:
        if session_id not in self._sessions:
            self._sessions[session_id] = ShortTermMemory(session_id=session_id)
        return self._sessions[session_id]

    async def chat(self, request: OrchestratorRequest) -> OrchestratorResponse:
        guard_result = self._prompt_guard.check(request.user_message)
        if not guard_result.safe:
            return OrchestratorResponse(
                session_id=request.session_id,
                response=f"⚠️ Request blocked: {guard_result.reason}",
                intent="blocked",
            )

        # ── Emotional Intelligence Analysis ──────────────────────────────────
        eq_profile: EmotionalProfile = self._eq_engine.analyze(request.user_message)
        eq_directive = self._eq_engine.get_system_prompt_modifier(eq_profile)

        memory = self._get_memory(request.session_id)
        intent: Intent = self._intent_router.route(request.user_message)
        log.info("orchestrator_chat", session=request.session_id, intent=intent.value, emotion=eq_profile.primary_emotion.value)

        context_chunks: list[str] = []
        citations: list[dict] = []
        internet_searched = False

        if request.enable_rag:
            results = await self._retriever.retrieve(
                request.user_message,
                source_filter=request.source_filter,
            )
            if results:
                results = await self._reranker.arerank(request.user_message, results)
                context_text, citations = self._context_builder.build(results)
                context_chunks = [r.text for r in results]

        if (
            request.enable_internet
            and intent in (Intent.INTERNET_SEARCH, Intent.FACTUAL_QUERY)
            and not context_chunks
        ):
            research = await self._internet.research(request.user_message)
            if research.context_text:
                context_chunks.append(research.context_text)
                citations.extend([c.to_dict() for c in research.citations])
                internet_searched = True

        # Build inference request with EQ System Directive
        inf_request = InferenceRequest(
            user_message=request.user_message,
            conversation_history=memory.get_messages(),
            context_chunks=context_chunks or None,
            system_override=eq_directive if eq_directive else None,
        )
        result = await self._engine.generate(inf_request)

        memory.add("user", request.user_message)
        memory.add("assistant", result.response)

        return OrchestratorResponse(
            session_id=request.session_id,
            response=result.response,
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
        guard_result = self._prompt_guard.check(request.user_message)
        if not guard_result.safe:
            yield f"⚠️ Request blocked: {guard_result.reason}"
            return

        eq_profile: EmotionalProfile = self._eq_engine.analyze(request.user_message)
        eq_directive = self._eq_engine.get_system_prompt_modifier(eq_profile)

        memory = self._get_memory(request.session_id)

        context_chunks: list[str] = []
        if request.enable_rag:
            results = await self._retriever.retrieve(request.user_message)
            if results:
                results = await self._reranker.arerank(request.user_message, results)
                context_text, _ = self._context_builder.build(results)
                context_chunks = [r.text for r in results]

        inf_request = InferenceRequest(
            user_message=request.user_message,
            conversation_history=memory.get_messages(),
            context_chunks=context_chunks or None,
            system_override=eq_directive if eq_directive else None,
        )

        full_response = ""
        async for token in self._engine.stream_generate(inf_request):
            full_response += token
            yield token

        memory.add("user", request.user_message)
        memory.add("assistant", full_response)

    def clear_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].clear()

    def get_session_memory(self, session_id: str) -> dict:
        return self._get_memory(session_id).to_dict()
