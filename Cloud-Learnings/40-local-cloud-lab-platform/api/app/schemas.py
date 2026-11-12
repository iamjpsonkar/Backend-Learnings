"""
api/app/schemas.py — Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Lab schemas
# ─────────────────────────────────────────────

class LabTask(BaseModel):
    id: str
    description: str
    hints: list[str] = []


class LabGradingRule(BaseModel):
    check: str
    points: int


class LabSummary(BaseModel):
    """Lightweight lab listing item."""
    id: str
    title: str
    category: str
    difficulty: str
    estimated_time: Optional[str] = None


class LabDetail(BaseModel):
    """Full lab definition."""
    id: str
    title: str
    description: str
    difficulty: str
    estimated_time: Optional[str] = None
    category: str
    prerequisites: list[str] = []
    tools_required: list[str] = []
    docker_profiles: list[str] = []
    ports_used: list[int] = []
    learning_objectives: list[str] = []
    tasks: list[LabTask] = []
    validation_steps: list[str] = []
    grading_rules: list[LabGradingRule] = []
    cleanup_steps: list[str] = []
    related_docs: list[str] = []
    related_cloud_services: list[str] = []
    local_only: bool = True
    optional_real_cloud: Optional[str] = None
    cost_warning: Optional[str] = None
    safety_warning: Optional[str] = None


# ─────────────────────────────────────────────
# Progress schemas
# ─────────────────────────────────────────────

class ProgressCreate(BaseModel):
    lab_id: str
    status: str = Field(..., pattern="^(not_started|in_progress|completed|failed)$")
    score: int = 0
    max_score: int = 0
    feedback: Optional[str] = None  # JSON string


class ProgressResponse(BaseModel):
    id: int
    lab_id: str
    status: str
    score: int
    max_score: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = 0
    last_feedback: Optional[str] = None

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Runner schemas
# ─────────────────────────────────────────────

class RunRequest(BaseModel):
    lab_id: str
    verbose: bool = False


class ValidationResult(BaseModel):
    check_id: str
    description: str
    passed: bool
    message: Optional[str] = None


class GradeResult(BaseModel):
    score: int
    max_score: int
    percentage: float
    passed: bool
    feedback: list[str] = []
    validation_results: list[ValidationResult] = []


class RunResponse(BaseModel):
    lab_id: str
    status: str
    grade: Optional[GradeResult] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None


# ─────────────────────────────────────────────
# Service health schemas
# ─────────────────────────────────────────────

class ServiceStatus(BaseModel):
    name: str
    status: str  # running | stopped | unhealthy | not_found
    health: Optional[str] = None
    image: Optional[str] = None
    ports: list[str] = []


class ServicesResponse(BaseModel):
    services: list[ServiceStatus]
    total: int
    running: int


# ─────────────────────────────────────────────
# Health schemas
# ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    db_connected: bool = True
    labs_loaded: int = 0
    timestamp: Optional[str] = None
