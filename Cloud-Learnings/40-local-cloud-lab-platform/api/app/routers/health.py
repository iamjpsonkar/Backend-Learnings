"""
api/app/routers/health.py — Health check endpoint
"""

from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas import HealthResponse

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> dict:
    """
    Health check endpoint used by Docker, load balancers, and the UI.
    Returns database connectivity and loaded lab count.
    """
    log.debug("health_check_requested")

    labs_loaded = 0
    db_connected = True
    lab_loader = getattr(request.app.state, "lab_loader", None)

    if lab_loader is not None:
        try:
            labs_loaded = len(lab_loader.all())
        except Exception as exc:
            log.warning("health_lab_count_failed", error=str(exc))

    # Quick DB connectivity test
    try:
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
    except Exception as exc:
        log.error("health_db_check_failed", error=str(exc))
        db_connected = False

    status = "ok" if db_connected else "degraded"
    log.info("health_check_complete", status=status, labs_loaded=labs_loaded, db_connected=db_connected)

    return {
        "status": status,
        "version": "1.0.0",
        "db_connected": db_connected,
        "labs_loaded": labs_loaded,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
