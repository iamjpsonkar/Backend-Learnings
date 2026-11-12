#!/usr/bin/env bash
# scripts/utils/common.sh — Shared utilities for all lab platform scripts
# Source this file at the top of other scripts: source "$(dirname "$0")/utils/common.sh"

set -euo pipefail

# ─────────────────────────────────────────────
# Color output
# ─────────────────────────────────────────────
BOLD='\033[1m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
BLUE='\033[34m'
RESET='\033[0m'

log_info()    { echo -e "${GREEN}[INFO]${RESET}  $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
log_debug()   { [[ "${LOG_LEVEL:-INFO}" == "DEBUG" ]] && echo -e "${BLUE}[DEBUG]${RESET} $*" || true; }
log_step()    { echo -e "\n${BOLD}==> $*${RESET}"; }
log_ok()      { echo -e "  ${GREEN}[OK]${RESET}  $*"; }
log_fail()    { echo -e "  ${RED}[FAIL]${RESET} $*"; }
log_skip()    { echo -e "  ${YELLOW}[SKIP]${RESET} $*"; }

# ─────────────────────────────────────────────
# Requirement checks
# ─────────────────────────────────────────────
require_command() {
    local cmd="$1"
    local install_hint="${2:-}"
    if ! command -v "$cmd" &>/dev/null; then
        log_error "Required command not found: $cmd"
        [[ -n "$install_hint" ]] && echo "  Install hint: $install_hint"
        return 1
    fi
    log_debug "Found command: $cmd ($(command -v "$cmd"))"
    return 0
}

require_env() {
    local var="$1"
    if [[ -z "${!var:-}" ]]; then
        log_error "Required environment variable not set: $var"
        log_error "Copy .env.example to .env and fill in values"
        exit 1
    fi
}

# ─────────────────────────────────────────────
# Docker helpers
# ─────────────────────────────────────────────
require_docker() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed or not in PATH"
        log_error "See REQUIREMENTS.md for installation instructions"
        exit 1
    fi
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        log_error "Start Docker Desktop or run: sudo systemctl start docker"
        exit 1
    fi
    log_debug "Docker is running"
}

require_docker_compose() {
    if ! docker compose version &>/dev/null; then
        log_error "Docker Compose v2 is not available"
        log_error "Update Docker Desktop or install docker-compose-plugin"
        exit 1
    fi
    log_debug "Docker Compose v2 available"
}

container_running() {
    local name="$1"
    docker ps --filter "name=^${name}$" --filter "status=running" --format "{{.Names}}" | grep -q "^${name}$" 2>/dev/null
}

container_healthy() {
    local name="$1"
    local status
    status=$(docker inspect --format='{{.State.Health.Status}}' "$name" 2>/dev/null || echo "none")
    [[ "$status" == "healthy" ]]
}

wait_for_service() {
    local name="$1"
    local url="$2"
    local max_attempts="${3:-30}"
    local attempt=0

    log_info "Waiting for $name to be ready..."
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -sf "$url" &>/dev/null; then
            log_ok "$name is ready ($url)"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    log_fail "$name did not become ready after $((max_attempts * 2))s ($url)"
    return 1
}

# ─────────────────────────────────────────────
# Platform paths
# ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

load_env() {
    local env_file="$PLATFORM_ROOT/.env"
    if [[ -f "$env_file" ]]; then
        log_debug "Loading environment from $env_file"
        set -a
        # shellcheck disable=SC1090
        source "$env_file"
        set +a
    else
        log_warn ".env file not found at $env_file"
        log_warn "Run: cp .env.example .env"
    fi
}

# ─────────────────────────────────────────────
# Confirmation prompt
# ─────────────────────────────────────────────
confirm_destructive() {
    local message="${1:-This is a destructive operation}"
    if [[ "${1:-}" == "--confirm" ]] || [[ "${CONFIRM:-}" == "yes" ]]; then
        log_debug "Destructive operation auto-confirmed via flag"
        return 0
    fi
    log_warn "$message"
    echo -n "Type 'yes' to confirm: "
    read -r answer
    if [[ "$answer" != "yes" ]]; then
        log_info "Cancelled"
        exit 0
    fi
}

# ─────────────────────────────────────────────
# Version checks
# ─────────────────────────────────────────────
version_gte() {
    # Returns 0 if version $1 >= required version $2
    local current="$1"
    local required="$2"
    printf '%s\n%s\n' "$required" "$current" | sort -V -C
}

check_min_version() {
    local tool="$1"
    local current_version="$2"
    local min_version="$3"
    if version_gte "$current_version" "$min_version"; then
        log_ok "$tool $current_version (>= $min_version required)"
        return 0
    else
        log_fail "$tool $current_version is below minimum required $min_version"
        return 1
    fi
}

# ─────────────────────────────────────────────
# Port availability check
# ─────────────────────────────────────────────
port_available() {
    local port="$1"
    ! lsof -i :"$port" -sTCP:LISTEN &>/dev/null
}

check_port() {
    local port="$1"
    local service="${2:-unknown}"
    if port_available "$port"; then
        log_ok "Port $port available ($service)"
        return 0
    else
        log_fail "Port $port is in use ($service)"
        lsof -i :"$port" -sTCP:LISTEN | tail -1 || true
        return 1
    fi
}
