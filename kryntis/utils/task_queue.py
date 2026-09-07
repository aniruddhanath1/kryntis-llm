"""
Resource-Aware Task Queue & Memory Safety Guard.

Ensures strict compliance with 8 GB RAM constraints:
- Maximum 1 heavy job (training, ingestion, dataset download) at a time (Mutex Lock)
- Minimum available RAM check before job execution (Safety Guard)
- Dynamic worker count selection based on available RAM/CPU
- Explicit garbage collection & cache cleanup after heavy jobs
"""

from __future__ import annotations

import gc
import sys
import threading
import time
from typing import Callable, Any

import psutil

from kryntis.utils.logging import get_logger
from kryntis.utils.memory_monitor import snapshot, can_load

log = get_logger(__name__)

# Global mutex to enforce MAX 1 heavy task (training, downloading, ingestion) at a time
_HEAVY_TASK_LOCK = threading.Lock()

# Safe threshold: Reject heavy task if available RAM < 1000 MB
MIN_SAFE_RAM_MB = 1000.0


class MemorySafetyError(RuntimeError):
    """Raised when available system memory is below the safe threshold."""
    pass


def get_optimal_worker_count(max_limit: int = 2) -> int:
    """
    Dynamically select worker count based on available RAM and CPU count.
    Defaults to 1 worker on <= 8 GB RAM machines or low available memory.
    """
    vm = psutil.virtual_memory()
    total_gb = vm.total / (1024 ** 3)
    free_mb = vm.available / (1024 ** 2)

    if total_gb <= 8.5 or free_mb < 2000:
        return 1

    cpus = os.cpu_count() or 1
    return min(max_limit, max(1, cpus // 2))


def run_heavy_task_safely(
    task_name: str,
    task_fn: Callable[..., Any],
    *args: Any,
    required_ram_mb: float = 1500.0,
    **kwargs: Any,
) -> Any:
    """
    Executes a heavy CPU/Memory task inside a strict single-task mutex lock
    with pre-flight memory checks and post-task garbage collection.
    """
    log.info("requesting_heavy_task_execution", task=task_name)

    # 1. Acquire global task lock (reject/wait if another heavy task is running)
    acquired = _HEAVY_TASK_LOCK.acquire(blocking=False)
    if not acquired:
        log.warning("heavy_task_rejected_busy", task=task_name)
        raise MemorySafetyError(
            f"Cannot start task '{task_name}': Another heavy operation is currently running. "
            "Kryntis AI enforces single-task execution to remain safe on 8 GB RAM."
        )

    try:
        # 2. Pre-flight RAM safety check
        snap = snapshot()
        if snap.available_mb < MIN_SAFE_RAM_MB or not can_load(required_ram_mb, safety_margin_mb=512.0):
            log.error(
                "heavy_task_rejected_low_ram",
                task=task_name,
                available_mb=snap.available_mb,
                required_mb=required_ram_mb,
            )
            raise MemorySafetyError(
                f"Cannot start task '{task_name}': Low system RAM ({snap.available_mb:.0f} MB available). "
                f"Minimum required is {required_ram_mb + 512:.0f} MB."
            )

        log.info("heavy_task_started", task=task_name, free_ram_mb=snap.available_mb)
        
        # 3. Run the task
        start_t = time.time()
        result = task_fn(*args, **kwargs)
        elapsed = time.time() - start_t
        log.info("heavy_task_completed", task=task_name, elapsed_seconds=round(elapsed, 2))
        return result

    finally:
        # 4. Explicit post-task cleanup & RAM recovery
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        _HEAVY_TASK_LOCK.release()
        post_snap = snapshot()
        log.info("heavy_task_cleanup_done", task=task_name, free_ram_mb=post_snap.available_mb)
