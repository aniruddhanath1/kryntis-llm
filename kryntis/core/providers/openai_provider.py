"""
OpenAI LLM provider (GPT-4o, GPT-4, GPT-3.5-turbo).

Requires OPENAI_API_KEY environment variable.
"""

from __future__ import annotations

from typing import AsyncIterator

from tenacity import retry, stop_after_attempt, wait_exponential

from kryntis.core.providers.base import (
    BaseLLMProvider, GenerationConfig, LLMResponse, Message
)
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI chat completion provider.

    Supports streaming and non-streaming responses via the
    official openai Python SDK.
    """

    def __init__(self, model: str = _DEFAULT_MODEL, api_key: str | None = None) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ImportError("Install openai: pip install openai") from e

        self._model = model
        self._client = AsyncOpenAI(api_key=api_key)
        log.info("openai_provider_init", model=model)

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    def _build_messages(self, messages: list[Message]) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in messages]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> LLMResponse:
        cfg = config or GenerationConfig()
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=self._build_messages(messages),
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            max_tokens=cfg.max_tokens,
            stop=cfg.stop or None,
            stream=False,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            provider=self.provider_name,
            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
            completion_tokens=response.usage.completion_tokens if response.usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    async def stream_chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        cfg = config or GenerationConfig()
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=self._build_messages(messages),
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            max_tokens=cfg.max_tokens,
            stop=cfg.stop or None,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    async def is_available(self) -> bool:
        try:
            models = await self._client.models.list()
            return any(m.id.startswith("gpt") for m in models.data)
        except Exception as e:
            log.warning("openai_unavailable", error=str(e))
            return False
