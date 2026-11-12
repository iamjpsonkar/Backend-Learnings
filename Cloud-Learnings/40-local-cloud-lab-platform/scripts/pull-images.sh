#!/usr/bin/env bash
# scripts/pull-images.sh — Pre-pull all Docker images for offline use
# Run: make pull

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

echo ""
log_step "Pre-pulling Docker images (this may take a while)"
echo "Tip: You can interrupt with Ctrl+C — images already pulled are cached"
echo ""

pull_image() {
    local image="$1"
    local desc="${2:-$image}"
    echo -n "  Pulling $desc... "
    if docker pull "$image" --quiet 2>/dev/null; then
        echo -e "${GREEN}done${RESET}"
    else
        echo -e "${YELLOW}failed (will retry on start)${RESET}"
    fi
}

log_info "Core images"
pull_image "minio/minio:RELEASE.2024-01-01T00-00-00Z" "MinIO"
pull_image "traefik:v3.0" "Traefik"
pull_image "nginx:alpine" "Nginx"

log_info "Observability images"
pull_image "prom/prometheus:v2.49.0" "Prometheus"
pull_image "grafana/grafana:10.2.0" "Grafana"
pull_image "grafana/loki:2.9.0" "Loki"
pull_image "grafana/promtail:2.9.0" "Promtail"
pull_image "jaegertracing/all-in-one:1.52" "Jaeger"
pull_image "otel/opentelemetry-collector-contrib:0.91.0" "OTel Collector"

log_info "Security images"
pull_image "hashicorp/vault:1.15" "Vault"
pull_image "quay.io/keycloak/keycloak:23.0" "Keycloak"

log_info "Data images"
pull_image "postgres:16-alpine" "PostgreSQL"
pull_image "mongo:7.0" "MongoDB"
pull_image "redis:7-alpine" "Redis"
pull_image "rabbitmq:3.12-management-alpine" "RabbitMQ"
pull_image "redpandadata/redpanda:v23.3.1" "Redpanda"

log_info "CI/CD images"
pull_image "gitea/gitea:1.21" "Gitea"
pull_image "woodpeckerci/woodpecker-server:v1.0" "Woodpecker Server"
pull_image "woodpeckerci/woodpecker-agent:v1.0" "Woodpecker Agent"

log_info "Cloud emulator images"
pull_image "localstack/localstack:3.0" "LocalStack"
pull_image "mcr.microsoft.com/azure-storage/azurite:3.28.0" "Azurite"

echo ""
log_ok "Image pull complete. Platform is ready for offline use."
echo ""
echo "Disk usage after pull:"
docker system df
