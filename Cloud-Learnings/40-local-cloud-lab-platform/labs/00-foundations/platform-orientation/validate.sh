#!/usr/bin/env bash
# Validate lab: platform-orientation
set -euo pipefail

VALIDATOR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/lab-runner/validators"

check_http() {
    local desc="$1"
    local url="$2"
    local grep_pattern="${3:-}"
    if curl -sf --max-time 5 "$url" | grep -qi "${grep_pattern:-}" &>/dev/null; then
        echo "PASS: $desc"
    else
        echo "FAIL: $desc ($url not reachable or pattern not found)"
    fi
}

check_docker_running() {
    local desc="$1"
    local name="$2"
    if docker ps --filter "name=$name" --filter "status=running" --format "{{.Names}}" | grep -q "$name"; then
        echo "PASS: $desc"
    else
        echo "FAIL: $desc (container $name not running)"
    fi
}

check_http "Lab API health endpoint" "http://localhost:4567/health" "ok"
check_http "Lab UI dashboard" "http://localhost:3001" ""
check_http "MinIO console" "http://localhost:9001" ""
check_docker_running "Lab API container running" "cloud-lab-api"
check_docker_running "MinIO container running" "cloud-lab-minio"
check_docker_running "Traefik container running" "cloud-lab-traefik"

# Check make list-labs works
if make -C "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)" list-labs &>/dev/null; then
    echo "PASS: make list-labs executes successfully"
else
    echo "FAIL: make list-labs failed"
fi
