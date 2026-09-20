"""
Ingestion router — multipart file upload with background processing, path sanitization, and size validation.

Endpoints:
  POST   /api/v1/ingestion/upload    → upload files, returns job_id
  GET    /api/v1/ingestion/job/{id}  → check job status
  DELETE /api/v1/ingestion/source/{id} → remove a source from the KB
"""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import BackgroundTasks

from kryntis.ingestion.pipeline import IngestionPipeline
from kryntis.ingestion.progress import format_progress
from kryntis.service.dependencies import get_doc_store, get_ingestion_pipeline
from kryntis.utils.config import get_config

router = APIRouter()


@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
) -> dict:
    """
    Upload one or more files for ingestion into the knowledge base.

    Returns a job_id that can be polled for status.
    """
    cfg = get_config().ingestion
    if len(files) > cfg.max_files_per_batch:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {cfg.max_files_per_batch} files per upload batch",
        )

    # Save to dedicated temporary directory
    tmp_dir = Path(tempfile.mkdtemp(prefix="kryntis_upload_"))
    saved: list[Path] = []

    try:
        for upload in files:
            # Prevent path traversal by extracting strictly the basename
            raw_filename = upload.filename or f"upload_{uuid.uuid4().hex[:8]}"
            safe_basename = Path(raw_filename).name
            if not safe_basename or safe_basename.startswith("."):
                safe_basename = f"file_{uuid.uuid4().hex[:8]}"

            dest = tmp_dir / safe_basename

            # Stream with size validation
            total_bytes = 0
            with open(dest, "wb") as f:
                while chunk := await upload.read(cfg.streaming_chunk_bytes):
                    total_bytes += len(chunk)
                    if total_bytes > cfg.max_file_size_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"File '{safe_basename}' exceeds maximum allowed size ({cfg.max_file_size_bytes} bytes).",
                        )
                    f.write(chunk)

            saved.append(dest)

        job = await pipeline.ingest_files(saved)
        return format_progress(job)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    pipeline: IngestionPipeline = Depends(get_ingestion_pipeline),
) -> dict:
    """Poll the status of a running ingestion job."""
    job = pipeline.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return format_progress(job)


@router.delete("/source/{source_id}")
async def delete_source(
    source_id: str,
    doc_store=Depends(get_doc_store),
) -> dict:
    """Remove a source and all its chunks from the knowledge base."""
    count = doc_store.delete_chunks_by_source(source_id)
    doc_store.delete_source(source_id)
    return {"status": "deleted", "source_id": source_id, "chunks_removed": count}
