"""
Centralised configuration loader.

All settings are loaded from:
1. config/default.yaml  (defaults)
2. .env / environment variables (overrides)

Settings are accessible as a frozen, typed Config object.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Load .env first so env vars override YAML
load_dotenv()

_ROOT = Path(__file__).resolve().parents[2]  # repo root


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file; return empty dict if not found."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _flatten(d: dict, prefix: str = "", sep: str = "__") -> dict[str, str]:
    """Recursively flatten a nested dict to `KEY__SUBKEY = value` pairs."""
    out: dict[str, str] = {}
    for k, v in d.items():
        full = f"{prefix}{sep}{k}".upper() if prefix else k.upper()
        if isinstance(v, dict):
            out.update(_flatten(v, full, sep))
        else:
            out[full] = str(v)
    return out


# ─────────────────────────────────────────────
# Typed settings (pydantic-settings)
# ─────────────────────────────────────────────

class ServiceSettings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "INFO"
    internal_key_header: str = "X-Kryntis-Key"
    cors_origins: list[str] = ["*"]

    class Config:
        env_prefix = "KRYNTIS_SERVICE_"


class ModelSettings(BaseSettings):
    backend: str = "llama_cpp"
    path: str = "data/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    context_length: int = 4096
    max_new_tokens: int = 1024
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repeat_penalty: float = 1.1
    threads: int = 4
    gpu_layers: int = 0
    idle_unload_seconds: int = 300

    class Config:
        env_prefix = "KRYNTIS_MODEL_"


class RAGSettings(BaseSettings):
    embedder_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedder_batch_size: int = 32
    dense_top_k: int = 20
    rerank_top_k: int = 5
    bm25_weight: float = 0.3
    dense_weight: float = 0.7
    min_score_threshold: float = 0.3

    class Config:
        env_prefix = "KRYNTIS_RAG_"


class ChunkingSettings(BaseSettings):
    default_chunk_size: int = 512
    default_chunk_overlap: int = 64
    min_chunk_size: int = 50
    max_chunk_size: int = 1024
    include_metadata: bool = True
    hierarchical: bool = True

    class Config:
        env_prefix = "KRYNTIS_CHUNKING_"


class KnowledgeSettings(BaseSettings):
    vector_backend: str = "chroma"
    chroma_path: str = "data/knowledge/chroma"
    sqlite_path: str = "data/knowledge/kryntis.db"
    collection_name: str = "kryntis_knowledge"

    class Config:
        env_prefix = "KRYNTIS_KNOWLEDGE_"


class MemorySettings(BaseSettings):
    short_term_max_turns: int = 20
    short_term_max_tokens: int = 2048
    long_term_collection: str = "kryntis_memory"
    episodic_collection: str = "kryntis_episodes"
    consolidation_interval_seconds: int = 3600
    consolidation_similarity_threshold: float = 0.92

    class Config:
        env_prefix = "KRYNTIS_MEMORY_"


class IngestionSettings(BaseSettings):
    max_files_per_batch: int = 10
    max_file_size_bytes: int = 104_857_600  # 100 MB
    upload_dir: str = "data/uploads"
    streaming_chunk_bytes: int = 8192

    class Config:
        env_prefix = "KRYNTIS_INGESTION_"


class InternetSettings(BaseSettings):
    enabled: bool = True
    search_engine: str = "duckduckgo"
    max_results: int = 10
    max_content_length: int = 50_000
    request_timeout: int = 15
    max_concurrent_fetches: int = 3
    min_domain_trust_score: float = 0.3
    min_confidence_to_learn: float = 0.75
    respect_robots_txt: bool = True
    blocked_domains: list[str] = []
    brave_search_api_key: str = Field(default="", alias="BRAVE_SEARCH_API_KEY")

    class Config:
        env_prefix = "KRYNTIS_INTERNET_"
        populate_by_name = True


class LearningSettings(BaseSettings):
    enabled: bool = True
    confidence_threshold: float = 0.75
    min_confidence: float = 0.5
    auto_approve_above_confidence: float = 0.85
    require_human_approval: bool = False
    max_items_per_batch: int = 100
    snapshot_dir: str = "data/knowledge/snapshots"
    never_learn_from_self: bool = True

    class Config:
        env_prefix = "KRYNTIS_LEARNING_"


class SecuritySettings(BaseSettings):
    prompt_injection_detection: bool = True
    max_prompt_length: int = 8192
    audit_log_path: str = "data/logs/audit.jsonl"
    rate_limit_requests_per_minute: int = 60
    internal_key: str = Field(default="dev-key", alias="KRYNTIS_INTERNAL_KEY")
    # Guardrail switches
    block_toxic_input: bool = True
    strip_pii_from_input: bool = False
    block_harmful_output: bool = True
    redact_pii_from_output: bool = True
    flag_uncertain_output: bool = True

    class Config:
        env_prefix = "KRYNTIS_SECURITY_"
        populate_by_name = True


class EvaluationSettings(BaseSettings):
    hallucination_check: bool = True
    confidence_scoring: bool = True
    min_confidence_to_respond: float = 0.2

    class Config:
        env_prefix = "KRYNTIS_EVALUATION_"


class CacheSettings(BaseSettings):
    embedding_cache_size: int = 1000
    search_cache_size: int = 200
    search_cache_ttl_seconds: int = 300
    response_cache_size: int = 100
    response_cache_ttl_seconds: int = 600

    class Config:
        env_prefix = "KRYNTIS_CACHE_"


class MCPSettings(BaseSettings):
    enabled: bool = True
    # Comma-separated list of allowed client origins (empty = trust auth header only)
    allowed_origins: list[str] = []

    class Config:
        env_prefix = "KRYNTIS_MCP_"


class A2ASettings(BaseSettings):
    enabled: bool = True
    # Base URL advertised in the Agent Card; set to the public-facing URL in prod
    public_base_url: str = "http://localhost:8000"

    class Config:
        env_prefix = "KRYNTIS_A2A_"


class KryntisConfig:
    """
    Top-level configuration object.

    Access sub-configs via attributes:
        cfg = get_config()
        cfg.model.path
        cfg.rag.dense_top_k
    """

    def __init__(self) -> None:
        self.root: Path = _ROOT
        self.service = ServiceSettings()
        self.model = ModelSettings()
        self.rag = RAGSettings()
        self.chunking = ChunkingSettings()
        self.knowledge = KnowledgeSettings()
        self.memory = MemorySettings()
        self.ingestion = IngestionSettings()
        self.internet = InternetSettings()
        self.learning = LearningSettings()
        self.security = SecuritySettings()
        self.evaluation = EvaluationSettings()
        self.cache = CacheSettings()
        self.mcp = MCPSettings()
        self.a2a = A2ASettings()

    def abs_path(self, relative: str) -> Path:
        """Resolve a path relative to the repo root."""
        return self.root / relative


@lru_cache(maxsize=1)
def get_config() -> KryntisConfig:
    """Return the singleton config instance."""
    return KryntisConfig()
