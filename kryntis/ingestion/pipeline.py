"""
Ingestion Pipeline — streaming multi-file ingestion with progress tracking.

Flow: File → Validate → Chunk → Embed → Store (vector + document)
Handles up to 10 files simultaneously, max 100 MB per file.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from kryntis.chunking.chunk_router import ChunkRouter
from kryntis.ingestion.validator import FileValidator, ValidationResult
from kryntis.knowledge.document_store import DocumentStore
from kryntis.knowledge.provenance import Provenance, ProvenanceType
from kryntis.knowledge.vector_store import BaseVectorStore, build_vector_store
from kryntis.rag.embedder import get_embedder
from kryntis.utils.config import get_config
from kryntis.utils.logging import get_logger
from kryntis.utils.memory_monitor import log_memory

log = get_logger(__name__)


@dataclass
class IngestionJob:
    """Tracks the progress of a multi-file ingestion job."""
    job_id: str
    file_names: list[str]
    total_files: int
    started_at: float = field(default_factory=time.time)
    completed_files: int = 0
    failed_files: list[str] = field(default_factory=list)
    total_chunks: int = 0
    status: str = "running"       # running | completed | failed
    errors: list[str] = field(default_factory=list)


class IngestionPipeline:
    """
    Async streaming ingestion pipeline.

    Validates, chunks, embeds, and stores files one by one
    without loading the full file into RAM.
    """

    def __init__(
        self,
        vector_store: BaseVectorStore | None = None,
        doc_store: DocumentStore | None = None,
        chunk_router: ChunkRouter | None = None,
    ) -> None:
        cfg = get_config()
        self._vs = vector_store or build_vector_store()
        self._ds = doc_store or DocumentStore()
        self._router = chunk_router or ChunkRouter()
        self._embedder = get_embedder()
        self._validator = FileValidator()
        self._batch_size = cfg.rag.embedder_batch_size
        self._jobs: dict[str, IngestionJob] = {}

    async def ingest_files(
        self,
        file_paths: list[Path],
        on_progress: Callable[[IngestionJob], None] | None = None,
    ) -> IngestionJob:
        """
        Ingest multiple files asynchronously.

        Args:
            file_paths: List of uploaded file paths.
            on_progress: Optional callback called after each file completes.

        Returns:
            Completed IngestionJob.
        """
        cfg = get_config().ingestion
        if len(file_paths) > cfg.max_files_per_batch:
            raise ValueError(
                f"Too many files: {len(file_paths)} > {cfg.max_files_per_batch} max"
            )

        job = IngestionJob(
            job_id=str(uuid.uuid4()),
            file_names=[p.name for p in file_paths],
            total_files=len(file_paths),
        )
        self._jobs[job.job_id] = job
        log.info("ingestion_job_started", job_id=job.job_id, files=len(file_paths))
        log_memory("ingestion_start")

        import gc
        from kryntis.utils.memory_monitor import snapshot, can_load

        snap = snapshot()
        if snap.available_mb < 800.0:
            raise MemoryError(f"Insufficient RAM to start ingestion: {snap.available_mb:.0f} MB free, need at least 800 MB.")

        for path in file_paths:
            try:
                await self._ingest_one(path, job)
                job.completed_files += 1
            except Exception as e:
                log.error("ingestion_file_error", path=str(path), error=str(e))
                job.failed_files.append(path.name)
                job.errors.append(f"{path.name}: {e}")
            gc.collect()
            if on_progress:
                on_progress(job)

        job.status = "failed" if job.failed_files and not job.completed_files else "completed"
        log.info(
            "ingestion_job_done",
            job_id=job.job_id,
            completed=job.completed_files,
            failed=len(job.failed_files),
            chunks=job.total_chunks,
        )
        gc.collect()
        log_memory("ingestion_end")
        return job

    async def _ingest_one(self, path: Path, job: IngestionJob) -> None:
        """Ingest a single file into the knowledge store."""
        # Validate
        result: ValidationResult = self._validator.validate(path)
        if not result.valid:
            raise ValueError(f"Validation failed: {result.reason}")

        source_id = str(uuid.uuid5(uuid.NAMESPACE_URL, str(path.resolve())))

        # Register source
        self._ds.upsert_source(
            source_id=source_id,
            source_path=str(path),
            file_name=path.name,
            file_size=path.stat().st_size,
            mime_type=result.mime_type,
        )

        # Stream chunks
        chunk_buffer: list = []
        texts: list[str] = []

        for chunk in self._router.chunk(path, source_id):
            chunk_buffer.append(chunk)
            texts.append(chunk.text)

            if len(chunk_buffer) >= self._batch_size:
                await self._store_batch(chunk_buffer, texts, job)
                chunk_buffer.clear()
                texts.clear()

        if chunk_buffer:
            await self._store_batch(chunk_buffer, texts, job)

    async def _store_batch(self, chunks: list, texts: list[str], job: IngestionJob) -> None:
        """Embed and store a batch of chunks."""
        embeddings = await self._embedder.aembed(texts)

        ids = [c.chunk_id for c in chunks]
        metadatas = [
            {
                "source_id": c.source_id,
                "source_path": c.source_path,
                "section": c.section,
                "page": str(c.page or ""),
                "chunk_type": c.chunk_type,
                "token_count": str(c.token_count),
            }
            for c in chunks
        ]

        self._vs.add(ids=ids, embeddings=embeddings, texts=texts, metadatas=metadatas)

        for chunk in chunks:
            self._ds.upsert_chunk(chunk, confidence=1.0, validated=True, provenance="document")

        job.total_chunks += len(chunks)
        log.debug("batch_stored", size=len(chunks), total=job.total_chunks)

    def get_job(self, job_id: str) -> IngestionJob | None:
        return self._jobs.get(job_id)
