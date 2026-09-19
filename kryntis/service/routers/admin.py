"""
Admin router — system health, provider management, continual learning queue, and user training.

Endpoints:
  GET  /api/v1/admin/health               → full system health check
  GET  /api/v1/admin/providers            → LLM provider status
  GET  /api/v1/admin/learning/pending     → pending learning candidates
  POST /api/v1/admin/learning/approve     → approve a learning candidate
  POST /api/v1/admin/learning/process     → run approved learning batch
  POST /api/v1/admin/train/user-feedback  → record user training correction
  POST /api/v1/admin/train/user-run       → run gradient updates on user data
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from kryntis.core.model_manager import ModelManager
from kryntis.learning.continual_learner import ContinualLearner
from kryntis.learning.user_trainer import UserTrainer
from kryntis.service.dependencies import get_learner, get_orchestrator

router = APIRouter()


class UserFeedbackRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="User instruction or prompt")
    response: str = Field(..., min_length=1, description="Corrected or desired AI response")
    domain: str = Field(default="user_input", description="Domain tag")


class UserTrainRunRequest(BaseModel):
    steps: int = Field(default=20, ge=1, le=500, description="Number of gradient update steps")
    learning_rate: float = Field(default=1e-4, ge=1e-6, le=1e-2, description="Fine-tuning learning rate")


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


@router.post("/train/user-feedback", summary="Record user feedback / correction pair for training")
async def record_user_feedback(req: UserFeedbackRequest) -> dict:
    """Save user prompt and corrected answer into user fine-tuning corpus."""
    try:
        trainer = UserTrainer()
        total_samples = trainer.record_user_sample(
            prompt=req.prompt,
            response=req.response,
            domain=req.domain,
        )
        return {
            "status": "recorded",
            "total_user_samples": total_samples,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train/user-run", summary="Trigger fine-tuning step on user-recorded data")
async def run_user_training(req: UserTrainRunRequest) -> dict:
    """Execute fine-tuning on user interactions."""
    try:
        trainer = UserTrainer()
        result = trainer.train_on_user_data(
            max_steps=req.steps,
            learning_rate=req.learning_rate,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
