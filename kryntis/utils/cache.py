"""
Cache layer — thread-safe LRU + TTL caches for embeddings, search results,
and inference responses.

Three independent caches are exposed as module-level singletons:
  - embedding cache  : text → vector (no TTL; embeddings are deterministic)
  - search cache     : query+top_k → result list (TTL = search_cache_ttl_seconds)
  - response cache   : prompt+temperature → response string (TTL = response_cache_ttl_seconds)

Usage:
    from kryntis.utils.cache import get_embedding_cache, embedding_key
    cache = get_embedding_cache()
    vec   = cache.get(embedding_key(text))
    if vec is None:
        vec = model.encode(text)
        cache.set(embedding_key(text), vec)
"""

from __future__ import annotations

import hashlib
import time
from threading import Lock
from typing import Generic, TypeVar

from kryntis.utils.logging import get_logger

log = get_logger(__name__)

V = TypeVar("V")


# ── Core data structure ───────────────────────────────────────────────────────

class _Node(Generic[V]):
    __slots__ = ("key", "value", "expires_at", "prev", "next")

    def __init__(self, key: str, value: V, expires_at: float | None) -> None:
        self.key = key
        self.value = value
        self.expires_at = expires_at
        self.prev: _Node | None = None
        self.next: _Node | None = None


class LRUCache(Generic[V]):
    """Thread-safe doubly-linked LRU cache with optional per-entry TTL."""

    def __init__(self, maxsize: int, ttl_seconds: float | None = None) -> None:
        self._maxsize = max(1, maxsize)
        self._ttl = ttl_seconds
        self._map: dict[str, _Node[V]] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        # Sentinel nodes — never evicted, never returned
        self._head: _Node = _Node("__head__", None, None)  # type: ignore
        self._tail: _Node = _Node("__tail__", None, None)  # type: ignore
        self._head.next = self._tail
        self._tail.prev = self._head

    # ── Private helpers (call with lock held) ─────────────────────────────

    def _unlink(self, node: _Node) -> None:
        node.prev.next = node.next  # type: ignore
        node.next.prev = node.prev  # type: ignore

    def _prepend(self, node: _Node) -> None:
        node.next = self._head.next
        node.prev = self._head
        self._head.next.prev = node  # type: ignore
        self._head.next = node

    def _is_expired(self, node: _Node) -> bool:
        return node.expires_at is not None and time.monotonic() > node.expires_at

    # ── Public API ────────────────────────────────────────────────────────

    def get(self, key: str) -> V | None:
        with self._lock:
            node = self._map.get(key)
            if node is None:
                self._misses += 1
                return None
            if self._is_expired(node):
                self._unlink(node)
                del self._map[key]
                self._misses += 1
                return None
            self._unlink(node)
            self._prepend(node)
            self._hits += 1
            return node.value

    def set(self, key: str, value: V) -> None:
        expires_at = (time.monotonic() + self._ttl) if self._ttl else None
        with self._lock:
            if key in self._map:
                node = self._map[key]
                node.value = value
                node.expires_at = expires_at
                self._unlink(node)
                self._prepend(node)
                return
            node = _Node(key, value, expires_at)
            self._map[key] = node
            self._prepend(node)
            if len(self._map) > self._maxsize:
                lru = self._tail.prev  # type: ignore
                if lru is not self._head:
                    self._unlink(lru)
                    del self._map[lru.key]

    def invalidate(self, key: str) -> None:
        with self._lock:
            node = self._map.pop(key, None)
            if node:
                self._unlink(node)

    def clear(self) -> None:
        with self._lock:
            self._map.clear()
            self._head.next = self._tail
            self._tail.prev = self._head
            self._hits = 0
            self._misses = 0

    def __len__(self) -> int:
        return len(self._map)

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = round(self._hits / total, 4) if total else 0.0
        return {
            "size": len(self._map),
            "maxsize": self._maxsize,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


# ── Key derivation ────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def embedding_key(text: str) -> str:
    return _sha256(text)


def search_key(query: str, top_k: int) -> str:
    return _sha256(f"{query}\x00{top_k}")


def response_key(prompt: str, temperature: float) -> str:
    return _sha256(f"{prompt}\x00{temperature:.4f}")


# ── Module-level singletons ───────────────────────────────────────────────────

_embedding_cache: LRUCache[list[float]] | None = None
_search_cache: LRUCache[list[dict]] | None = None
_response_cache: LRUCache[str] | None = None
_init_lock = Lock()


def _init() -> None:
    global _embedding_cache, _search_cache, _response_cache
    if _embedding_cache is not None:
        return
    with _init_lock:
        if _embedding_cache is not None:
            return
        from kryntis.utils.config import get_config
        cfg = get_config().cache
        _embedding_cache = LRUCache(maxsize=cfg.embedding_cache_size)
        _search_cache = LRUCache(
            maxsize=cfg.search_cache_size,
            ttl_seconds=cfg.search_cache_ttl_seconds,
        )
        _response_cache = LRUCache(
            maxsize=cfg.response_cache_size,
            ttl_seconds=cfg.response_cache_ttl_seconds,
        )
        log.info(
            "cache_initialised",
            embedding_size=cfg.embedding_cache_size,
            search_size=cfg.search_cache_size,
            response_size=cfg.response_cache_size,
        )


def get_embedding_cache() -> LRUCache[list[float]]:
    _init()
    return _embedding_cache  # type: ignore


def get_search_cache() -> LRUCache[list[dict]]:
    _init()
    return _search_cache  # type: ignore


def get_response_cache() -> LRUCache[str]:
    _init()
    return _response_cache  # type: ignore


def cache_stats() -> dict:
    """Return hit/miss statistics for all three caches."""
    _init()
    return {
        "embedding": _embedding_cache.stats,  # type: ignore
        "search": _search_cache.stats,  # type: ignore
        "response": _response_cache.stats,  # type: ignore
    }


def clear_all_caches() -> None:
    """Flush all caches — useful after a knowledge base update."""
    _init()
    _embedding_cache.clear()  # type: ignore
    _search_cache.clear()  # type: ignore
    _response_cache.clear()  # type: ignore
    log.info("all_caches_cleared")
