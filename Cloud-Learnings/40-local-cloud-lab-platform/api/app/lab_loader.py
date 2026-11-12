"""
api/app/lab_loader.py — Load and validate lab YAML definitions from the labs/ directory.

Scans labs/<category>/<lab-slug>/lab.yaml files, validates against schema,
and caches results in the database.
"""

import os
from pathlib import Path
from typing import Optional

import structlog
import yaml
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import Lab
from app.schemas import LabDetail, LabTask, LabGradingRule

log = structlog.get_logger(__name__)

REQUIRED_FIELDS = {"id", "title", "description", "difficulty", "category"}
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


class LabLoader:
    """Loads and caches lab definitions from the filesystem."""

    def __init__(self, labs_dir: str):
        self.labs_dir = Path(labs_dir)
        self._cache: dict[str, dict] = {}
        log.info("lab_loader_initialized", labs_dir=str(self.labs_dir))

    async def load_all(self) -> int:
        """
        Scan labs_dir for all lab.yaml files, validate, and persist to DB.
        Returns count of labs successfully loaded.
        """
        if not self.labs_dir.exists():
            log.warning("labs_dir_not_found", labs_dir=str(self.labs_dir))
            return 0

        loaded = 0
        errors = 0
        yaml_files = list(self.labs_dir.rglob("lab.yaml"))
        log.info("scanning_labs_dir", yaml_files_found=len(yaml_files))

        for yaml_path in sorted(yaml_files):
            try:
                lab_data = self._load_yaml(yaml_path)
                self._validate(lab_data, yaml_path)
                await self._upsert_lab(lab_data, str(yaml_path))
                self._cache[lab_data["id"]] = lab_data
                loaded += 1
                log.debug("lab_loaded", lab_id=lab_data["id"], path=str(yaml_path))
            except Exception as exc:
                errors += 1
                log.error(
                    "lab_load_failed",
                    path=str(yaml_path),
                    error=str(exc),
                )

        log.info(
            "lab_load_complete",
            loaded=loaded,
            errors=errors,
            total=len(yaml_files),
        )
        return loaded

    def _load_yaml(self, path: Path) -> dict:
        """Load and parse a YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"lab.yaml must be a YAML mapping, got {type(data)}")
        return data

    def _validate(self, data: dict, path: Path) -> None:
        """Validate required fields and values."""
        missing = REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ValueError(f"Missing required fields: {missing}")

        if data.get("difficulty") not in VALID_DIFFICULTIES:
            raise ValueError(
                f"difficulty must be one of {VALID_DIFFICULTIES}, "
                f"got '{data.get('difficulty')}'"
            )

        lab_id = data.get("id", "")
        if not lab_id or not lab_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"id must be alphanumeric (with hyphens/underscores), got '{lab_id}'")

    async def _upsert_lab(self, data: dict, yaml_path: str) -> None:
        """Insert or update a lab record in the database."""
        async with AsyncSessionLocal() as session:
            existing = await session.get(Lab, data["id"])
            if existing:
                existing.title = data["title"]
                existing.category = data["category"]
                existing.difficulty = data["difficulty"]
                existing.estimated_time = data.get("estimated_time")
                existing.yaml_path = yaml_path
            else:
                lab = Lab(
                    id=data["id"],
                    title=data["title"],
                    category=data["category"],
                    difficulty=data["difficulty"],
                    estimated_time=data.get("estimated_time"),
                    yaml_path=yaml_path,
                )
                session.add(lab)
            await session.commit()

    def get(self, lab_id: str) -> Optional[dict]:
        """Get a lab by ID from cache."""
        return self._cache.get(lab_id)

    def all(self) -> list[dict]:
        """Get all cached labs."""
        return list(self._cache.values())

    def by_category(self, category: str) -> list[dict]:
        """Filter labs by category."""
        return [lab for lab in self._cache.values() if lab.get("category") == category]

    def to_detail(self, data: dict) -> LabDetail:
        """Convert raw YAML dict to LabDetail schema."""
        tasks = [
            LabTask(
                id=t.get("id", ""),
                description=t.get("description", ""),
                hints=t.get("hints", []),
            )
            for t in data.get("tasks", [])
        ]
        grading_rules = [
            LabGradingRule(
                check=r.get("check", ""),
                points=r.get("points", 0),
            )
            for r in data.get("grading_rules", [])
        ]
        return LabDetail(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            difficulty=data["difficulty"],
            estimated_time=data.get("estimated_time"),
            category=data["category"],
            prerequisites=data.get("prerequisites", []),
            tools_required=data.get("tools_required", []),
            docker_profiles=data.get("docker_profiles", []),
            ports_used=data.get("ports_used", []),
            learning_objectives=data.get("learning_objectives", []),
            tasks=tasks,
            validation_steps=data.get("validation_steps", []),
            grading_rules=grading_rules,
            cleanup_steps=data.get("cleanup_steps", []),
            related_docs=data.get("related_docs", []),
            related_cloud_services=data.get("related_cloud_services", []),
            local_only=data.get("local_only", True),
            optional_real_cloud=data.get("optional_real_cloud"),
            cost_warning=data.get("cost_warning"),
            safety_warning=data.get("safety_warning"),
        )
