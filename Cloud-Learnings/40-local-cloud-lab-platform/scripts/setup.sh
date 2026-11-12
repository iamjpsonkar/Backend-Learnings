#!/usr/bin/env bash
# scripts/setup.sh — First-time platform setup
# Run once before starting labs: make setup

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/utils/common.sh"

log_step "Local Cloud Lab Platform — First-Time Setup"
echo "Platform root: $PLATFORM_ROOT"
echo ""

# ─────────────────────────────────────────────
# 1. Check requirements
# ─────────────────────────────────────────────
log_step "Checking requirements"
bash "$SCRIPT_DIR/doctor.sh" || {
    log_error "Doctor check failed. Fix the issues above before proceeding."
    exit 1
}

# ─────────────────────────────────────────────
# 2. Copy .env if not present
# ─────────────────────────────────────────────
log_step "Environment file"
if [[ ! -f "$PLATFORM_ROOT/.env" ]]; then
    log_info "Creating .env from .env.example"
    cp "$PLATFORM_ROOT/.env.example" "$PLATFORM_ROOT/.env"
    log_ok ".env created — review and edit if needed"
else
    log_ok ".env already exists"
fi

load_env

# ─────────────────────────────────────────────
# 3. Create Python venv for API and lab runner
# ─────────────────────────────────────────────
log_step "Python virtual environment"
VENV_DIR="$PLATFORM_ROOT/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    log_info "Creating Python venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    log_ok "venv created"
else
    log_ok "venv already exists at $VENV_DIR"
fi

log_info "Installing API dependencies"
"$VENV_DIR/bin/pip" install -q --upgrade pip
"$VENV_DIR/bin/pip" install -q -r "$PLATFORM_ROOT/api/requirements.txt"
log_ok "API dependencies installed"

log_info "Installing lab runner dependencies"
"$VENV_DIR/bin/pip" install -q -r "$PLATFORM_ROOT/lab-runner/requirements.txt"
log_ok "Lab runner dependencies installed"

# ─────────────────────────────────────────────
# 4. Create required directories
# ─────────────────────────────────────────────
log_step "Creating required directories"
mkdir -p "$PLATFORM_ROOT/api/data"
mkdir -p "$PLATFORM_ROOT/reports"
mkdir -p "$PLATFORM_ROOT/logs"
log_ok "Directories created"

# ─────────────────────────────────────────────
# 5. Initialize the database
# ─────────────────────────────────────────────
log_step "Initializing database"
bash "$SCRIPT_DIR/init-db.sh"
log_ok "Database initialized"

# ─────────────────────────────────────────────
# 6. Validate lab definitions
# ─────────────────────────────────────────────
log_step "Validating lab definitions"
"$VENV_DIR/bin/python3" "$PLATFORM_ROOT/lab-runner/runner.py" validate-all 2>&1 | tail -5
log_ok "Lab definitions validated"

# ─────────────────────────────────────────────
# 7. Create Docker network
# ─────────────────────────────────────────────
log_step "Docker network"
if ! docker network inspect cloud-lab-network &>/dev/null; then
    docker network create cloud-lab-network \
        --label "com.cloudlabs.project=local-cloud-lab" \
        --subnet 172.20.0.0/16
    log_ok "Docker network cloud-lab-network created"
else
    log_ok "Docker network cloud-lab-network already exists"
fi

# ─────────────────────────────────────────────
# 8. Pull core images (optional, speeds up first start)
# ─────────────────────────────────────────────
log_step "Pulling core Docker images"
log_info "This may take a few minutes on first run..."
docker compose -f "$PLATFORM_ROOT/docker-compose.yml" --profile core pull --quiet || {
    log_warn "Could not pre-pull images (will pull on first start)"
}

# ─────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}Setup complete!${RESET}"
echo ""
echo "Next steps:"
echo "  1. make start-core    — start the core services"
echo "  2. open http://localhost:${LAB_UI_PORT:-3001}"
echo "  3. make list-labs     — browse available labs"
echo "  4. make run-lab LAB=00-foundations/platform-orientation"
echo ""
