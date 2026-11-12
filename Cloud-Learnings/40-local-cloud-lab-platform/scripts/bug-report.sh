#!/usr/bin/env bash
# scripts/bug-report.sh — Gather diagnostic info for bug reports
# Run: make bug-report   (output is safe to share — no secrets logged)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

REPORT_FILE="$PLATFORM_ROOT/reports/bug-report-$(date +%Y%m%d-%H%M%S).txt"
mkdir -p "$PLATFORM_ROOT/reports"

{
    echo "Local Cloud Lab Platform — Bug Report"
    echo "Generated: $(date -u)"
    echo "============================================"
    echo ""

    echo "## Platform Info"
    echo "Platform root: $PLATFORM_ROOT"
    uname -a
    echo ""

    echo "## Tool Versions"
    docker --version 2>/dev/null || echo "docker: not found"
    docker compose version 2>/dev/null || echo "docker compose: not found"
    python3 --version 2>/dev/null || echo "python3: not found"
    make --version 2>/dev/null | head -1 || echo "make: not found"
    kubectl version --client 2>/dev/null | head -1 || echo "kubectl: not found"
    kind --version 2>/dev/null || echo "kind: not found"
    terraform --version 2>/dev/null | head -1 || echo "terraform: not found"
    echo ""

    echo "## Docker Info (sanitized)"
    docker info 2>/dev/null | grep -E "Version|Server Version|Operating|Architecture|CPUs|Total Memory|Storage Driver" || echo "Docker not available"
    echo ""

    echo "## Running Lab Containers"
    docker ps --filter "label=com.cloudlabs.project=local-cloud-lab" \
        --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" 2>/dev/null || echo "None running"
    echo ""

    echo "## Container Health"
    docker ps --filter "label=com.cloudlabs.project=local-cloud-lab" \
        --format "{{.Names}}" 2>/dev/null | while read -r name; do
        health=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "no healthcheck")
        echo "  $name: $health"
    done
    echo ""

    echo "## Port Usage (relevant ports only)"
    for port in 3001 4567 8080 9000 9001 9090 3000 16686 8200 8888 18080 18081 5432 27017 6379 4566; do
        if lsof -i :"$port" -sTCP:LISTEN &>/dev/null 2>&1; then
            process=$(lsof -i :"$port" -sTCP:LISTEN 2>/dev/null | awk 'NR==2 {print $1, "(PID:"$2")"}')
            echo "  Port $port: IN USE by $process"
        fi
    done
    echo ""

    echo "## .env Config (secrets redacted)"
    if [[ -f "$PLATFORM_ROOT/.env" ]]; then
        grep -v "PASSWORD\|SECRET\|TOKEN\|KEY" "$PLATFORM_ROOT/.env" | grep -v "^#" | grep -v "^$" || true
        grep -E "PASSWORD|SECRET|TOKEN|KEY" "$PLATFORM_ROOT/.env" | sed 's/=.*/=***REDACTED***/' || true
    else
        echo ".env not found"
    fi
    echo ""

    echo "## Disk Usage"
    df -h "$PLATFORM_ROOT" 2>/dev/null || true
    docker system df 2>/dev/null || true
    echo ""

    echo "## Recent Docker Logs (last 20 lines per running container)"
    docker ps --filter "label=com.cloudlabs.project=local-cloud-lab" \
        --format "{{.Names}}" 2>/dev/null | while read -r name; do
        echo "--- $name ---"
        docker logs --tail=20 "$name" 2>&1 | grep -v "password\|secret\|token" || true
        echo ""
    done

} > "$REPORT_FILE"

echo ""
log_ok "Bug report saved to: $REPORT_FILE"
echo ""
echo "Review the file before sharing to confirm no sensitive data is included."
echo "Then attach it when opening a GitHub issue."
