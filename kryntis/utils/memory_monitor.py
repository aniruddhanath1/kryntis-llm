"""
RAM and system memory monitoring utilities.

Provides real-time memory usage tracking and alerts when approaching
the configured limit, enabling components to make decisions about
model loading, cache eviction, and streaming vs. full-load strategies.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

import psutil

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

# Alert thresholds
_WARN_THRESHOLD_PCT = 75.0
_CRITICAL_THRESHOLD_PCT = 88.0


@dataclass(frozen=True)
class MemorySnapshot:
    """Point-in-time system memory statistics."""

    total_mb: float
    available_mb: float
    used_mb: float
    percent_used: float
    process_rss_mb: float  # This process's resident set size

    @property
    def free_mb(self) -> float:
        return self.available_mb

    @property
    def is_warning(self) -> bool:
        return self.percent_used >= _WARN_THRESHOLD_PCT

    @property
    def is_critical(self) -> bool:
        return self.percent_used >= _CRITICAL_THRESHOLD_PCT

    def __str__(self) -> str:
        return (
            f"RAM: {self.used_mb:.0f}/{self.total_mb:.0f} MB "
            f"({self.percent_used:.1f}%) — process RSS: {self.process_rss_mb:.0f} MB"
        )


def snapshot() -> MemorySnapshot:
    """Take a current memory snapshot."""
    vm = psutil.virtual_memory()
    proc = psutil.Process(os.getpid())
    rss = proc.memory_info().rss / (1024 * 1024)
    return MemorySnapshot(
        total_mb=vm.total / (1024 * 1024),
        available_mb=vm.available / (1024 * 1024),
        used_mb=vm.used / (1024 * 1024),
        percent_used=vm.percent,
        process_rss_mb=rss,
    )


def log_memory(label: str = "") -> MemorySnapshot:
    """Log current memory usage and return snapshot."""
    snap = snapshot()
    level = "warning" if snap.is_warning else "info"
    getattr(log, level)(
        "memory_usage",
        label=label,
        total_mb=round(snap.total_mb, 1),
        used_mb=round(snap.used_mb, 1),
        free_mb=round(snap.free_mb, 1),
        percent=round(snap.percent_used, 1),
        process_rss_mb=round(snap.process_rss_mb, 1),
    )
    return snap


def assert_memory_available(required_mb: float, label: str = "") -> None:
    """
    Raise MemoryError if insufficient RAM is available.

    Args:
        required_mb: Minimum free RAM needed in megabytes.
        label: Context label for the log message.
    """
    snap = snapshot()
    if snap.free_mb < required_mb:
        msg = (
            f"Insufficient RAM for '{label}': need {required_mb:.0f} MB, "
            f"only {snap.free_mb:.0f} MB available."
        )
        log.error("insufficient_memory", label=label, needed_mb=required_mb, free_mb=snap.free_mb)
        raise MemoryError(msg)


def can_load(required_mb: float, safety_margin_mb: float = 512.0) -> bool:
    """Return True if enough RAM exists to safely load something of `required_mb`."""
    snap = snapshot()
    return snap.free_mb >= (required_mb + safety_margin_mb)
