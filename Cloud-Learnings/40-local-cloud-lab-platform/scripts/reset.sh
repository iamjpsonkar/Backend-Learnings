#!/usr/bin/env bash
# scripts/reset.sh — Full platform reset: stops all, removes volumes, wipes DB
# DESTRUCTIVE: all lab progress and service data will be lost
# Run: make reset   (prompts for confirmation)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
load_env

echo ""
echo -e "${RED}${BOLD}FULL PLATFORM RESET${RESET}"
echo "This will:"
echo "  - Stop all lab Docker services"
echo "  - Remove all Docker volumes (ALL data will be lost)"
echo "  - Delete the lab progress database"
echo "  - Remove the Python virtual environment"
echo ""
echo -e "${RED}All lab progress, database data, and credentials will be lost.${RESET}"
echo ""

if [[ "${1:-}" != "--confirm" ]] && [[ "${CONFIRM:-}" != "yes" ]]; then
    echo -n "Type 'yes' to confirm full reset: "
    read -r answer
    if [[ "$answer" != "yes" ]]; then
        log_info "Reset cancelled"
        exit 0
    fi
fi

log_step "Stopping all services"
docker compose \
    -f "$PLATFORM_ROOT/docker-compose.yml" \
    -f "$PLATFORM_ROOT/docker-compose.observability.yml" \
    -f "$PLATFORM_ROOT/docker-compose.security.yml" \
    -f "$PLATFORM_ROOT/docker-compose.cicd.yml" \
    -f "$PLATFORM_ROOT/docker-compose.data.yml" \
    -f "$PLATFORM_ROOT/docker-compose.aws-local.yml" \
    -f "$PLATFORM_ROOT/docker-compose.azure-local.yml" \
    down -v 2>/dev/null || true
log_ok "Services stopped"

log_step "Running cleanup"
bash "$SCRIPT_DIR/cleanup.sh" --confirm

log_step "Removing database"
DB_PATH="${DB_PATH:-$PLATFORM_ROOT/api/data/lab_platform.db}"
rm -f "$DB_PATH" "${DB_PATH}-shm" "${DB_PATH}-wal"
log_ok "Database removed"

log_step "Removing virtual environment"
rm -rf "$PLATFORM_ROOT/.venv"
log_ok "Virtual environment removed"

log_step "Cleaning reports"
rm -f "$PLATFORM_ROOT"/reports/*.json "$PLATFORM_ROOT"/reports/*.html
log_ok "Reports cleaned"

echo ""
log_ok "Full reset complete."
echo ""
echo "To start fresh: make setup"
