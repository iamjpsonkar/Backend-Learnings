"""
lab-runner/validators/docker_validator.py — Docker validation helpers

Used by validate.sh scripts via: python3 -m validators.docker_validator <check>
Or imported directly in grade.sh output processors.
"""

import subprocess
import sys
import json


def container_running(name: str) -> tuple[bool, str]:
    """Check if a Docker container is running by name or partial name."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={name}", "--filter", "status=running",
             "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10,
        )
        names = result.stdout.strip().splitlines()
        running = any(name in n for n in names)
        msg = f"Container '{name}' is {'running' if running else 'not running'}"
        return running, msg
    except Exception as exc:
        return False, f"Docker check failed: {exc}"


def image_exists(image_ref: str) -> tuple[bool, str]:
    """Check if a Docker image exists locally."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image_ref],
            capture_output=True, text=True, timeout=10,
        )
        exists = result.returncode == 0
        return exists, f"Image '{image_ref}' {'found' if exists else 'not found'}"
    except Exception as exc:
        return False, f"Image check failed: {exc}"


def container_healthy(name: str) -> tuple[bool, str]:
    """Check if a container's healthcheck is passing."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", name],
            capture_output=True, text=True, timeout=10,
        )
        status = result.stdout.strip()
        healthy = status == "healthy"
        return healthy, f"Container '{name}' health: {status or 'unknown'}"
    except Exception as exc:
        return False, f"Health check failed: {exc}"


def volume_exists(volume_name: str) -> tuple[bool, str]:
    """Check if a Docker volume exists."""
    try:
        result = subprocess.run(
            ["docker", "volume", "inspect", volume_name],
            capture_output=True, text=True, timeout=10,
        )
        exists = result.returncode == 0
        return exists, f"Volume '{volume_name}' {'exists' if exists else 'not found'}"
    except Exception as exc:
        return False, f"Volume check failed: {exc}"


def network_exists(network_name: str) -> tuple[bool, str]:
    """Check if a Docker network exists."""
    try:
        result = subprocess.run(
            ["docker", "network", "inspect", network_name],
            capture_output=True, text=True, timeout=10,
        )
        exists = result.returncode == 0
        return exists, f"Network '{network_name}' {'exists' if exists else 'not found'}"
    except Exception as exc:
        return False, f"Network check failed: {exc}"


def container_log_contains(name: str, pattern: str, lines: int = 100) -> tuple[bool, str]:
    """Check if container logs contain a pattern."""
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), name],
            capture_output=True, text=True, timeout=15,
        )
        found = pattern in result.stdout or pattern in result.stderr
        return found, f"Pattern '{pattern}' {'found' if found else 'not found'} in {name} logs"
    except Exception as exc:
        return False, f"Log check failed: {exc}"


if __name__ == "__main__":
    """CLI interface: python3 docker_validator.py <check> <args...>"""
    if len(sys.argv) < 3:
        print("Usage: docker_validator.py <check> <arg>", file=sys.stderr)
        sys.exit(1)

    check = sys.argv[1]
    arg = sys.argv[2]
    extra = sys.argv[3] if len(sys.argv) > 3 else None

    checks = {
        "container-running": container_running,
        "image-exists": image_exists,
        "container-healthy": container_healthy,
        "volume-exists": volume_exists,
        "network-exists": network_exists,
    }

    fn = checks.get(check)
    if fn is None:
        print(f"Unknown check: {check}. Available: {list(checks.keys())}", file=sys.stderr)
        sys.exit(1)

    if extra:
        passed, msg = fn(arg, extra)
    else:
        passed, msg = fn(arg)

    print(msg)
    sys.exit(0 if passed else 1)
