"""Cluster Node representation."""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ClusterNode:
    node_id: str
    ip_address: str
    port: int
    gpu_count: int
    vram_available_gb: float
    is_healthy: bool = True
