"""
api/app/routers/labs.py — Lab catalog endpoints
"""

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import LabDetail, LabSummary

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/labs", response_model=list[LabSummary])
async def list_labs(
    request: Request,
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
) -> list[dict]:
    """
    List all available labs.

    Supports filtering by category and difficulty.
    """
    log.debug("list_labs_requested", category=category, difficulty=difficulty)

    lab_loader = getattr(request.app.state, "lab_loader", None)
    if lab_loader is None:
        log.warning("lab_loader_not_initialized")
        return []

    labs = lab_loader.all()
    log.debug("labs_fetched", total=len(labs))

    if category:
        labs = [lab for lab in labs if lab.get("category", "").lower() == category.lower()]
        log.debug("filtered_by_category", category=category, count=len(labs))

    if difficulty:
        labs = [lab for lab in labs if lab.get("difficulty", "").lower() == difficulty.lower()]
        log.debug("filtered_by_difficulty", difficulty=difficulty, count=len(labs))

    result = [
        {
            "id": lab["id"],
            "title": lab["title"],
            "category": lab["category"],
            "difficulty": lab["difficulty"],
            "estimated_time": lab.get("estimated_time"),
        }
        for lab in sorted(labs, key=lambda x: x["id"])
    ]
    log.info("list_labs_complete", returned=len(result))
    return result


@router.get("/labs/{lab_id:path}", response_model=LabDetail)
async def get_lab(lab_id: str, request: Request) -> dict:
    """
    Get full details for a specific lab.

    lab_id uses path matching to support category/slug format:
      e.g. GET /api/v1/labs/04-docker/docker-basics
    """
    log.debug("get_lab_requested", lab_id=lab_id)

    lab_loader = getattr(request.app.state, "lab_loader", None)
    if lab_loader is None:
        log.warning("lab_loader_not_initialized")
        raise HTTPException(status_code=503, detail="Lab catalog not available")

    # Try with the raw path as id first
    lab_data = lab_loader.get(lab_id)

    # Also try stripping leading/trailing slashes
    if lab_data is None:
        lab_data = lab_loader.get(lab_id.strip("/"))

    if lab_data is None:
        log.warning("lab_not_found", lab_id=lab_id)
        raise HTTPException(status_code=404, detail=f"Lab not found: {lab_id}")

    log.info("get_lab_complete", lab_id=lab_id, title=lab_data.get("title"))
    return lab_loader.to_detail(lab_data).model_dump()
