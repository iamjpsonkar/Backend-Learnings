#!/usr/bin/env python3
"""
lab-runner/runner.py — Lab execution engine

CLI entry point for running, validating, and grading labs.

Usage:
  python3 runner.py list                          # list all available labs
  python3 runner.py info --lab=04-docker/docker-basics
  python3 runner.py run  --lab=04-docker/docker-basics
  python3 runner.py validate --lab=04-docker/docker-basics
  python3 runner.py grade --lab=04-docker/docker-basics --output-json
  python3 runner.py validate-all                  # validate all lab YAMLs
  python3 runner.py progress                      # show progress summary
  python3 runner.py report --output=reports/progress.json
  python3 runner.py reset-progress                # reset all progress in DB
"""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import click
import structlog
import yaml

# Runner is run from the platform root or via the API.
# Resolve paths relative to this file's parent directory.
RUNNER_DIR = Path(__file__).parent.resolve()
PLATFORM_ROOT = RUNNER_DIR.parent
LABS_DIR = PLATFORM_ROOT / "labs"
DB_PATH = PLATFORM_ROOT / "api" / "data" / "lab_platform.db"

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)
log = structlog.get_logger("runner")

logging.basicConfig(level=logging.WARNING, stream=sys.stderr)


# ─────────────────────────────────────────────
# Lab YAML loading
# ─────────────────────────────────────────────
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}
REQUIRED_FIELDS = {"id", "title", "description", "difficulty", "category"}


def load_lab_yaml(lab_id: str) -> dict:
    """Load and return lab.yaml for the given lab_id."""
    lab_path = LABS_DIR / lab_id / "lab.yaml"
    if not lab_path.exists():
        raise FileNotFoundError(f"lab.yaml not found: {lab_path}")

    with open(lab_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"lab.yaml must be a YAML mapping: {lab_path}")

    log.debug("lab_yaml_loaded", lab_id=lab_id, path=str(lab_path))
    return data


def validate_lab_yaml(data: dict, path: Optional[str] = None) -> list[str]:
    """
    Validate lab.yaml structure. Returns list of error messages.
    Empty list means valid.
    """
    errors = []
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")

    diff = data.get("difficulty", "")
    if diff not in VALID_DIFFICULTIES:
        errors.append(f"difficulty must be one of {sorted(VALID_DIFFICULTIES)}, got '{diff}'")

    lab_id = data.get("id", "")
    if not lab_id:
        errors.append("id is required")
    elif not all(c.isalnum() or c in "-_/" for c in lab_id):
        errors.append(f"id contains invalid characters: '{lab_id}'")

    tasks = data.get("tasks", [])
    if not isinstance(tasks, list):
        errors.append("tasks must be a list")
    else:
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"tasks[{i}] must be a mapping")
            elif "description" not in task:
                errors.append(f"tasks[{i}] missing 'description'")

    return errors


def find_all_labs() -> list[dict]:
    """Scan labs directory and return list of (id, path, data) for all valid labs."""
    if not LABS_DIR.exists():
        log.warning("labs_dir_not_found", path=str(LABS_DIR))
        return []

    labs = []
    for yaml_path in sorted(LABS_DIR.rglob("lab.yaml")):
        # lab_id is relative path from LABS_DIR, minus /lab.yaml
        lab_id = str(yaml_path.parent.relative_to(LABS_DIR))
        try:
            data = yaml.safe_load(yaml_path.read_text())
            labs.append({"id": lab_id, "path": str(yaml_path), "data": data})
        except Exception as exc:
            log.error("lab_yaml_load_failed", path=str(yaml_path), error=str(exc))

    log.info("labs_found", count=len(labs))
    return labs


# ─────────────────────────────────────────────
# Docker profile check
# ─────────────────────────────────────────────
def check_docker_profiles(required_profiles: list[str]) -> tuple[bool, list[str]]:
    """
    Check that required Docker Compose profiles are running.
    Returns (all_running: bool, missing_profiles: list[str]).
    """
    try:
        import docker
        client = docker.from_env()
        containers = client.containers.list(
            filters={"label": "com.cloudlabs.project=local-cloud-lab", "status": "running"}
        )
        # Map running containers to profile names via the service label
        # We use container names to infer profiles
        running_names = {c.name for c in containers}
        log.debug("running_containers", count=len(running_names))
    except Exception as exc:
        log.warning("docker_check_failed", error=str(exc))
        return True, []  # If Docker unavailable, don't block

    # Profile → expected container name mapping (simplified)
    profile_containers = {
        "core": "cloud-lab-api",
        "observability": "cloud-lab-prometheus",
        "security": "cloud-lab-vault",
        "cicd": "cloud-lab-gitea",
        "data": "cloud-lab-postgres",
        "aws-local": "cloud-lab-localstack",
        "azure-local": "cloud-lab-azurite",
        "kubernetes": None,  # kind runs on host, not in Docker
    }

    missing = []
    for profile in required_profiles:
        expected = profile_containers.get(profile)
        if expected is None:
            continue  # kubernetes — can't check via Docker
        if expected not in running_names:
            missing.append(profile)

    return len(missing) == 0, missing


# ─────────────────────────────────────────────
# Validation and grading
# ─────────────────────────────────────────────
def run_script(script_path: Path, timeout: int = 120) -> tuple[int, str, str]:
    """
    Run a shell script. Returns (returncode, stdout, stderr).
    """
    if not script_path.exists():
        log.debug("script_not_found", path=str(script_path))
        return -1, "", f"Script not found: {script_path}"

    log.info("running_script", script=str(script_path))
    start = time.time()
    try:
        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=script_path.parent,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = round(time.time() - start, 2)
        log.info(
            "script_completed",
            script=script_path.name,
            returncode=result.returncode,
            duration_seconds=duration,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        log.error("script_timeout", script=str(script_path), timeout=timeout)
        return -1, "", f"Script timed out after {timeout}s"
    except Exception as exc:
        log.error("script_error", script=str(script_path), error=str(exc))
        return -1, "", str(exc)


def run_validation(lab_id: str, lab_data: dict) -> dict:
    """Run validate.sh and return structured results."""
    lab_dir = LABS_DIR / lab_id
    validate_script = lab_dir / "validate.sh"

    returncode, stdout, stderr = run_script(validate_script)

    if returncode == -1 and "not found" in stderr:
        log.info("no_validate_script", lab_id=lab_id)
        return {
            "validations": [],
            "all_passed": True,
            "note": "No validate.sh — manual validation only",
        }

    passed = returncode == 0
    validations = []

    # Try to parse structured output (one check per line: PASS/FAIL: description)
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("PASS:"):
            validations.append({
                "id": f"check-{len(validations)+1}",
                "description": line[5:].strip(),
                "passed": True,
            })
        elif line.startswith("FAIL:"):
            validations.append({
                "id": f"check-{len(validations)+1}",
                "description": line[5:].strip(),
                "passed": False,
            })

    # If no structured output, treat exit code as overall result
    if not validations:
        validations = [{
            "id": "overall",
            "description": "Lab validation",
            "passed": passed,
            "message": stdout[:500] if stdout else stderr[:200],
        }]

    log.info(
        "validation_complete",
        lab_id=lab_id,
        all_passed=passed,
        checks=len(validations),
    )

    return {
        "validations": validations,
        "all_passed": passed,
        "stdout": stdout,
        "stderr": stderr[:500] if stderr else "",
    }


def run_grading(lab_id: str, lab_data: dict, validation_result: dict) -> dict:
    """
    Run grade.sh if present. Falls back to grading_rules from lab.yaml.
    Returns structured grade result.
    """
    lab_dir = LABS_DIR / lab_id
    grade_script = lab_dir / "grade.sh"

    grading_rules = lab_data.get("grading_rules", [])
    max_score = sum(r.get("points", 0) for r in grading_rules) if grading_rules else 100

    # Try grade.sh first
    returncode, stdout, stderr = run_script(grade_script)

    if returncode != -1:
        try:
            grade_data = json.loads(stdout)
            score = grade_data.get("score", 0)
            result_max = grade_data.get("max_score", max_score)
            feedback = grade_data.get("feedback", [])
            passed = score >= result_max * 0.7 if result_max > 0 else returncode == 0
            log.info(
                "grading_from_grade_sh",
                lab_id=lab_id,
                score=score,
                max_score=result_max,
                passed=passed,
            )
            return {
                "score": score,
                "max_score": result_max,
                "percentage": round(score / result_max * 100, 1) if result_max > 0 else 0,
                "passed": passed,
                "feedback": feedback,
                "validations": validation_result.get("validations", []),
            }
        except json.JSONDecodeError:
            log.warning("grade_sh_invalid_json", lab_id=lab_id, stdout=stdout[:200])

    # Fall back: score from validation results
    validations = validation_result.get("validations", [])
    if grading_rules and validations:
        score = sum(
            r.get("points", 0)
            for r, v in zip(grading_rules, validations)
            if v.get("passed")
        )
    elif validations:
        passed_count = sum(1 for v in validations if v.get("passed"))
        score = int((passed_count / len(validations)) * max_score) if validations else 0
    else:
        score = max_score if validation_result.get("all_passed") else 0

    passed = validation_result.get("all_passed", False)
    feedback = ["Validation passed!" if passed else "Some validation checks failed."]

    log.info(
        "grading_from_validation",
        lab_id=lab_id,
        score=score,
        max_score=max_score,
        passed=passed,
    )

    return {
        "score": score,
        "max_score": max_score,
        "percentage": round(score / max_score * 100, 1) if max_score > 0 else 0,
        "passed": passed,
        "feedback": feedback,
        "validations": validations,
    }


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
@click.group()
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable verbose output")
def cli(verbose):
    """Local Cloud Lab Platform — Lab Runner"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        structlog.configure(processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ])


@cli.command("list")
@click.option("--category", default=None, help="Filter by category")
@click.option("--difficulty", default=None, help="Filter by difficulty")
def cmd_list(category, difficulty):
    """List all available labs."""
    labs = find_all_labs()

    if not labs:
        click.echo("No labs found. Check that labs/ directory contains lab.yaml files.")
        return

    if category:
        labs = [l for l in labs if l["data"].get("category", "").lower() == category.lower()]
    if difficulty:
        labs = [l for l in labs if l["data"].get("difficulty", "").lower() == difficulty.lower()]

    click.echo(f"\n{'ID':<45} {'DIFFICULTY':<15} {'TIME':<15} TITLE")
    click.echo("-" * 110)
    for lab in labs:
        d = lab["data"]
        click.echo(
            f"{lab['id']:<45} {d.get('difficulty',''):<15} {d.get('estimated_time',''):<15} {d.get('title','')}"
        )
    click.echo(f"\n{len(labs)} lab(s) found")


@cli.command("info")
@click.option("--lab", required=True, help="Lab ID (e.g. 04-docker/docker-basics)")
def cmd_info(lab):
    """Show detailed info for a lab."""
    try:
        data = load_lab_yaml(lab)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"\n{'='*60}")
    click.echo(f"  {data.get('title', 'Unknown')}")
    click.echo(f"{'='*60}")
    click.echo(f"  ID:         {data.get('id', lab)}")
    click.echo(f"  Category:   {data.get('category', '')}")
    click.echo(f"  Difficulty: {data.get('difficulty', '')}")
    click.echo(f"  Time:       {data.get('estimated_time', 'Unknown')}")
    click.echo(f"\n  Description:")
    click.echo(f"  {data.get('description', '')}")
    click.echo(f"\n  Prerequisites:")
    for p in data.get("prerequisites", []):
        click.echo(f"    - {p}")
    click.echo(f"\n  Required profiles:")
    for p in data.get("docker_profiles", []):
        click.echo(f"    - {p}  (make start-{p})")
    click.echo(f"\n  Learning objectives:")
    for obj in data.get("learning_objectives", []):
        click.echo(f"    - {obj}")
    click.echo(f"\n  Tasks ({len(data.get('tasks', []))}):")
    for i, task in enumerate(data.get("tasks", []), 1):
        click.echo(f"    {i}. {task.get('description', '')}")


@cli.command("run")
@click.option("--lab", required=True, help="Lab ID (e.g. 04-docker/docker-basics)")
@click.option("--verbose", is_flag=True, default=False)
def cmd_run(lab, verbose):
    """
    Run a lab interactively. Prints the brief, waits for you to type 'done',
    then validates and grades.
    """
    try:
        data = load_lab_yaml(lab)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"\n{'='*60}")
    click.echo(f"  LAB: {data.get('title', lab)}")
    click.echo(f"  Difficulty: {data.get('difficulty', '')}  |  Time: {data.get('estimated_time', '')}")
    click.echo(f"{'='*60}")
    click.echo(f"\n{data.get('description', '')}\n")

    # Check Docker profiles
    required_profiles = data.get("docker_profiles", [])
    if required_profiles:
        ok, missing = check_docker_profiles(required_profiles)
        if not ok:
            click.echo(f"\n⚠  Required profiles not running: {', '.join(missing)}")
            for p in missing:
                click.echo(f"   Run: make start-{p}")
            click.echo("")

    click.echo("Learning Objectives:")
    for obj in data.get("learning_objectives", []):
        click.echo(f"  - {obj}")

    click.echo(f"\nTasks:")
    for i, task in enumerate(data.get("tasks", []), 1):
        click.echo(f"\n  {i}. {task.get('description', '')}")
        if verbose and task.get("hints"):
            click.echo("     Hints:")
            for h in task["hints"]:
                click.echo(f"       - {h}")

    if data.get("safety_warning"):
        click.echo(f"\n⚠  WARNING: {data['safety_warning']}")

    click.echo(f"\n{'─'*60}")
    click.echo("Complete the tasks above, then type 'done' and press Enter.")
    click.echo("Type 'hints' to reveal hints. Type 'skip' to skip grading.")
    click.echo(f"{'─'*60}\n")

    while True:
        try:
            user_input = input("> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            click.echo("\nLab cancelled.")
            sys.exit(0)

        if user_input == "done":
            break
        elif user_input == "hints":
            for task in data.get("tasks", []):
                for hint in task.get("hints", []):
                    click.echo(f"  💡 {hint}")
        elif user_input == "skip":
            click.echo("Skipping grading. Progress not recorded.")
            sys.exit(0)
        elif user_input == "help":
            click.echo("Commands: done | hints | skip")

    # Run validation and grading
    click.echo("\nRunning validation...")
    start = time.time()
    validation = run_validation(lab, data)
    grade = run_grading(lab, data, validation)
    duration = round(time.time() - start, 2)

    click.echo(f"\n{'='*60}")
    if grade["passed"]:
        click.echo(f"  ✓ LAB PASSED — Score: {grade['score']}/{grade['max_score']} ({grade['percentage']}%)")
    else:
        click.echo(f"  ✗ LAB FAILED — Score: {grade['score']}/{grade['max_score']} ({grade['percentage']}%)")
    click.echo(f"{'='*60}")

    for fb in grade.get("feedback", []):
        click.echo(f"  {fb}")

    if not grade["passed"]:
        click.echo("\nValidation details:")
        for v in grade.get("validations", []):
            mark = "✓" if v.get("passed") else "✗"
            click.echo(f"  {mark} {v.get('description', '')}")
            if not v.get("passed") and v.get("message"):
                click.echo(f"      → {v['message']}")

    click.echo(f"\nCompleted in {duration}s")


@cli.command("validate")
@click.option("--lab", required=True, help="Lab ID")
def cmd_validate(lab):
    """Run validate.sh for a lab and show results."""
    try:
        data = load_lab_yaml(lab)
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Validating: {data.get('title', lab)}")
    result = run_validation(lab, data)

    for v in result.get("validations", []):
        mark = "✓" if v.get("passed") else "✗"
        click.echo(f"  {mark} {v.get('description', '')}")

    if result.get("all_passed"):
        click.echo("\nAll checks passed.")
    else:
        click.echo("\nSome checks failed.")
        sys.exit(1)


@cli.command("grade")
@click.option("--lab", required=True, help="Lab ID")
@click.option("--output-json", is_flag=True, default=False, help="Output JSON (for API use)")
@click.option("--verbose", is_flag=True, default=False)
def cmd_grade(lab, output_json, verbose):
    """Grade a lab and output results."""
    try:
        data = load_lab_yaml(lab)
    except FileNotFoundError as exc:
        if output_json:
            click.echo(json.dumps({"error": str(exc), "score": 0, "max_score": 0, "passed": False}))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    validation = run_validation(lab, data)
    grade = run_grading(lab, data, validation)

    if output_json:
        click.echo(json.dumps(grade))
    else:
        click.echo(f"\nGrade: {grade['score']}/{grade['max_score']} ({grade['percentage']}%)")
        click.echo(f"Passed: {grade['passed']}")
        for fb in grade.get("feedback", []):
            click.echo(f"  {fb}")


@cli.command("validate-all")
def cmd_validate_all():
    """Validate all lab.yaml files and report errors."""
    labs = find_all_labs()
    errors_found = 0

    click.echo(f"Scanning {len(labs)} lab definitions...")
    for lab in labs:
        errors = validate_lab_yaml(lab["data"], lab["path"])
        if errors:
            click.echo(f"\n  ERROR: {lab['id']}")
            for err in errors:
                click.echo(f"    - {err}")
            errors_found += 1
        else:
            click.echo(f"  ✓ {lab['id']}")

    click.echo(f"\n{len(labs) - errors_found}/{len(labs)} valid")
    if errors_found:
        sys.exit(1)


@cli.command("progress")
def cmd_progress():
    """Show lab progress summary from the database."""
    import sqlite3

    db_path = str(DB_PATH)
    if not Path(db_path).exists():
        click.echo("No database found. Run 'make setup' first.")
        return

    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT lab_id, status, score, max_score, attempts FROM progress ORDER BY lab_id"
        ).fetchall()
        conn.close()
    except Exception as exc:
        click.echo(f"Database error: {exc}", err=True)
        return

    if not rows:
        click.echo("No progress recorded yet. Start a lab with: make run-lab LAB=...")
        return

    click.echo(f"\n{'LAB':<50} {'STATUS':<15} {'SCORE':<12} ATTEMPTS")
    click.echo("-" * 95)
    for lab_id, status, score, max_score, attempts in rows:
        score_str = f"{score}/{max_score}" if max_score else "—"
        click.echo(f"{lab_id:<50} {status:<15} {score_str:<12} {attempts or 0}")

    completed = sum(1 for _, s, *_ in rows if s == "completed")
    click.echo(f"\nCompleted: {completed}/{len(rows)}")


@cli.command("report")
@click.option("--output", default="reports/progress.json", help="Output file path")
def cmd_report(output):
    """Generate a progress report JSON file."""
    import sqlite3

    db_path = str(DB_PATH)
    output_path = PLATFORM_ROOT / output

    if not Path(db_path).exists():
        click.echo("No database found. Run 'make setup' first.")
        return

    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT lab_id, status, score, max_score, attempts, completed_at FROM progress"
        ).fetchall()
        conn.close()
    except Exception as exc:
        click.echo(f"Database error: {exc}", err=True)
        return

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_labs_attempted": len(rows),
        "completed": sum(1 for _, s, *_ in rows if s == "completed"),
        "in_progress": sum(1 for _, s, *_ in rows if s == "in_progress"),
        "failed": sum(1 for _, s, *_ in rows if s == "failed"),
        "total_score": sum(r[2] or 0 for r in rows),
        "total_max_score": sum(r[3] or 0 for r in rows),
        "labs": [
            {
                "lab_id": r[0],
                "status": r[1],
                "score": r[2],
                "max_score": r[3],
                "attempts": r[4],
                "completed_at": r[5],
            }
            for r in rows
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    click.echo(f"Report saved to: {output_path}")


@cli.command("reset-progress")
def cmd_reset_progress():
    """Reset all progress in the database."""
    import sqlite3

    db_path = str(DB_PATH)
    if not Path(db_path).exists():
        click.echo("No database found.")
        return

    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM progress")
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()
    click.echo("Progress reset.")


if __name__ == "__main__":
    cli()
