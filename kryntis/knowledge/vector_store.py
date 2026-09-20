"""
Vector Store — pluggable abstract interface + built-in adapters.

Built-in adapters:
  - ChromaAdapter   → ChromaDB (disk-persistent, default)
  - FAISSAdapter    → FAISS (in-memory + disk index)
  - CustomAdapter   → Placeholder for your own Vector DB

To connect your own Vector DB, subclass BaseVectorStore and pass
it to KnowledgeStore via dependency injection:

    from kryntis.knowledge.vector_store import BaseVectorStore

    class MyVectorDB(BaseVectorStore):
        def add(self, ...): ...
        def search(self, ...): ...
        ...

    store = KnowledgeStore(vector_store=MyVectorDB(...))
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class VectorSearchResult:
    """A single vector search result."""
    chunk_id: str
    text: str
    score: float          # Cosine similarity [0, 1]
    metadata: dict


# ─── Abstract Interface ───────────────────────────────────────────────────────

class BaseVectorStore(ABC):
    """
    Abstract vector store interface.

    Implement this to connect Kryntis AI to any vector database,
    including your own proprietary store.
    """

    @abstractmethod
    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        """Upsert vectors into the store."""
        ...

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        """Return top-k nearest neighbours for a query embedding."""
        ...

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """Delete vectors by ID."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return total number of stored vectors."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Delete all vectors (use with caution)."""
        ...

    def get_by_id(self, chunk_id: str) -> VectorSearchResult | None:
        """Retrieve a single chunk by ID (optional to override)."""
        raise NotImplementedError


# ─── ChromaDB Adapter ─────────────────────────────────────────────────────────

class ChromaAdapter(BaseVectorStore):
    """
    ChromaDB vector store adapter.

    Uses disk-persistent chromadb client — no server required.
    Collection is created automatically if it doesn't exist.
    """

    def __init__(self, path: str, collection_name: str) -> None:
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as e:
            raise ImportError("Install chromadb: pip install chromadb") from e

        Path(path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=path)
        self._col = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("chroma_adapter_init", path=path, collection=collection_name)

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        # Chroma upsert = add or update
        self._col.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=[{k: str(v) for k, v in m.items()} for m in metadatas],
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        kwargs: dict[str, Any] = dict(
            query_embeddings=[query_embedding],
            n_results=min(top_k, max(1, self.count())),
            include=["documents", "distances", "metadatas"],
        )
        if where:
            kwargs["where"] = where

        res = self._col.query(**kwargs)
        results: list[VectorSearchResult] = []
        for i, chunk_id in enumerate(res["ids"][0]):
            distance = res["distances"][0][i]
            score = max(0.0, 1.0 - distance)  # cosine distance → similarity
            results.append(VectorSearchResult(
                chunk_id=chunk_id,
                text=res["documents"][0][i],
                score=score,
                metadata=res["metadatas"][0][i] if res["metadatas"] else {},
            ))
        return results

    def delete(self, ids: list[str]) -> None:
        self._col.delete(ids=ids)

    def count(self) -> int:
        return self._col.count()

    def reset(self) -> None:
        self._client.delete_collection(self._col.name)
        self._col = self._client.get_or_create_collection(
            name=self._col.name,
            metadata={"hnsw:space": "cosine"},
        )

    def get_by_id(self, chunk_id: str) -> VectorSearchResult | None:
        res = self._col.get(ids=[chunk_id], include=["documents", "metadatas"])
        if not res["ids"]:
            return None
        return VectorSearchResult(
            chunk_id=chunk_id,
            text=res["documents"][0],
            score=1.0,
            metadata=res["metadatas"][0] if res["metadatas"] else {},
        )


# ─── FAISS Adapter ────────────────────────────────────────────────────────────

class FAISSAdapter(BaseVectorStore):
    """
    FAISS vector store adapter.

    Stores a flat cosine-similarity index backed by a JSON
    metadata sidecar on disk. Suitable as a lightweight fallback.
    """

    def __init__(self, index_path: str, dim: int = 384) -> None:
        try:
            import faiss
            self._faiss = faiss
        except ImportError as e:
            raise ImportError("Install faiss-cpu: pip install faiss-cpu") from e

        self._dim = dim
        self._index_path = Path(index_path)
        self._meta_path = self._index_path.with_suffix(".meta.json")
        self._index_path.parent.mkdir(parents=True, exist_ok=True)

        # id → (text, metadata)
        self._store: dict[str, tuple[str, dict]] = {}
        self._ids: list[str] = []  # Ordered to map FAISS int id → chunk_id

        if self._index_path.exists():
            self._index = faiss.read_index(str(self._index_path))
            self._load_meta()
        else:
            self._index = faiss.IndexFlatIP(dim)  # Inner product ≈ cosine after L2 norm

        log.info("faiss_adapter_init", path=str(index_path), dim=dim)

    def _load_meta(self) -> None:
        import json
        if self._meta_path.exists():
            with open(self._meta_path) as f:
                data = json.load(f)
            self._ids = data["ids"]
            self._store = {k: (v["text"], v["meta"]) for k, v in data["store"].items()}

    def _save_meta(self) -> None:
        import json
        data = {
            "ids": self._ids,
            "store": {k: {"text": v[0], "meta": v[1]} for k, v in self._store.items()},
        }
        with open(self._meta_path, "w") as f:
            json.dump(data, f)
        self._faiss.write_index(self._index, str(self._index_path))

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict],
    ) -> None:
        import numpy as np
        vecs = np.array(embeddings, dtype="float32")
        # L2-normalise for cosine similarity via inner product
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / (norms + 1e-10)
        self._index.add(vecs)
        for cid, text, meta in zip(ids, texts, metadatas):
            self._store[cid] = (text, meta)
            self._ids.append(cid)
        self._save_meta()

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        import numpy as np
        if self._index.ntotal == 0:
            return []
        q = np.array([query_embedding], dtype="float32")
        q /= np.linalg.norm(q) + 1e-10
        scores, indices = self._index.search(q, min(top_k * 2, self._index.ntotal))
        results: list[VectorSearchResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._ids):
                continue
            cid = self._ids[idx]
            text, meta = self._store.get(cid, ("", {}))
            results.append(VectorSearchResult(chunk_id=cid, text=text, score=float(score), metadata=meta))
            if len(results) >= top_k:
                break
        return results

    def delete(self, ids: list[str]) -> None:
        # FAISS flat index doesn't support deletion; mark as removed in meta
        for cid in ids:
            self._store.pop(cid, None)
        self._save_meta()

    def count(self) -> int:
        return self._index.ntotal

    def reset(self) -> None:
        self._index.reset()
        self._store.clear()
        self._ids.clear()
        self._save_meta()


# ─── Custom Adapter Placeholder ───────────────────────────────────────────────

class CustomVectorStoreAdapter(BaseVectorStore):
    """
    Placeholder adapter for connecting your own Vector DB.

    Replace the method bodies with calls to your proprietary
    vector database SDK. The rest of Kryntis AI is unchanged.

    Example: connect to Pinecone, Weaviate, Qdrant, Milvus, etc.
    """

    def __init__(self, **connection_kwargs) -> None:
        self._kwargs = connection_kwargs
        log.info("custom_vector_store_init", kwargs=list(connection_kwargs.keys()))
        # TODO: Initialise your vector DB client here
        raise NotImplementedError(
            "Implement CustomVectorStoreAdapter to connect your own Vector DB. "
            "See kryntis/knowledge/vector_store.py"
        )

    def add(self, ids, embeddings, texts, metadatas) -> None:
        raise NotImplementedError

    def search(self, query_embedding, top_k=5, where=None) -> list[VectorSearchResult]:
        raise NotImplementedError

    def delete(self, ids) -> None:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError


# ─── Factory ──────────────────────────────────────────────────────────────────

def build_vector_store(backend: str | None = None) -> BaseVectorStore:
    """
    Build the configured vector store from config/env.

    Args:
        backend: "chroma" | "faiss" | "postgres" | "custom". Defaults to config value.

    Returns:
        Configured BaseVectorStore instance.
    """
    cfg = get_config().knowledge
    backend = backend or cfg.vector_backend

    if backend == "chroma":
        return ChromaAdapter(path=cfg.chroma_path, collection_name=cfg.collection_name)
    elif backend == "faiss":
        idx_path = str(Path(cfg.chroma_path).parent / "faiss" / "index.faiss")
        return FAISSAdapter(index_path=idx_path)
    elif backend == "postgres" or backend == "pgvector":
        from kryntis.knowledge.pgvector_adapter import PGVectorAdapter
        return PGVectorAdapter()
    elif backend == "custom":
        return CustomVectorStoreAdapter()
    else:
        raise ValueError(f"Unknown vector backend: '{backend}'. Use: chroma, faiss, postgres, custom")


VectorStore = BaseVectorStore
