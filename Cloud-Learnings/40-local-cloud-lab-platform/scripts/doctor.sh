#!/usr/bin/env bash
# scripts/doctor.sh — Check all platform requirements
# Run: make doctor

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

PASS=0
FAIL=0
WARN=0

pass() { log_ok "$*"; PASS=$((PASS + 1)); }
fail() { log_fail "$*"; FAIL=$((FAIL + 1)); }
warn() { log_warn "$*"; WARN=$((WARN + 1)); }

echo ""
echo -e "${BOLD}Local Cloud Lab Platform — Doctor Check${RESET}"
echo "================================================="

# ─────────────────────────────────────────────
# Required tools
# ─────────────────────────────────────────────
log_step "Required Tools"

# Docker
if command -v docker &>/dev/null; then
    DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    if version_gte "$DOCKER_VERSION" "24.0"; then
        pass "Docker $DOCKER_VERSION"
    else
        fail "Docker $DOCKER_VERSION (need 24.0+)"
    fi
else
    fail "Docker not found — install from https://www.docker.com"
fi

# Docker daemon
if docker info &>/dev/null 2>&1; then
    pass "Docker daemon is running"
else
    fail "Docker daemon is NOT running"
fi

# Docker Compose v2
if docker compose version &>/dev/null 2>&1; then
    COMPOSE_VERSION=$(docker compose version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    if version_gte "$COMPOSE_VERSION" "2.20"; then
        pass "Docker Compose v$COMPOSE_VERSION"
    else
        fail "Docker Compose v$COMPOSE_VERSION (need 2.20+)"
    fi
else
    fail "Docker Compose v2 not found"
fi

# Python
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    if version_gte "$PY_VERSION" "3.11"; then
        pass "Python $PY_VERSION"
    else
        fail "Python $PY_VERSION (need 3.11+)"
    fi
else
    fail "Python 3 not found"
fi

# make
if command -v make &>/dev/null; then
    pass "make $(make --version | head -1 | grep -oE '[0-9]+\.[0-9]+')"
else
    fail "make not found"
fi

# curl and jq (used in scripts)
if command -v curl &>/dev/null; then
    pass "curl"
else
    fail "curl not found"
fi

if command -v jq &>/dev/null; then
    pass "jq"
else
    warn "jq not found (optional but recommended)"
fi

# ─────────────────────────────────────────────
# Optional tools (warn, don't fail)
# ─────────────────────────────────────────────
log_step "Optional Tools (for specific lab categories)"

check_optional() {
    local cmd="$1"
    local desc="$2"
    if command -v "$cmd" &>/dev/null; then
        pass "$desc: $(command -v "$cmd")"
    else
        warn "$desc not found (needed for $3 labs)"
    fi
}

check_optional kubectl  "kubectl"    "kubernetes"
check_optional kind     "kind"       "kubernetes"
check_optional helm     "helm"       "kubernetes"
check_optional terraform "terraform" "terraform"
check_optional tofu     "opentofu"   "opentofu"
check_optional ansible  "ansible"    "ansible"
check_optional trivy    "trivy"      "security"
check_optional checkov  "checkov"    "security/iac"
check_optional aws      "aws-cli"    "aws-local"
check_optional az       "azure-cli"  "azure-local"

# ─────────────────────────────────────────────
# System resources
# ─────────────────────────────────────────────
log_step "System Resources"

# RAM
if command -v free &>/dev/null; then
    TOTAL_RAM_MB=$(free -m | awk '/^Mem:/ {print $2}')
elif [[ "$(uname)" == "Darwin" ]]; then
    TOTAL_RAM_MB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 ))
else
    TOTAL_RAM_MB=0
fi

if [[ $TOTAL_RAM_MB -ge 16000 ]]; then
    pass "RAM: ${TOTAL_RAM_MB}MB (sufficient for all profiles)"
elif [[ $TOTAL_RAM_MB -ge 8000 ]]; then
    pass "RAM: ${TOTAL_RAM_MB}MB (sufficient for most profiles, avoid 'all')"
else
    fail "RAM: ${TOTAL_RAM_MB}MB — minimum 8 GB required"
fi

# Disk
DISK_FREE_GB=$(df -BG "$PLATFORM_ROOT" | awk 'NR==2 {gsub("G",""); print $4}')
if [[ "$DISK_FREE_GB" -ge 40 ]]; then
    pass "Free disk: ${DISK_FREE_GB}GB"
elif [[ "$DISK_FREE_GB" -ge 20 ]]; then
    pass "Free disk: ${DISK_FREE_GB}GB (20 GB minimum met, 40 GB recommended)"
else
    fail "Free disk: ${DISK_FREE_GB}GB — need at least 20 GB free"
fi

# ─────────────────────────────────────────────
# Port availability (core ports only)
# ─────────────────────────────────────────────
log_step "Core Port Availability"

PORTS=(
    "3001:Lab UI"
    "4567:Lab API"
    "8080:Traefik"
    "9000:MinIO API"
    "9001:MinIO Console"
)

for entry in "${PORTS[@]}"; do
    port="${entry%%:*}"
    service="${entry##*:}"
    if port_available "$port"; then
        pass "Port $port ($service)"
    else
        fail "Port $port ($service) is already in use"
    fi
done

# ─────────────────────────────────────────────
# .env file
# ─────────────────────────────────────────────
log_step "Configuration"

if [[ -f "$PLATFORM_ROOT/.env" ]]; then
    pass ".env file exists"
else
    warn ".env not found — run: cp .env.example .env"
fi

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
echo ""
echo "================================================="
echo -e "Results: ${GREEN}$PASS passed${RESET}, ${RED}$FAIL failed${RESET}, ${YELLOW}$WARN warnings${RESET}"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}${BOLD}Doctor check FAILED — fix the issues above before continuing${RESET}"
    exit 1
elif [[ $WARN -gt 0 ]]; then
    echo -e "${YELLOW}Doctor check passed with warnings — optional tools missing for some lab categories${RESET}"
    exit 0
else
    echo -e "${GREEN}${BOLD}Doctor check PASSED — ready to run labs!${RESET}"
    exit 0
fi
