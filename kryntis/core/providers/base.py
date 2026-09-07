"""
Abstract base class for LLM provider backends.

All providers must implement this interface so the rest of the
system is completely decoupled from the underlying model API.

Supported providers (configured via KRYNTIS_LLM_PROVIDER):
  - openai      → GPT-4o, GPT-4, GPT-3.5-turbo
  - anthropic   → Claude 3 Opus/Sonnet/Haiku
  - local       → llama-cpp-python (GGUF quantized models)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class Message:
    """A single conversation message."""
    role: str          # "system" | "user" | "assistant"
    content: str


@dataclass
class GenerationConfig:
    """Parameters that control generation."""
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 1024
    stop: list[str] = field(default_factory=list)
    stream: bool = True


@dataclass
class LLMResponse:
    """A completed LLM response."""
    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = "stop"


class BaseLLMProvider(ABC):
    """
    Abstract LLM provider interface.

    Every concrete provider must implement:
      - chat()         → non-streaming response
      - stream_chat()  → async token generator
      - is_available() → health check
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier being used."""
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> LLMResponse:
        """
        Send a chat request and return the full response.

        Args:
            messages: Conversation history in order.
            config: Optional generation parameters.

        Returns:
            LLMResponse with content and usage stats.
        """
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[Message],
        config: GenerationConfig | None = None,
    ) -> AsyncIterator[str]:
        """
        Send a chat request and stream tokens as they arrive.

        Args:
            messages: Conversation history in order.
            config: Optional generation parameters.

        Yields:
            Token strings as they are generated.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Return True if this provider is reachable and configured."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name})"
