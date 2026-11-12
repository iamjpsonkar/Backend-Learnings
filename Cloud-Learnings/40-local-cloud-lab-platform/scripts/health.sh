#!/usr/bin/env bash
# scripts/health.sh — Check health of all running lab services
# Run: make health

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
load_env

echo ""
echo -e "${BOLD}Service Health Check${RESET}"
echo "=============================="

PASS=0
FAIL=0
SKIP=0

check_http() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    if ! docker ps --filter "name=${name}" --filter "status=running" --format "{{.Names}}" | grep -q "${name}" 2>/dev/null; then
        log_skip "$name (not running)"
        SKIP=$((SKIP + 1))
        return 0
    fi
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    if [[ "$status" == "$expected_status" ]] || [[ "$status" == "200" ]]; then
        log_ok "$name — $url"
        PASS=$((PASS + 1))
    else
        log_fail "$name — $url (HTTP $status)"
        FAIL=$((FAIL + 1))
    fi
}

check_tcp() {
    local name="$1"
    local host="$2"
    local port="$3"
    if ! docker ps --filter "name=${name}" --filter "status=running" --format "{{.Names}}" | grep -q "${name}" 2>/dev/null; then
        log_skip "$name (not running)"
        SKIP=$((SKIP + 1))
        return 0
    fi
    if nc -z -w3 "$host" "$port" 2>/dev/null; then
        log_ok "$name — $host:$port"
        PASS=$((PASS + 1))
    else
        log_fail "$name — $host:$port (not reachable)"
        FAIL=$((FAIL + 1))
    fi
}

log_step "Core Services"
check_http "lab-api"    "http://localhost:${LAB_API_PORT:-4567}/health"
check_http "lab-ui"     "http://localhost:${LAB_UI_PORT:-3001}"
check_http "minio"      "http://localhost:${MINIO_CONSOLE_PORT:-9001}"
check_http "traefik"    "http://localhost:${TRAEFIK_DASHBOARD_PORT:-8080}/ping"

log_step "Observability"
check_http "prometheus"    "http://localhost:${PROMETHEUS_PORT:-9090}/-/ready"
check_http "grafana"       "http://localhost:${GRAFANA_PORT:-3000}/api/health"
check_http "loki"          "http://localhost:${LOKI_PORT:-3100}/ready"
check_http "jaeger"        "http://localhost:${JAEGER_UI_PORT:-16686}"

log_step "Security"
check_http "vault"         "http://localhost:${VAULT_PORT:-8200}/v1/sys/health"
check_http "keycloak"      "http://localhost:${KEYCLOAK_PORT:-8888}/health/ready"

log_step "CI/CD"
check_http "gitea"         "http://localhost:${GITEA_PORT:-18080}"
check_http "woodpecker"    "http://localhost:${WOODPECKER_PORT:-18081}"

log_step "Data Services"
check_tcp "postgres"      "localhost" "${POSTGRES_PORT:-5432}"
check_tcp "mongodb"       "localhost" "${MONGODB_PORT:-27017}"
check_tcp "redis"         "localhost" "${REDIS_PORT:-6379}"
check_tcp "rabbitmq"      "localhost" "${RABBITMQ_PORT:-5672}"
check_tcp "redpanda"      "localhost" "${REDPANDA_KAFKA_PORT:-9092}"

log_step "Cloud Emulators"
check_http "localstack"   "http://localhost:${LOCALSTACK_PORT:-4566}/health"
check_tcp  "azurite"      "localhost" "${AZURITE_PORT:-10000}"

echo ""
echo "=============================="
echo -e "Results: ${GREEN}$PASS healthy${RESET}, ${RED}$FAIL unhealthy${RESET}, ${YELLOW}$SKIP not running${RESET}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${YELLOW}Some services are unhealthy. Run: make logs SERVICE=<name>${RESET}"
    exit 1
fi
