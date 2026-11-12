"""
api/app/models.py — SQLAlchemy ORM models for lab platform
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db import Base


class Lab(Base):
    """Lab catalog entry — cached from lab.yaml files."""

    __tablename__ = "labs"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False, index=True)
    difficulty = Column(String, nullable=False)
    estimated_time = Column(String)
    yaml_path = Column(String, nullable=False)
    last_loaded_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    progress_records = relationship("LabProgress", back_populates="lab", lazy="select")
    run_records = relationship("LabRun", back_populates="lab", lazy="select")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "difficulty": self.difficulty,
            "estimated_time": self.estimated_time,
            "yaml_path": self.yaml_path,
            "last_loaded_at": self.last_loaded_at.isoformat() if self.last_loaded_at else None,
        }


class LabProgress(Base):
    """User progress for each lab."""

    __tablename__ = "progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lab_id = Column(String, ForeignKey("labs.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="not_started")
    score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    attempts = Column(Integer, default=0)
    last_feedback = Column(Text)  # JSON string

    lab = relationship("Lab", back_populates="progress_records")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lab_id": self.lab_id,
            "status": self.status,
            "score": self.score,
            "max_score": self.max_score,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "attempts": self.attempts,
            "last_feedback": self.last_feedback,
        }


class LabRun(Base):
    """Historical record of each lab run attempt."""

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lab_id = Column(String, ForeignKey("labs.id"), nullable=False, index=True)
    run_at = Column(DateTime, default=func.now())
    score = Column(Integer)
    max_score = Column(Integer)
    duration_seconds = Column(Integer)
    validation_output = Column(Text)  # JSON
    grade_output = Column(Text)        # JSON

    lab = relationship("Lab", back_populates="run_records")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "lab_id": self.lab_id,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "score": self.score,
            "max_score": self.max_score,
            "duration_seconds": self.duration_seconds,
            "validation_output": self.validation_output,
            "grade_output": self.grade_output,
        }


class Setting(Base):
    """Platform settings key-value store."""

    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
