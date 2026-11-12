"""
tests/test_runner.py — Tests for the lab runner

Tests run against the actual lab YAML files to verify schema compliance
and runner functionality.
"""

import sys
import json
import subprocess
from pathlib import Path

import pytest
import yaml

PLATFORM_ROOT = Path(__file__).parent.parent
LABS_DIR = PLATFORM_ROOT / "labs"
RUNNER = PLATFORM_ROOT / "lab-runner" / "runner.py"

REQUIRED_FIELDS = {"id", "title", "description", "difficulty", "category"}
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


def find_lab_yamls():
    """Find all lab.yaml files."""
    if not LABS_DIR.exists():
        return []
    return list(LABS_DIR.rglob("lab.yaml"))


@pytest.mark.parametrize("yaml_path", find_lab_yamls())
def test_lab_yaml_required_fields(yaml_path):
    """Every lab.yaml must have all required fields."""
    data = yaml.safe_load(yaml_path.read_text())
    missing = REQUIRED_FIELDS - set(data.keys())
    assert not missing, f"{yaml_path}: missing required fields: {missing}"


@pytest.mark.parametrize("yaml_path", find_lab_yamls())
def test_lab_yaml_valid_difficulty(yaml_path):
    """Every lab.yaml must have a valid difficulty."""
    data = yaml.safe_load(yaml_path.read_text())
    assert data.get("difficulty") in VALID_DIFFICULTIES, \
        f"{yaml_path}: difficulty must be one of {VALID_DIFFICULTIES}"


@pytest.mark.parametrize("yaml_path", find_lab_yamls())
def test_lab_yaml_has_description(yaml_path):
    """Every lab.yaml description must be at least 10 chars."""
    data = yaml.safe_load(yaml_path.read_text())
    desc = data.get("description", "")
    assert len(str(desc).strip()) >= 10, \
        f"{yaml_path}: description is too short (< 10 chars)"


@pytest.mark.parametrize("yaml_path", find_lab_yamls())
def test_lab_yaml_tasks_have_descriptions(yaml_path):
    """Every task must have a description."""
    data = yaml.safe_load(yaml_path.read_text())
    tasks = data.get("tasks", [])
    for i, task in enumerate(tasks):
        assert "description" in task, \
            f"{yaml_path}: task[{i}] missing 'description'"
        assert len(task["description"]) >= 5, \
            f"{yaml_path}: task[{i}] description too short"


def test_runner_list_command():
    """runner.py list should succeed and return output."""
    if not RUNNER.exists():
        pytest.skip("lab-runner/runner.py not found")

    result = subprocess.run(
        [sys.executable, str(RUNNER), "list"],
        capture_output=True, text=True, timeout=30,
    )
    # Exit 0 even if no labs found
    assert result.returncode == 0, f"runner list failed: {result.stderr}"


def test_runner_validate_all():
    """runner.py validate-all should pass for all lab YAMLs."""
    if not RUNNER.exists():
        pytest.skip("lab-runner/runner.py not found")

    result = subprocess.run(
        [sys.executable, str(RUNNER), "validate-all"],
        capture_output=True, text=True, timeout=60,
    )
    # Expect 0 (all valid) — any failure means a YAML has a schema error
    assert result.returncode == 0, \
        f"validate-all failed:\n{result.stdout}\n{result.stderr}"
