"""
Knowledge base management router.

Endpoints:
  GET  /api/v1/knowledge/sources         → list all ingested sources
  GET  /api/v1/knowledge/search          → full-text search
  GET  /api/v1/knowledge/stats           → KB statistics
  POST /api/v1/knowledge/snapshot        → create knowledge snapshot
  GET  /api/v1/knowledge/snapshots       → list all snapshots
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from kryntis.knowledge.document_store import DocumentStore
from kryntis.learning.versioning import KnowledgeVersionManager
from kryntis.service.dependencies import get_doc_store

router = APIRouter()


@router.get("/sources")
async def list_sources(ds: DocumentStore = Depends(get_doc_store)) -> dict:
    """List all ingested document sources."""
    sources = ds.list_sources()
    return {"sources": sources, "count": len(sources)}


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    ds: DocumentStore = Depends(get_doc_store),
) -> dict:
    """Full-text search across the knowledge base (fallback to BM25)."""
    results = ds.search_by_text(q, limit=limit)
    return {"results": results, "count": len(results)}


@router.get("/stats")
async def knowledge_stats(ds: DocumentStore = Depends(get_doc_store)) -> dict:
    """Return knowledge base statistics."""
    sources = ds.list_sources()
    chunks = ds.count_chunks()
    return {
        "source_count": len(sources),
        "chunk_count": chunks,
        "sources": [{"source_id": s["source_id"], "file_name": s["file_name"]} for s in sources],
    }


@router.post("/snapshot")
async def create_snapshot(
    description: str = "",
    ds: DocumentStore = Depends(get_doc_store),
) -> dict:
    """Create a knowledge base snapshot."""
    vm = KnowledgeVersionManager(doc_store=ds)
    snapshot_id = vm.create_snapshot(description)
    return {"snapshot_id": snapshot_id, "status": "created"}


@router.get("/snapshots")
async def list_snapshots(ds: DocumentStore = Depends(get_doc_store)) -> dict:
    """List all knowledge base snapshots."""
    vm = KnowledgeVersionManager(doc_store=ds)
    snapshots = vm.list_snapshots()
    return {"snapshots": snapshots}
