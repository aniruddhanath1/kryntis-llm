"""Progress tracking for ingestion jobs."""

from __future__ import annotations

from kryntis.ingestion.pipeline import IngestionJob


def format_progress(job: IngestionJob) -> dict:
    """Serialise an IngestionJob to a progress dict for API responses."""
    pct = 0
    if job.total_files > 0:
        pct = round((job.completed_files / job.total_files) * 100, 1)
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress_pct": pct,
        "completed_files": job.completed_files,
        "total_files": job.total_files,
        "failed_files": job.failed_files,
        "total_chunks": job.total_chunks,
        "errors": job.errors,
    }
