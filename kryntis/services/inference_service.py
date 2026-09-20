"""Inference Service business logic."""

from typing import Dict, Any, Generator
from kryntis.core.inference import InferenceEngine

class InferenceService:
    """Provides high-level generation methods."""
    def __init__(self, engine: InferenceEngine = None) -> None:
        self.engine = engine or InferenceEngine()

    def generate(self, prompt: str, max_new_tokens: int = 512, temperature: float = 0.7) -> str:
        return self.engine.generate(prompt=prompt, max_new_tokens=max_new_tokens, temperature=temperature)

    def stream_generate(self, prompt: str, max_new_tokens: int = 512, temperature: float = 0.7) -> Generator[str, None, None]:
        yield from self.engine.stream_generate(prompt=prompt, max_new_tokens=max_new_tokens, temperature=temperature)
