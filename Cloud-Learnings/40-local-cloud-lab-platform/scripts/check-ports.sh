#!/usr/bin/env bash
# scripts/check-ports.sh — Verify required ports are available
# Run: make check-ports

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
load_env

echo ""
echo -e "${BOLD}Port Availability Check${RESET}"
echo "=============================="

FAIL=0

declare -A PORTS
PORTS=(
    [3001]="Lab UI"
    [4567]="Lab API"
    [8080]="Traefik Dashboard"
    [9000]="MinIO API"
    [9001]="MinIO Console"
    [9090]="Prometheus"
    [3000]="Grafana"
    [3100]="Loki"
    [16686]="Jaeger UI"
    [8200]="Vault"
    [8888]="Keycloak"
    [18080]="Gitea"
    [18081]="Woodpecker CI"
    [5432]="PostgreSQL"
    [3306]="MySQL"
    [27017]="MongoDB"
    [6379]="Redis"
    [5672]="RabbitMQ"
    [15672]="RabbitMQ Management"
    [9092]="Redpanda (Kafka)"
    [4566]="LocalStack"
    [10000]="Azurite Blob"
    [10001]="Azurite Queue"
    [10002]="Azurite Table"
)

for port in $(echo "${!PORTS[@]}" | tr ' ' '\n' | sort -n); do
    service="${PORTS[$port]}"
    if port_available "$port"; then
        log_ok "Port $port — $service"
    else
        log_fail "Port $port — $service (IN USE)"
        if command -v lsof &>/dev/null; then
            lsof -i :"$port" -sTCP:LISTEN | awk 'NR==2 {printf "          Process: %s (PID %s)\n", $1, $2}'
        fi
        FAIL=$((FAIL + 1))
    fi
done

echo ""
if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}$FAIL port(s) are in use.${RESET}"
    echo "Options:"
    echo "  1. Stop the conflicting process"
    echo "  2. Edit .env to change the port number"
    exit 1
else
    echo -e "${GREEN}All ports are available.${RESET}"
fi
