"""
api/app/routers/progress.py — Lab progress tracking endpoints
"""

import json
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import LabProgress
from app.schemas import ProgressCreate, ProgressResponse

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/progress", response_model=list[ProgressResponse])
async def list_progress(
    lab_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> list:
    """
    Get lab progress records.
    Optionally filter by lab_id.
    """
    log.debug("list_progress_requested", lab_id=lab_id)

    stmt = select(LabProgress)
    if lab_id:
        stmt = stmt.where(LabProgress.lab_id == lab_id)
    stmt = stmt.order_by(LabProgress.lab_id)

    result = await db.execute(stmt)
    records = result.scalars().all()

    log.info("list_progress_complete", count=len(records), lab_id=lab_id)
    return [r.to_dict() for r in records]


@router.post("/progress", response_model=ProgressResponse, status_code=201)
async def record_progress(
    payload: ProgressCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Record or update lab progress.

    If a progress record exists for the lab, it is updated.
    If not, a new record is created.
    """
    log.info(
        "record_progress_requested",
        lab_id=payload.lab_id,
        status=payload.status,
        score=payload.score,
        max_score=payload.max_score,
    )

    # Check for existing progress record
    stmt = select(LabProgress).where(LabProgress.lab_id == payload.lab_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if existing:
        log.debug("updating_existing_progress", lab_id=payload.lab_id, prev_status=existing.status)
        existing.status = payload.status
        existing.score = payload.score
        existing.max_score = payload.max_score
        existing.attempts = (existing.attempts or 0) + 1
        existing.last_feedback = payload.feedback

        if payload.status == "in_progress" and existing.started_at is None:
            existing.started_at = now
        if payload.status in ("completed", "failed"):
            existing.completed_at = now

        await db.commit()
        await db.refresh(existing)
        log.info("progress_updated", lab_id=payload.lab_id, status=payload.status, attempts=existing.attempts)
        return existing.to_dict()

    # Create new record
    log.debug("creating_new_progress_record", lab_id=payload.lab_id)
    progress = LabProgress(
        lab_id=payload.lab_id,
        status=payload.status,
        score=payload.score,
        max_score=payload.max_score,
        attempts=1,
        last_feedback=payload.feedback,
        started_at=now if payload.status == "in_progress" else None,
        completed_at=now if payload.status in ("completed", "failed") else None,
    )
    db.add(progress)
    await db.commit()
    await db.refresh(progress)
    log.info("progress_created", lab_id=payload.lab_id, status=payload.status)
    return progress.to_dict()


@router.delete("/progress/{lab_id}", status_code=204)
async def reset_lab_progress(
    lab_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Reset progress for a specific lab."""
    log.info("reset_lab_progress_requested", lab_id=lab_id)

    stmt = select(LabProgress).where(LabProgress.lab_id == lab_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if record is None:
        log.warning("progress_record_not_found_for_reset", lab_id=lab_id)
        raise HTTPException(status_code=404, detail=f"No progress record for lab: {lab_id}")

    await db.delete(record)
    await db.commit()
    log.info("lab_progress_reset", lab_id=lab_id)
