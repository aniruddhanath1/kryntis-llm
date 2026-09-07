"""
Structured logging setup using structlog.

Usage:
    from kryntis.utils.logging import get_logger
    log = get_logger(__name__)
    log.info("model_loaded", path="data/models/tinyllama.gguf", size_mb=680)
"""

from __future__ import annotations

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

import structlog
import yaml


def _ensure_log_dir(log_path: str) -> None:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)


def setup_logging(log_level: str = "INFO", config_path: str | None = None) -> None:
    """
    Configure structlog + stdlib logging.

    Call once at application startup.
    """
    _ensure_log_dir("data/logs/kryntis.log")

    if config_path and Path(config_path).exists():
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
        logging.config.dictConfig(cfg)
    else:
        # Minimal fallback
        logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            level=getattr(logging, log_level.upper(), logging.INFO),
            stream=sys.stdout,
        )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a named structlog logger."""
    return structlog.get_logger(name)
