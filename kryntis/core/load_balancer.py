"""
Load Balancer — High-availability model provider and inference load balancer.

Supports:
1. Round-Robin Balancing
2. Weighted Balancing
3. Least-Latency Dynamic Balancing
4. Active Failover
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Sequence, TypeVar

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T")


@dataclass
class BackendNode(Generic[T]):
    """Represents an active model backend endpoint or provider instance."""
    id: str
    target: T
    weight: int = 1
    is_healthy: bool = True
    active_requests: int = 0
    total_requests: int = 0
    total_latency_ms: float = 0.0
    last_error: str | None = None
    last_checked_at: float = field(default_factory=time.time)

    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests


class ILoadBalancer(ABC, Generic[T]):
    """Abstract Load Balancer Interface (Interface Segregation)."""

    @abstractmethod
    def add_node(self, node: BackendNode[T]) -> None:
        """Register a backend node."""
        ...

    @abstractmethod
    def remove_node(self, node_id: str) -> bool:
        """Remove a backend node."""
        ...

    @abstractmethod
    def select_node(self) -> BackendNode[T] | None:
        """Select next optimal backend node according to load balancing strategy."""
        ...

    @abstractmethod
    def record_result(self, node_id: str, latency_ms: float, success: bool, error: str | None = None) -> None:
        """Record health metrics and latency for a node."""
        ...


class RoundRobinLoadBalancer(ILoadBalancer[T]):
    """Sequential Round-Robin Load Balancer."""

    def __init__(self, nodes: Sequence[BackendNode[T]] | None = None) -> None:
        self._nodes: list[BackendNode[T]] = list(nodes) if nodes else []
        self._index: int = 0

    def add_node(self, node: BackendNode[T]) -> None:
        self._nodes.append(node)

    def remove_node(self, node_id: str) -> bool:
        initial = len(self._nodes)
        self._nodes = [n for n in self._nodes if n.id != node_id]
        return len(self._nodes) < initial

    def select_node(self) -> BackendNode[T] | None:
        healthy_nodes = [n for n in self._nodes if n.is_healthy]
        if not healthy_nodes:
            return None
        self._index = self._index % len(healthy_nodes)
        node = healthy_nodes[self._index]
        self._index = (self._index + 1) % len(healthy_nodes)
        node.active_requests += 1
        node.total_requests += 1
        return node

    def record_result(self, node_id: str, latency_ms: float, success: bool, error: str | None = None) -> None:
        for node in self._nodes:
            if node.id == node_id:
                node.active_requests = max(0, node.active_requests - 1)
                node.total_latency_ms += latency_ms
                node.is_healthy = success
                node.last_error = error if not success else None
                node.last_checked_at = time.time()
                break


class WeightedLoadBalancer(ILoadBalancer[T]):
    """Weighted Load Balancer distributing traffic proportional to assigned weights."""

    def __init__(self, nodes: Sequence[BackendNode[T]] | None = None) -> None:
        self._nodes: list[BackendNode[T]] = list(nodes) if nodes else []
        self._current_weights: dict[str, int] = {}

    def add_node(self, node: BackendNode[T]) -> None:
        self._nodes.append(node)
        self._current_weights[node.id] = 0

    def remove_node(self, node_id: str) -> bool:
        initial = len(self._nodes)
        self._nodes = [n for n in self._nodes if n.id != node_id]
        self._current_weights.pop(node_id, None)
        return len(self._nodes) < initial

    def select_node(self) -> BackendNode[T] | None:
        healthy = [n for n in self._nodes if n.is_healthy]
        if not healthy:
            return None

        total_weight = sum(n.weight for n in healthy)
        if total_weight == 0:
            return healthy[0]

        best_node = None
        max_current = -1000000

        for node in healthy:
            cur = self._current_weights.get(node.id, 0) + node.weight
            self._current_weights[node.id] = cur
            if cur > max_current:
                max_current = cur
                best_node = node

        if best_node:
            self._current_weights[best_node.id] -= total_weight
            best_node.active_requests += 1
            best_node.total_requests += 1

        return best_node

    def record_result(self, node_id: str, latency_ms: float, success: bool, error: str | None = None) -> None:
        for node in self._nodes:
            if node.id == node_id:
                node.active_requests = max(0, node.active_requests - 1)
                node.total_latency_ms += latency_ms
                node.is_healthy = success
                node.last_error = error if not success else None
                break


class LeastLatencyLoadBalancer(ILoadBalancer[T]):
    """Dynamic Least-Latency and Least-Connections Load Balancer."""

    def __init__(self, nodes: Sequence[BackendNode[T]] | None = None) -> None:
        self._nodes: list[BackendNode[T]] = list(nodes) if nodes else []

    def add_node(self, node: BackendNode[T]) -> None:
        self._nodes.append(node)

    def remove_node(self, node_id: str) -> bool:
        initial = len(self._nodes)
        self._nodes = [n for n in self._nodes if n.id != node_id]
        return len(self._nodes) < initial

    def select_node(self) -> BackendNode[T] | None:
        healthy = [n for n in self._nodes if n.is_healthy]
        if not healthy:
            return None

        # Sort by active requests first, then average latency
        healthy.sort(key=lambda n: (n.active_requests, n.avg_latency_ms))
        selected = healthy[0]
        selected.active_requests += 1
        selected.total_requests += 1
        return selected

    def record_result(self, node_id: str, latency_ms: float, success: bool, error: str | None = None) -> None:
        for node in self._nodes:
            if node.id == node_id:
                node.active_requests = max(0, node.active_requests - 1)
                node.total_latency_ms += latency_ms
                node.is_healthy = success
                node.last_error = error if not success else None
                break
