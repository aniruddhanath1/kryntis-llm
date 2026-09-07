"""
Model Manager — provider registry and lifecycle manager.
Default provider is Local (100% self-hosted, no API key needed).
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

if TYPE_CHECKING:
    from kryntis.core.providers.base import BaseLLMProvider

log = get_logger(__name__)


def _build_provider(provider_name: str, cfg) -> "BaseLLMProvider":
    """Instantiate a provider from its name string."""
    provider_name = provider_name.lower()

    if provider_name == "local":
        from kryntis.core.providers.local_provider import LocalProvider
        return LocalProvider(
            model_path=cfg.model.path,
            n_ctx=cfg.model.context_length,
            n_threads=cfg.model.threads,
            n_gpu_layers=cfg.model.gpu_layers,
        )
    else:
        log.warning("unsupported_provider_fallback_to_local", requested=provider_name)
        from kryntis.core.providers.local_provider import LocalProvider
        return LocalProvider(
            model_path=cfg.model.path,
            n_ctx=cfg.model.context_length,
            n_threads=cfg.model.threads,
            n_gpu_layers=cfg.model.gpu_layers,
        )


class ModelManager:
    """
    Manages LLM provider instances and their lifecycle.
    100% self-hosted local model provider.
    """

    def __init__(self, primary: str = "local", fallback: str | None = None) -> None:
        cfg = get_config()
        self._cfg = cfg
        self._primary_name = "local"
        self._primary: BaseLLMProvider | None = None
        log.info("model_manager_init", primary="local")

    @classmethod
    def from_config(cls) -> "ModelManager":
        return cls(primary="local", fallback=None)

    def _get_or_build_primary(self) -> "BaseLLMProvider":
        if self._primary is None:
            self._primary = _build_provider(self._primary_name, self._cfg)
        return self._primary

    async def get_provider(self) -> "BaseLLMProvider":
        primary = self._get_or_build_primary()
        return primary

    async def health_check(self) -> dict:
        primary = self._get_or_build_primary()
        primary_ok = await primary.is_available()
        return {
            "primary": {
                "provider": "local",
                "model": primary.model_name,
                "available": primary_ok,
            }
        }

    def unload_local(self) -> None:
        from kryntis.core.providers.local_provider import LocalProvider
        if isinstance(self._primary, LocalProvider):
            self._primary.unload()
