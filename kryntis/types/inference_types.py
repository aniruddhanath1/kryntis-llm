"""Inference Type definitions."""

from typing import TypedDict, List, Optional

class GenerationOptionsDict(TypedDict, total=False):
    max_new_tokens: int
    temperature: float
    top_p: float
    top_k: int
    repetition_penalty: float
