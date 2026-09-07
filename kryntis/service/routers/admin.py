"""
Admin router — system health, provider management, learning queue.

Endpoints:
  GET  /api/v1/admin/health          → full system health check
  GET  /api/v1/admin/providers       → LLM provider status
  GET  /api/v1/admin/learning/pending → pending learning candidates
  POST /api/v1/admin/learning/approve → approve a learning candidate
  POST /api/v1/admin/learning/process → run approved learning batch
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from kryntis.core.model_manager import ModelManager
from kryntis.learning.continual_learner import ContinualLearner
from kryntis.service.dependencies import get_learner, get_orchestrator

router = APIRouter()


@router.get("/health")
async def full_health_check() -> dict:
    """Full system health check including LLM provider availability."""
    manager = ModelManager.from_config()
    provider_health = await manager.health_check()
    return {
        "status": "ok",
        "providers": provider_health,
    }


@router.get("/providers")
async def provider_status() -> dict:
    """Check LLM provider status."""
    manager = ModelManager.from_config()
    return await manager.health_check()


@router.get("/learning/pending")
async def list_pending(learner: ContinualLearner = Depends(get_learner)) -> dict:
    """List pending learning candidates awaiting approval."""
    pending = learner.list_pending()
    return {
        "pending": [
            {
                "candidate_id": c.candidate_id,
                "source": c.source,
                "confidence": c.confidence,
                "preview": c.content[:200],
            }
            for c in pending
        ],
        "count": len(pending),
    }


@router.post("/learning/approve/{candidate_id}")
async def approve_candidate(
    candidate_id: str,
    learner: ContinualLearner = Depends(get_learner),
) -> dict:
    """Approve a learning candidate for persistence."""
    approved = learner.approve(candidate_id)
    return {"status": "approved" if approved else "not_found", "candidate_id": candidate_id}


@router.post("/learning/process")
async def process_learning(learner: ContinualLearner = Depends(get_learner)) -> dict:
    """Run the approved learning batch."""
    count = await learner.process_approved()
    return {"status": "processed", "learned_count": count}
