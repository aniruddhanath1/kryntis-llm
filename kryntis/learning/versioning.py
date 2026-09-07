"""Knowledge versioning — snapshot and rollback support."""

from __future__ import annotations

import time
import uuid

from kryntis.knowledge.document_store import DocumentStore
from kryntis.utils.logging import get_logger

log = get_logger(__name__)


class KnowledgeVersionManager:
    """
    Manages snapshots of the knowledge base.

    Snapshots record the state of the document store at a point in time.
    Full vector index rollback is complex; this provides metadata-level
    snapshots and is a foundation for future complete rollback support.
    """

    def __init__(self, doc_store: DocumentStore | None = None) -> None:
        self._ds = doc_store or DocumentStore()

    def create_snapshot(self, description: str = "") -> str:
        snapshot_id = str(uuid.uuid4())
        self._ds.record_snapshot(snapshot_id, description)
        count = self._ds.count_chunks()
        log.info("snapshot_created", snapshot_id=snapshot_id, chunks=count)
        return snapshot_id

    def list_snapshots(self) -> list[dict]:
        return self._ds.list_snapshots()
