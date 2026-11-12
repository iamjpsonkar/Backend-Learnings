"""
api/app/main.py — FastAPI Lab Platform API entry point

Provides:
  GET  /health               — health check
  GET  /api/v1/labs          — list all labs
  GET  /api/v1/labs/{id}     — lab details
  GET  /api/v1/progress      — all progress
  POST /api/v1/progress      — record lab progress
  POST /api/v1/runner/run    — trigger lab run
  GET  /api/v1/services      — Docker service health
"""

import logging
import os
import time
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import init_db, get_db_path
from app.lab_loader import LabLoader
from app.routers import health, labs, progress, runner, services
from app.settings import settings

# ─────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

log = structlog.get_logger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(message)s",
)


# ─────────────────────────────────────────────
# Lifespan — startup and shutdown
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, clean up on shutdown."""
    log.info(
        "lab_api_starting",
        version="1.0.0",
        db_path=get_db_path(),
        labs_dir=settings.labs_dir,
        log_level=settings.log_level,
    )

    # Initialize database
    try:
        await init_db()
        log.info("database_initialized", db_path=get_db_path())
    except Exception as exc:
        log.error("database_init_failed", error=str(exc), exc_info=True)
        raise

    # Load lab catalog
    try:
        loader = LabLoader(settings.labs_dir)
        count = await loader.load_all()
        app.state.lab_loader = loader
        log.info("lab_catalog_loaded", lab_count=count, labs_dir=settings.labs_dir)
    except Exception as exc:
        log.error("lab_catalog_load_failed", error=str(exc), exc_info=True)
        # Non-fatal: API still starts, labs endpoint returns empty
        app.state.lab_loader = None

    log.info("lab_api_ready", port=4567)
    yield

    log.info("lab_api_shutting_down")


# ─────────────────────────────────────────────
# App factory
# ─────────────────────────────────────────────
app = FastAPI(
    title="Local Cloud Lab Platform API",
    description="Backend API for the local cloud lab platform.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the UI (React) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{settings.ui_port}",
        "http://localhost:3001",
        "http://lab.localhost",
        "http://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Request logging middleware
# ─────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    request_id = request.headers.get("x-request-id", "")
    log.debug(
        "request_received",
        method=request.method,
        path=request.url.path,
        request_id=request_id,
    )
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    log.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
        request_id=request_id,
    )
    return response


# ─────────────────────────────────────────────
# Global exception handler
# ─────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ─────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────
app.include_router(health.router, tags=["health"])
app.include_router(labs.router, prefix="/api/v1", tags=["labs"])
app.include_router(progress.router, prefix="/api/v1", tags=["progress"])
app.include_router(runner.router, prefix="/api/v1", tags=["runner"])
app.include_router(services.router, prefix="/api/v1", tags=["services"])


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=4567,
        reload=os.environ.get("RELOAD", "false").lower() == "true",
        log_level=settings.log_level.lower(),
    )
