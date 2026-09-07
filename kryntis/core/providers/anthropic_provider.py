"""
Anthropic LLM provider (Claude 3 Opus / Sonnet / Haiku).

Requires ANTHROPIC_API_KEY environment variable.
"""

from __future__ import annotations

from typing import AsyncIterator

from tenacity import retry, stop_after_attempt, wait_exponential

from kryntis.core.providers.base import (
    BaseLLMProvider, GenerationConfig, LLMResponse, Message
)
from kryntis.utils.logging import get_logger

log = get_logger(__name__)

_DEFAULT_MODEL = "claude-3-5-haiku-latest"


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude provider.

    Splits the message list into an optional system prompt
    and conversation messages as the Anthropic API requires.
    """

    def __init__(self, model: str = _DEFAULT_MODEL, api_key: str | None = None) -> None:
        try:
            import anthropic as _anthropic
            self._anthropic = _anthropic
        except ImportError as e:
            raise ImportError("Install anthropic: pip install anthropic") from e

        self._model = model
        self._client = _anthropic.AsyncAnthropic(api_key=api_key)
        log.info("anthropic_provider_init", model=model)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    def _split_messages(
        self, messages: list[Message]
    ) -> tuple[str, list[dict]]:
        """Separate system message and build Anthropic message list."""
        system = ""
        conv: list[dict] = []
        for m in messages:
            if m.role == "system":
                system = m.content
            else:
                conv.append({"role": m.role, "content": m.content})
        return system, conv

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> LLMResponse:
        cfg = config or GenerationConfig()
        system, conv = self._split_messages(messages)

        kwargs: dict = dict(
            model=self._model,
            messages=conv,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
        )
        if system:
            kwargs["system"] = system
        if cfg.stop:
            kwargs["stop_sequences"] = cfg.stop

        response = await self._client.messages.create(**kwargs)
        content = response.content[0].text if response.content else ""
        return LLMResponse(
            content=content,
            model=self._model,
            provider=self.provider_name,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason or "stop",
        )

    async def stream_chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        cfg = config or GenerationConfig()
        system, conv = self._split_messages(messages)

        kwargs: dict = dict(
            model=self._model,
            messages=conv,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
        )
        if system:
            kwargs["system"] = system

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def is_available(self) -> bool:
        try:
            # Cheapest possible call to verify connectivity
            await self._client.messages.create(
                model=self._model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True
        except Exception as e:
            log.warning("anthropic_unavailable", error=str(e))
            return False
