"""
Ingestion router — multipart file upload with background processing.

Endpoints:
  POST   /api/v1/ingestion/upload    → upload files, returns job_id
  GET    /api/v1/ingestion/job/{id}  → check job status
  DELETE /api/v1/ingestion/source/{id} → remove a source from the KB
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi import BackgroundTasks

from kryntis.ingestion.pipeline import IngestionPipeline
from kryntis.ingestion.progress import format_progress
from kryntis.service.dependencies import get_doc_store, get_ingestion_pipeline

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
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per upload")

    # Save to temp dir
    tmp_dir = Path(tempfile.mkdtemp(prefix="kryntis_upload_"))
    saved: list[Path] = []

    for upload in files:
        dest = tmp_dir / (upload.filename or "file")
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        saved.append(dest)

    # Run ingestion in background
    async def run():
        try:
            await pipeline.ingest_files(saved)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    background_tasks.add_task(run)

    # Start the job to get a job_id synchronously
    job = await pipeline.ingest_files(saved)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return format_progress(job)


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
