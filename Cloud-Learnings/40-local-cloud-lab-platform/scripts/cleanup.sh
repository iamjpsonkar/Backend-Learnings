#!/usr/bin/env bash
# scripts/cleanup.sh — Remove all Docker resources belonging to the lab platform
# Only removes resources labelled com.cloudlabs.project=local-cloud-lab
# Run: make cleanup   (prompts for confirmation)
#      make cleanup --confirm   (skips prompt)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
load_env

LABEL="com.cloudlabs.project=local-cloud-lab"

echo ""
echo -e "${BOLD}Lab Platform Cleanup${RESET}"
echo "This will remove Docker containers, networks, and volumes"
echo "labelled: $LABEL"
echo ""
echo -e "${YELLOW}Your other Docker resources are NOT affected.${RESET}"
echo ""

# Require confirmation
if [[ "${1:-}" != "--confirm" ]] && [[ "${CONFIRM:-}" != "yes" ]]; then
    echo -n "Type 'yes' to continue: "
    read -r answer
    if [[ "$answer" != "yes" ]]; then
        log_info "Cleanup cancelled"
        exit 0
    fi
fi

# ─────────────────────────────────────────────
# Stop and remove containers
# ─────────────────────────────────────────────
log_step "Stopping containers"
CONTAINERS=$(docker ps -a --filter "label=$LABEL" --format "{{.ID}}" 2>/dev/null || true)
if [[ -n "$CONTAINERS" ]]; then
    echo "$CONTAINERS" | xargs docker stop --time=10 2>/dev/null || true
    echo "$CONTAINERS" | xargs docker rm 2>/dev/null || true
    log_ok "Containers removed"
else
    log_info "No lab containers found"
fi

# ─────────────────────────────────────────────
# Remove volumes
# ─────────────────────────────────────────────
log_step "Removing volumes"
VOLUMES=$(docker volume ls --filter "label=$LABEL" --format "{{.Name}}" 2>/dev/null || true)
if [[ -n "$VOLUMES" ]]; then
    echo "$VOLUMES" | xargs docker volume rm 2>/dev/null || true
    log_ok "Volumes removed"
else
    log_info "No lab volumes found"
fi

# ─────────────────────────────────────────────
# Remove networks (except default docker ones)
# ─────────────────────────────────────────────
log_step "Removing networks"
NETWORKS=$(docker network ls --filter "label=$LABEL" --format "{{.Name}}" 2>/dev/null || true)
if [[ -n "$NETWORKS" ]]; then
    echo "$NETWORKS" | xargs docker network rm 2>/dev/null || true
    log_ok "Networks removed"
else
    log_info "No lab networks found"
fi

echo ""
log_ok "Cleanup complete. Your other Docker resources are untouched."
echo ""
echo "To rebuild: make setup && make start-core"
