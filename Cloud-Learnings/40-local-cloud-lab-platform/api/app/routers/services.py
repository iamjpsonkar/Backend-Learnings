"""
api/app/routers/services.py — Docker service health endpoints
"""

from typing import Optional

import structlog
from fastapi import APIRouter

log = structlog.get_logger(__name__)
router = APIRouter()

# Services to monitor, keyed by container name
MONITORED_SERVICES = {
    "cloud-lab-traefik": {"profile": "core", "url": "http://localhost:8080/ping"},
    "cloud-lab-minio": {"profile": "core", "url": "http://localhost:9000/minio/health/live"},
    "cloud-lab-api": {"profile": "core", "url": "http://localhost:4567/health"},
    "cloud-lab-ui": {"profile": "core", "url": "http://localhost:3001"},
    "cloud-lab-prometheus": {"profile": "observability", "url": None},
    "cloud-lab-grafana": {"profile": "observability", "url": None},
    "cloud-lab-loki": {"profile": "observability", "url": None},
    "cloud-lab-jaeger": {"profile": "observability", "url": None},
    "cloud-lab-otel-collector": {"profile": "observability", "url": None},
    "cloud-lab-vault": {"profile": "security", "url": None},
    "cloud-lab-keycloak": {"profile": "security", "url": None},
    "cloud-lab-gitea": {"profile": "cicd", "url": None},
    "cloud-lab-woodpecker-server": {"profile": "cicd", "url": None},
    "cloud-lab-postgres": {"profile": "data", "url": None},
    "cloud-lab-mongodb": {"profile": "data", "url": None},
    "cloud-lab-redis": {"profile": "data", "url": None},
    "cloud-lab-rabbitmq": {"profile": "data", "url": None},
    "cloud-lab-redpanda": {"profile": "data", "url": None},
    "cloud-lab-localstack": {"profile": "aws-local", "url": None},
    "cloud-lab-azurite": {"profile": "azure-local", "url": None},
}


def _get_docker_client():
    """Get Docker client; returns None if Docker is not available."""
    try:
        import docker
        return docker.from_env()
    except Exception as exc:
        log.warning("docker_client_unavailable", error=str(exc))
        return None


@router.get("/services")
async def get_services(profile: Optional[str] = None) -> dict:
    """
    Get status of all monitored lab services.

    Queries Docker for running containers with the lab platform label.
    Optionally filter by profile.
    """
    log.debug("services_status_requested", profile=profile)

    client = _get_docker_client()
    services_list = []
    running_count = 0

    if client is None:
        log.warning("services_status_docker_unavailable")
        return {
            "services": [],
            "total": 0,
            "running": 0,
            "error": "Docker not available",
        }

    try:
        # Get all containers with the platform label
        containers = client.containers.list(
            all=True,
            filters={"label": "com.cloudlabs.project=local-cloud-lab"},
        )
        container_map = {c.name: c for c in containers}
        log.debug("docker_containers_fetched", count=len(containers))
    except Exception as exc:
        log.error("docker_containers_fetch_failed", error=str(exc))
        return {
            "services": [],
            "total": 0,
            "running": 0,
            "error": f"Docker error: {exc}",
        }

    for container_name, meta in MONITORED_SERVICES.items():
        if profile and meta["profile"] != profile:
            continue

        container = container_map.get(container_name)

        if container is None:
            status = "not_running"
            health = None
            image = None
            ports = []
        else:
            status = container.status  # running, exited, etc.
            health_status = container.attrs.get("State", {}).get("Health", {})
            health = health_status.get("Status") if health_status else None
            image = container.image.tags[0] if container.image.tags else str(container.image.id)[:12]
            raw_ports = container.ports or {}
            ports = [
                f"{host_info[0]['HostPort']}:{internal}"
                for internal, host_info in raw_ports.items()
                if host_info
            ]

        if status == "running":
            running_count += 1

        services_list.append({
            "name": container_name.replace("cloud-lab-", ""),
            "container_name": container_name,
            "profile": meta["profile"],
            "status": status,
            "health": health,
            "image": image,
            "ports": ports,
        })

    log.info(
        "services_status_complete",
        total=len(services_list),
        running=running_count,
        profile=profile,
    )

    return {
        "services": services_list,
        "total": len(services_list),
        "running": running_count,
    }


@router.get("/services/profiles")
async def get_active_profiles() -> dict:
    """
    Return which Docker Compose profiles are currently active
    (i.e., have at least one running container).
    """
    log.debug("active_profiles_requested")

    client = _get_docker_client()
    if client is None:
        return {"profiles": [], "error": "Docker not available"}

    try:
        containers = client.containers.list(
            filters={"label": "com.cloudlabs.project=local-cloud-lab", "status": "running"},
        )
    except Exception as exc:
        log.error("active_profiles_docker_failed", error=str(exc))
        return {"profiles": [], "error": str(exc)}

    running_names = {c.name for c in containers}
    active_profiles = set()

    for container_name, meta in MONITORED_SERVICES.items():
        if container_name in running_names:
            active_profiles.add(meta["profile"])

    profiles = sorted(active_profiles)
    log.info("active_profiles_result", profiles=profiles)
    return {"profiles": profiles}
