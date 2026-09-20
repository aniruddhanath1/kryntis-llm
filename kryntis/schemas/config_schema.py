"""Configuration Pydantic Schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List

class ServiceConfigSchema(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

class ModelConfigSchema(BaseModel):
    backend: str = "local"
    model_path: str = "data/models/checkpoints/final_model.pt"
    model_size: str = "small"
    temperature: float = 0.7
    top_p: float = 0.9
    max_new_tokens: int = 512
