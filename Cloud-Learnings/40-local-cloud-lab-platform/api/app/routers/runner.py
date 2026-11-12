"""
api/app/routers/runner.py — Lab execution trigger endpoints
"""

import asyncio
import json
import subprocess
import time
from pathlib import Path

import structlog
from fastapi import APIRouter, HTTPException, Request

from app.schemas import RunRequest, RunResponse, GradeResult, ValidationResult
from app.settings import settings

log = structlog.get_logger(__name__)
router = APIRouter()

# Lab runner script path (relative to platform root, resolved at runtime)
LAB_RUNNER_SCRIPT = Path(__file__).parent.parent.parent.parent / "lab-runner" / "runner.py"


@router.post("/runner/run", response_model=RunResponse)
async def run_lab(payload: RunRequest, request: Request) -> dict:
    """
    Trigger a lab validation/grading run.

    This calls the lab-runner/runner.py script as a subprocess and returns
    structured results. The runner executes validate.sh and grade.sh.
    """
    lab_id = payload.lab_id
    verbose = payload.verbose
    log.info("runner_run_requested", lab_id=lab_id, verbose=verbose)

    # Verify the lab exists
    lab_loader = getattr(request.app.state, "lab_loader", None)
    if lab_loader is None:
        log.warning("lab_loader_unavailable", lab_id=lab_id)
        raise HTTPException(status_code=503, detail="Lab catalog not available")

    lab_data = lab_loader.get(lab_id) or lab_loader.get(lab_id.strip("/"))
    if lab_data is None:
        log.warning("runner_lab_not_found", lab_id=lab_id)
        raise HTTPException(status_code=404, detail=f"Lab not found: {lab_id}")

    if not LAB_RUNNER_SCRIPT.exists():
        log.error("runner_script_missing", path=str(LAB_RUNNER_SCRIPT))
        raise HTTPException(status_code=503, detail="Lab runner not available")

    # Execute the runner
    start_time = time.time()
    cmd = [
        "python3",
        str(LAB_RUNNER_SCRIPT),
        "grade",
        f"--lab={lab_id}",
        "--output-json",
    ]
    if verbose:
        cmd.append("--verbose")

    log.info("running_lab_runner", lab_id=lab_id, cmd=" ".join(cmd))

    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=settings.lab_runner_timeout,
        )
        stdout, stderr = await proc.communicate()
        duration = time.time() - start_time

        log.info(
            "runner_completed",
            lab_id=lab_id,
            returncode=proc.returncode,
            duration_seconds=round(duration, 2),
        )

        if stderr:
            log.debug("runner_stderr", lab_id=lab_id, stderr=stderr.decode()[:1000])

        # Parse the JSON output from the runner
        try:
            result_data = json.loads(stdout.decode())
        except json.JSONDecodeError as exc:
            log.error(
                "runner_output_parse_failed",
                lab_id=lab_id,
                stdout=stdout.decode()[:500],
                error=str(exc),
            )
            return {
                "lab_id": lab_id,
                "status": "error",
                "grade": None,
                "duration_seconds": duration,
                "error": f"Could not parse runner output: {exc}",
            }

        # Build grade result
        validations = [
            ValidationResult(
                check_id=v.get("id", ""),
                description=v.get("description", ""),
                passed=v.get("passed", False),
                message=v.get("message"),
            )
            for v in result_data.get("validations", [])
        ]

        score = result_data.get("score", 0)
        max_score = result_data.get("max_score", 0)
        grade = GradeResult(
            score=score,
            max_score=max_score,
            percentage=round((score / max_score * 100) if max_score > 0 else 0, 1),
            passed=result_data.get("passed", False),
            feedback=result_data.get("feedback", []),
            validation_results=validations,
        )

        status = "completed" if grade.passed else "failed"
        log.info(
            "runner_result",
            lab_id=lab_id,
            status=status,
            score=score,
            max_score=max_score,
            passed=grade.passed,
        )

        return {
            "lab_id": lab_id,
            "status": status,
            "grade": grade.model_dump(),
            "duration_seconds": round(duration, 2),
            "error": None,
        }

    except asyncio.TimeoutError:
        log.error(
            "runner_timeout",
            lab_id=lab_id,
            timeout_seconds=settings.lab_runner_timeout,
        )
        return {
            "lab_id": lab_id,
            "status": "error",
            "grade": None,
            "duration_seconds": settings.lab_runner_timeout,
            "error": f"Lab runner timed out after {settings.lab_runner_timeout}s",
        }
    except Exception as exc:
        log.error("runner_unexpected_error", lab_id=lab_id, error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Runner error: {exc}")


@router.get("/runner/status/{lab_id:path}")
async def get_runner_status(lab_id: str) -> dict:
    """
    Check if a lab's required Docker profiles are running.
    Used by the UI to show 'Start services first' warnings.
    """
    log.debug("runner_status_requested", lab_id=lab_id)
    # Profile checking is done client-side via the services endpoint
    return {"lab_id": lab_id, "check": "see /api/v1/services for running profiles"}
