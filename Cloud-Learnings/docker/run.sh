#!/usr/bin/env bash
# =============================================================================
# Cloud-Learnings Lab Platform — run.sh
# Main control script for the Docker-based cloud practice platform
#
# Usage:
#   ./run.sh                    Interactive menu
#   ./run.sh <command> [args]   Direct command
#   ./run.sh --help             Show help
#
# Project: cloud-learnings-lab
# =============================================================================

set -euo pipefail

# Change to script directory so compose paths always resolve correctly
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# =============================================================================
# Constants
# =============================================================================
readonly PROJECT_NAME="cloud-learnings-lab"
readonly COMPOSE_FILE="docker-compose.yml"
readonly ENV_FILE=".env"
readonly ENV_EXAMPLE=".env.example"
readonly LAB_INDEX="labs/lab-index.yaml"
readonly LABEL_FILTER="com.cloudlearnings.project=cloud-learnings-lab"
readonly VERSION="1.0.0"

# =============================================================================
# Color output
# =============================================================================
if [[ -t 1 ]] && [[ "${NO_COLOR:-}" != "true" ]] && command -v tput &>/dev/null; then
  RED=$(tput setaf 1)
  GREEN=$(tput setaf 2)
  YELLOW=$(tput setaf 3)
  BLUE=$(tput setaf 4)
  CYAN=$(tput setaf 6)
  BOLD=$(tput bold)
  RESET=$(tput sgr0)
else
  RED="" GREEN="" YELLOW="" BLUE="" CYAN="" BOLD="" RESET=""
fi

# =============================================================================
# Logging helpers
# =============================================================================
log_info()    { echo "${GREEN}[INFO]${RESET}  $*"; }
log_warn()    { echo "${YELLOW}[WARN]${RESET}  $*"; }
log_error()   { echo "${RED}[ERROR]${RESET} $*" >&2; }
log_debug()   { [[ "${VERBOSE:-false}" == "true" ]] && echo "${CYAN}[DEBUG]${RESET} $*" || true; }
log_step()    { echo "${BOLD}${BLUE}==> $*${RESET}"; }
log_success() { echo "${GREEN}${BOLD}[OK]${RESET}   $*"; }
log_fail()    { echo "${RED}${BOLD}[FAIL]${RESET} $*" >&2; }
log_header()  {
  echo ""
  echo "${BOLD}${CYAN}============================================================${RESET}"
  echo "${BOLD}${CYAN}  $*${RESET}"
  echo "${BOLD}${CYAN}============================================================${RESET}"
  echo ""
}

# =============================================================================
# Global flags
# =============================================================================
VERBOSE="${VERBOSE:-false}"
DRY_RUN="${DRY_RUN:-false}"
YES="${YES:-false}"

# =============================================================================
# Parse global flags (strip from args before processing command)
# =============================================================================
parse_global_flags() {
  local args=()
  for arg in "$@"; do
    case "$arg" in
      --verbose|-v) VERBOSE=true ;;
      --dry-run)    DRY_RUN=true ;;
      --yes|-y)     YES=true ;;
      *)            args+=("$arg") ;;
    esac
  done
  echo "${args[@]:-}"
}

# =============================================================================
# Load .env if present
# =============================================================================
load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    log_debug "Loading $ENV_FILE"
    # Export variables from .env (skip comments and blank lines)
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
}

# =============================================================================
# Dry-run wrapper
# =============================================================================
run_cmd() {
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "${YELLOW}[DRY-RUN]${RESET} $*"
    return 0
  fi
  log_debug "Running: $*"
  "$@"
}

# =============================================================================
# Docker Compose wrapper — always uses project name and file
# =============================================================================
dc() {
  run_cmd docker compose \
    --project-name "$PROJECT_NAME" \
    --file "$COMPOSE_FILE" \
    "$@"
}

dc_profile() {
  # Usage: dc_profile "profile1 profile2" up -d
  local profiles="$1"
  shift
  local profile_args=()
  for p in $profiles; do
    profile_args+=(--profile "$p")
  done
  run_cmd docker compose \
    --project-name "$PROJECT_NAME" \
    --file "$COMPOSE_FILE" \
    "${profile_args[@]}" \
    "$@"
}

# =============================================================================
# Confirmation prompt
# =============================================================================
confirm() {
  local prompt="${1:-Are you sure?}"
  if [[ "$YES" == "true" ]]; then
    log_debug "Auto-confirmed (--yes flag)"
    return 0
  fi
  echo -n "${YELLOW}${prompt} [y/N]: ${RESET}"
  read -r answer
  case "$answer" in
    [yY][eE][sS]|[yY]) return 0 ;;
    *) return 1 ;;
  esac
}

# =============================================================================
# Prerequisites check
# =============================================================================
cmd_doctor() {
  log_header "Doctor — Checking Prerequisites"
  local all_ok=true

  # Docker
  echo -n "  Docker installed:         "
  if command -v docker &>/dev/null; then
    local docker_ver
    docker_ver=$(docker --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    log_success "docker $docker_ver"
  else
    log_fail "docker not found — install Docker Desktop or Docker Engine"
    all_ok=false
  fi

  # Docker daemon running
  echo -n "  Docker daemon running:    "
  if docker info &>/dev/null 2>&1; then
    log_success "running"
  else
    log_fail "daemon not running — start Docker Desktop or run: sudo systemctl start docker"
    all_ok=false
  fi

  # Docker Compose v2
  echo -n "  Docker Compose v2:        "
  if docker compose version &>/dev/null 2>&1; then
    local compose_ver
    compose_ver=$(docker compose version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    log_success "compose $compose_ver"
  else
    log_fail "docker compose v2 not found — update Docker Desktop or install compose plugin"
    all_ok=false
  fi

  # Available memory
  echo -n "  Available memory:         "
  local mem_free
  if [[ "$(uname)" == "Darwin" ]]; then
    # macOS: use vm_stat and pagesize
    local pages_free pages_inactive page_size
    pages_free=$(vm_stat 2>/dev/null | grep "Pages free" | awk '{print $3}' | tr -d '.')
    pages_inactive=$(vm_stat 2>/dev/null | grep "Pages inactive" | awk '{print $3}' | tr -d '.')
    page_size=$(pagesize 2>/dev/null || echo 4096)
    mem_free=$(( (${pages_free:-0} + ${pages_inactive:-0}) * page_size / 1024 / 1024 ))
  else
    mem_free=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)
  fi
  if [[ "$mem_free" -ge 4096 ]]; then
    log_success "${mem_free} MB free"
  elif [[ "$mem_free" -ge 2048 ]]; then
    log_warn "${mem_free} MB free — minimum met but tight; only run core profile"
  else
    log_fail "${mem_free} MB free — below 2GB; some services will fail"
    all_ok=false
  fi

  # Disk space
  echo -n "  Available disk space:     "
  local disk_free
  disk_free=$(df -k "$SCRIPT_DIR" 2>/dev/null | awk 'NR==2 {print int($4/1024)}' || echo 0)
  if [[ "$disk_free" -ge 10240 ]]; then
    log_success "${disk_free} MB free"
  elif [[ "$disk_free" -ge 5120 ]]; then
    log_warn "${disk_free} MB free — minimum met; avoid starting all profiles"
  else
    log_fail "${disk_free} MB free — below 5GB; may fail on image pulls"
    all_ok=false
  fi

  # .env file
  echo -n "  .env file:                "
  if [[ -f "$ENV_FILE" ]]; then
    log_success "present"
  else
    log_warn "missing — run: ./run.sh setup"
  fi

  # Port checks
  echo ""
  log_step "Checking key ports..."
  local ports=(80 443 3000 3001 4566 5432 6379 8080 8200 9090)
  for port in "${ports[@]}"; do
    echo -n "  Port $port: "
    if command -v lsof &>/dev/null; then
      if lsof -i ":$port" -sTCP:LISTEN &>/dev/null 2>&1; then
        log_warn "IN USE — may conflict (edit .env to change port)"
      else
        log_success "available"
      fi
    else
      echo "  (lsof not available — skipping port check)"
      break
    fi
  done

  # Optional tools
  echo ""
  log_step "Optional tools..."
  for tool in kind k3d kubectl helm jq yq; do
    echo -n "  $tool: "
    if command -v "$tool" &>/dev/null; then
      log_success "installed"
    else
      log_warn "not installed (needed for kubernetes labs)"
    fi
  done

  echo ""
  if [[ "$all_ok" == "true" ]]; then
    log_success "All required checks passed. Platform is ready."
  else
    log_error "Some checks failed. Fix the above issues before starting."
    return 1
  fi
}

# =============================================================================
# Setup — create .env from .env.example
# =============================================================================
cmd_setup() {
  log_header "Setup"
  if [[ -f "$ENV_FILE" ]]; then
    log_warn ".env already exists."
    if ! confirm "Overwrite .env with defaults from .env.example?"; then
      log_info "Setup cancelled. Existing .env kept."
      return 0
    fi
  fi
  if [[ ! -f "$ENV_EXAMPLE" ]]; then
    log_error ".env.example not found. Cannot create .env."
    return 1
  fi
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  log_success ".env created from .env.example"
  log_info "Review and adjust .env before starting services."
  log_info "All credentials are fake and local-only by default."
}

# =============================================================================
# Profile mapping — translate friendly names to compose profiles
# =============================================================================
resolve_profiles() {
  local input="${1:-core}"
  case "$input" in
    core)          echo "core" ;;
    dashboard)     echo "core dashboard" ;;
    data)          echo "core data" ;;
    messaging)     echo "core messaging" ;;
    aws)           echo "core aws" ;;
    azure)         echo "core azure" ;;
    gcp)           echo "core gcp" ;;
    cloud)         echo "core aws azure gcp cloud" ;;
    observability) echo "core observability" ;;
    security)      echo "core security" ;;
    cicd)          echo "core cicd" ;;
    iac)           echo "core iac" ;;
    apps)          echo "core apps" ;;
    kubernetes)    echo "core kubernetes" ;;
    all)           echo "core dashboard data messaging aws azure gcp cloud observability security cicd iac apps" ;;
    *)
      # Allow passing raw profile name(s) directly
      echo "$input"
      ;;
  esac
}

# =============================================================================
# Resource warning for heavy profiles
# =============================================================================
resource_warning() {
  local profile="$1"
  case "$profile" in
    observability|security|cicd|cloud|all)
      log_warn "Profile '${profile}' is resource-heavy."
      log_warn "Recommended: 8-16 GB RAM, 4+ CPUs, 30+ GB disk free."
      log_warn "Use Docker Desktop Resources settings to increase limits if needed."
      echo ""
      ;;
  esac
}

# =============================================================================
# Start services
# =============================================================================
cmd_start() {
  local profile="${1:-core}"
  log_header "Starting Profile: $profile"
  resource_warning "$profile"

  if [[ ! -f "$ENV_FILE" ]]; then
    log_warn ".env not found. Running setup first..."
    cmd_setup
    load_env
  fi

  local resolved
  resolved=$(resolve_profiles "$profile")
  log_info "Resolved profiles: $resolved"
  log_debug "Using compose file: $COMPOSE_FILE"

  dc_profile "$resolved" up -d --remove-orphans

  echo ""
  log_success "Services started for profile: $profile"
  echo ""
  cmd_status
  echo ""
  log_info "Run './run.sh urls' to see all service URLs."
  log_info "Run './run.sh logs' to follow logs."
}

# =============================================================================
# Stop services
# =============================================================================
cmd_stop() {
  log_header "Stopping Services"
  dc stop
  log_success "All services stopped."
}

# =============================================================================
# Restart services
# =============================================================================
cmd_restart() {
  local service="${1:-}"
  log_header "Restarting ${service:-all services}"
  if [[ -n "$service" ]]; then
    dc restart "$service"
  else
    dc restart
  fi
  log_success "Restart complete."
}

# =============================================================================
# Status
# =============================================================================
cmd_status() {
  log_step "Service Status (project: $PROJECT_NAME)"
  dc ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || dc ps
}

cmd_ps() {
  cmd_status
}

# =============================================================================
# Logs
# =============================================================================
cmd_logs() {
  local service="${1:-}"
  if [[ -n "$service" ]]; then
    log_step "Logs: $service"
    dc logs -f --tail=100 "$service"
  else
    log_step "Logs: all services"
    dc logs -f --tail=50
  fi
}

# =============================================================================
# URLs — print all service endpoints
# =============================================================================
cmd_urls() {
  load_env
  log_header "Service URLs"

  local hp="${HOMEPAGE_PORT:-3000}"
  local traefik="${TRAEFIK_DASHBOARD_PORT:-8080}"
  local gf="${GRAFANA_PORT:-3001}"
  local prom="${PROMETHEUS_PORT:-9090}"
  local loki="${LOKI_PORT:-3100}"
  local vault="${VAULT_PORT:-8200}"
  local keycloak="${KEYCLOAK_PORT:-8180}"
  local gitea="${GITEA_PORT:-3002}"
  local jenkins="${JENKINS_PORT:-8090}"
  local adminer="${ADMINER_PORT:-8081}"
  local redis_cmd="${REDIS_COMMANDER_PORT:-8082}"
  local localstack="${LOCALSTACK_PORT:-4566}"
  local minio_ui="${MINIO_CONSOLE_PORT:-9002}"
  local portainer="${PORTAINER_PORT:-9000}"
  local rabbitmq="${RABBITMQ_MANAGEMENT_PORT:-15672}"
  local redpanda="${REDPANDA_CONSOLE_PORT:-8083}"
  local registry="${REGISTRY_PORT:-5000}"
  local sample_api="${SAMPLE_API_PORT:-8000}"
  local sample_fe="${SAMPLE_FRONTEND_PORT:-8100}"
  local tempo="${TEMPO_PORT:-3200}"

  echo ""
  echo "${BOLD}${CYAN}-- Core --${RESET}"
  printf "  %-30s %s\n" "Homepage Dashboard"      "http://localhost:${hp}"
  printf "  %-30s %s\n" "Traefik Dashboard"        "http://localhost:${traefik}"
  echo ""
  echo "${BOLD}${CYAN}-- Observability --${RESET}"
  printf "  %-30s %s\n" "Grafana"                  "http://localhost:${gf}  (admin/admin)"
  printf "  %-30s %s\n" "Prometheus"               "http://localhost:${prom}"
  printf "  %-30s %s\n" "Loki"                     "http://localhost:${loki}"
  printf "  %-30s %s\n" "Tempo"                    "http://localhost:${tempo}"
  echo ""
  echo "${BOLD}${CYAN}-- Data --${RESET}"
  printf "  %-30s %s\n" "Adminer (DB UI)"          "http://localhost:${adminer}"
  printf "  %-30s %s\n" "Redis Commander"          "http://localhost:${redis_cmd}"
  echo ""
  echo "${BOLD}${CYAN}-- Messaging --${RESET}"
  printf "  %-30s %s\n" "RabbitMQ Management"      "http://localhost:${rabbitmq}  (admin/adminpassword123)"
  printf "  %-30s %s\n" "Redpanda Console"         "http://localhost:${redpanda}"
  echo ""
  echo "${BOLD}${CYAN}-- Cloud Emulators --${RESET}"
  printf "  %-30s %s\n" "LocalStack (AWS)"         "http://localhost:${localstack}"
  printf "  %-30s %s\n" "MinIO Console"            "http://localhost:${minio_ui}  (minioadmin/minioadmin123)"
  printf "  %-30s %s\n" "Azurite (Azure)"          "http://localhost:10000 (Blob), :10001 (Queue), :10002 (Table)"
  printf "  %-30s %s\n" "GCP Pub/Sub Emulator"     "http://localhost:8085"
  printf "  %-30s %s\n" "GCP Firestore Emulator"   "http://localhost:8086"
  echo ""
  echo "${BOLD}${CYAN}-- Security --${RESET}"
  printf "  %-30s %s\n" "Vault UI"                 "http://localhost:${vault}  (token: dev-root-token)"
  printf "  %-30s %s\n" "Keycloak Admin"           "http://localhost:${keycloak}/admin  (admin/adminpassword123)"
  echo ""
  echo "${BOLD}${CYAN}-- CI/CD --${RESET}"
  printf "  %-30s %s\n" "Gitea"                    "http://localhost:${gitea}  (gitadmin/gitpassword123)"
  printf "  %-30s %s\n" "Jenkins"                  "http://localhost:${jenkins}"
  printf "  %-30s %s\n" "Docker Registry"          "http://localhost:${registry}"
  echo ""
  echo "${BOLD}${CYAN}-- Apps --${RESET}"
  printf "  %-30s %s\n" "Sample API"               "http://localhost:${sample_api}/health"
  printf "  %-30s %s\n" "Sample Frontend"          "http://localhost:${sample_fe}"
  echo ""
  echo "${BOLD}${CYAN}-- Optional --${RESET}"
  printf "  %-30s %s\n" "Portainer (opt-in)"       "http://localhost:${portainer}"
  echo ""
  log_info "Services not running will return connection refused. Start them first with './run.sh start <profile>'."
}

# =============================================================================
# Open dashboard in browser
# =============================================================================
cmd_open() {
  load_env
  local hp="${HOMEPAGE_PORT:-3000}"
  local url="http://localhost:${hp}"
  log_info "Opening $url..."
  case "$(uname)" in
    Darwin) open "$url" ;;
    Linux)  xdg-open "$url" 2>/dev/null || log_warn "Cannot open browser. Visit $url manually." ;;
    *)      log_warn "Cannot auto-open. Visit $url manually." ;;
  esac
}

# =============================================================================
# Validate — run basic health checks against running services
# =============================================================================
cmd_validate() {
  log_header "Validation Checks"
  load_env
  local pass=0 fail=0

  check_url() {
    local name="$1" url="$2" expect="${3:-200}"
    echo -n "  $name: "
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    if [[ "$status" == "$expect" || "$status" == "200" || "$status" == "302" || "$status" == "301" ]]; then
      log_success "$url ($status)"
      (( pass++ )) || true
    else
      log_fail "$url (got $status, expected ~$expect)"
      (( fail++ )) || true
    fi
  }

  local hp="${HOMEPAGE_PORT:-3000}"
  local traefik="${TRAEFIK_DASHBOARD_PORT:-8080}"
  local gf="${GRAFANA_PORT:-3001}"
  local vault="${VAULT_PORT:-8200}"
  local keycloak="${KEYCLOAK_PORT:-8180}"
  local prom="${PROMETHEUS_PORT:-9090}"
  local sample_api="${SAMPLE_API_PORT:-8000}"

  check_url "Homepage"           "http://localhost:${hp}"
  check_url "Traefik Dashboard"  "http://localhost:${traefik}/dashboard/"
  check_url "Grafana"            "http://localhost:${gf}/api/health"
  check_url "Prometheus"         "http://localhost:${prom}/-/healthy"
  check_url "Vault"              "http://localhost:${vault}/v1/sys/health"
  check_url "Sample API health"  "http://localhost:${sample_api}/health"

  echo ""
  log_info "Passed: $pass  Failed: $fail"
  if [[ "$fail" -gt 0 ]]; then
    log_warn "Some checks failed — services may not be running. Start them first."
    return 1
  fi
  log_success "All checks passed."
}

# =============================================================================
# Clean — remove only this project's containers, networks, volumes
# =============================================================================
cmd_clean() {
  log_header "Clean — Remove Project Containers and Volumes"
  log_warn "This will remove all containers, networks, and volumes for project: $PROJECT_NAME"
  log_warn "Your files in docker/ will NOT be deleted."
  log_warn "This action is irreversible for any data stored in volumes."
  echo ""

  if ! confirm "Proceed with cleanup?"; then
    log_info "Cleanup cancelled."
    return 0
  fi

  log_step "Stopping services..."
  dc down --remove-orphans --volumes 2>/dev/null || true

  log_step "Removing any remaining containers with project label..."
  local -a containers=()
  mapfile -t containers < <(docker ps -a --filter "label=${LABEL_FILTER}" -q 2>/dev/null || true)
  if (( ${#containers[@]} > 0 )); then
    run_cmd docker rm -f "${containers[@]}"
  fi

  log_step "Removing project networks..."
  local -a networks=()
  mapfile -t networks < <(docker network ls --filter "label=${LABEL_FILTER}" -q 2>/dev/null || true)
  if (( ${#networks[@]} > 0 )); then
    run_cmd docker network rm "${networks[@]}" 2>/dev/null || true
  fi

  log_step "Removing project volumes..."
  local -a volumes=()
  mapfile -t volumes < <(docker volume ls --filter "label=${LABEL_FILTER}" -q 2>/dev/null || true)
  if (( ${#volumes[@]} > 0 )); then
    run_cmd docker volume rm "${volumes[@]}" 2>/dev/null || true
  fi

  log_success "Cleanup complete. Run './run.sh start' to restart from scratch."
}

# =============================================================================
# Nuke — full cleanup including dangling resources
# =============================================================================
cmd_nuke() {
  log_header "NUKE — Full Cleanup"
  log_warn "This will:"
  log_warn "  1. Stop and remove ALL containers for project: $PROJECT_NAME"
  log_warn "  2. Remove ALL associated volumes (all local data will be lost)"
  log_warn "  3. Remove ALL project networks"
  log_warn "  4. Optionally prune unused images"
  log_warn ""
  log_warn "Your files on disk (labs/, configs/, apps/, etc.) will NOT be deleted."
  echo ""

  if ! confirm "Are you SURE you want to nuke everything for $PROJECT_NAME?"; then
    log_info "Nuke cancelled."
    return 0
  fi

  cmd_clean

  log_step "Pruning unused images (non-project)..."
  if confirm "Also remove unused Docker images to free disk space?"; then
    run_cmd docker image prune -f
    log_info "To remove ALL unused images: docker image prune -a -f"
  fi

  log_success "Nuke complete. Platform is fully reset."
}

# =============================================================================
# Seed data
# =============================================================================
cmd_seed() {
  log_header "Seed Sample Data"
  log_info "Seeding databases with sample data..."

  # PostgreSQL seed
  if dc ps postgres 2>/dev/null | grep -q "running\|Up"; then
    log_step "Seeding PostgreSQL..."
    dc exec postgres psql -U "${POSTGRES_USER:-labuser}" -d "${POSTGRES_DB:-labdb}" \
      -c "SELECT version();" 2>/dev/null && log_success "PostgreSQL accessible" || log_warn "PostgreSQL not ready"
  fi

  # Redis seed
  if dc ps redis 2>/dev/null | grep -q "running\|Up"; then
    log_step "Seeding Redis..."
    dc exec redis redis-cli -a "${REDIS_PASSWORD:-redispassword123}" SET "lab:seed" "hello-world" 2>/dev/null \
      && log_success "Redis seeded" || log_warn "Redis not ready"
  fi

  log_success "Seed complete. See data/ directory for sample datasets."
}

# =============================================================================
# Backup volumes
# =============================================================================
cmd_backup() {
  log_header "Backup Volumes"
  local backup_dir="${SCRIPT_DIR}/data/backups"
  local timestamp
  timestamp=$(date +%Y%m%d_%H%M%S)

  mkdir -p "$backup_dir"

  log_step "Backing up PostgreSQL..."
  if dc ps postgres 2>/dev/null | grep -q "running\|Up"; then
    run_cmd dc exec -T postgres pg_dump -U "${POSTGRES_USER:-labuser}" "${POSTGRES_DB:-labdb}" \
      > "${backup_dir}/postgres_${timestamp}.sql" 2>/dev/null \
      && log_success "Postgres backup: ${backup_dir}/postgres_${timestamp}.sql" \
      || log_warn "PostgreSQL backup failed — is it running?"
  else
    log_warn "PostgreSQL not running, skipping backup"
  fi

  log_success "Backup complete. Files in: $backup_dir"
}

# =============================================================================
# Lab commands
# =============================================================================
cmd_lab() {
  local action="${1:-list}"
  local lab_id="${2:-}"

  case "$action" in
    list)
      log_header "Available Labs"
      if [[ -f "$LAB_INDEX" ]]; then
        # Try yq first, then fall back to grep parsing
        if command -v yq &>/dev/null; then
          yq e '.labs[] | "  " + .id + "\t" + .name + "\t[" + .profile + "]"' "$LAB_INDEX" 2>/dev/null \
            || grep -E "^\s+(id|name|profile):" "$LAB_INDEX" | paste - - -
        else
          log_info "Lab index: $LAB_INDEX"
          grep -E "^\s+- id:|name:|profile:" "$LAB_INDEX" 2>/dev/null \
            | awk '/id:/{id=$2} /name:/{name=$2} /profile:/{print "  " id "\t" name "\t[" $2 "]"}' \
            || cat "$LAB_INDEX"
        fi
      else
        log_warn "Lab index not found: $LAB_INDEX"
        log_info "Listing lab directories:"
        find labs -mindepth 1 -maxdepth 1 -type d -printf '  %f\n' 2>/dev/null | sort
      fi
      ;;

    start)
      if [[ -z "$lab_id" ]]; then
        log_error "Usage: ./run.sh lab start <lab_id>"
        return 1
      fi
      log_header "Starting Lab: $lab_id"
      local lab_dir="labs/${lab_id}"
      if [[ ! -d "$lab_dir" ]]; then
        log_error "Lab not found: $lab_dir"
        log_info "Run './run.sh lab list' to see available labs."
        return 1
      fi
      log_info "Lab directory: $lab_dir"
      echo ""
      if [[ -f "${lab_dir}/README.md" ]]; then
        head -30 "${lab_dir}/README.md"
        echo ""
        log_info "Full lab guide: ${lab_dir}/README.md"
        log_info "Tasks: ${lab_dir}/tasks.md"
        log_info "Commands: ${lab_dir}/commands.md"
      fi
      # Start the required profile for this lab
      if command -v yq &>/dev/null && [[ -f "$LAB_INDEX" ]]; then
        local lab_profile
        lab_profile=$(yq e ".labs[] | select(.id == \"${lab_id}\") | .profile" "$LAB_INDEX" 2>/dev/null || true)
        if [[ -n "$lab_profile" && "$lab_profile" != "null" ]]; then
          log_info "This lab requires profile: $lab_profile"
          if confirm "Start required services now?"; then
            cmd_start "$lab_profile"
          fi
        fi
      fi
      ;;

    validate)
      if [[ -z "$lab_id" ]]; then
        log_error "Usage: ./run.sh lab validate <lab_id>"
        return 1
      fi
      log_header "Validating Lab: $lab_id"
      local validate_script="labs/${lab_id}/validate.sh"
      if [[ -f "$validate_script" ]]; then
        bash "$validate_script"
      elif [[ -f "labs/${lab_id}/validate.md" ]]; then
        log_info "Validation guide: labs/${lab_id}/validate.md"
        cat "labs/${lab_id}/validate.md"
      else
        log_warn "No validation script found for lab: $lab_id"
      fi
      ;;

    reset)
      if [[ -z "$lab_id" ]]; then
        log_error "Usage: ./run.sh lab reset <lab_id>"
        return 1
      fi
      log_header "Resetting Lab: $lab_id"
      log_warn "This will reset the lab environment for: $lab_id"
      if confirm "Reset lab $lab_id?"; then
        local reset_script="labs/${lab_id}/reset.sh"
        if [[ -f "$reset_script" ]]; then
          bash "$reset_script"
          log_success "Lab $lab_id reset."
        else
          log_warn "No reset script found. Restart services manually."
        fi
      fi
      ;;

    *)
      log_error "Unknown lab action: $action"
      log_info "Usage: ./run.sh lab <list|start|validate|reset> [lab_id]"
      return 1
      ;;
  esac
}

# =============================================================================
# Kubernetes — kind/k3d commands (not compose-based)
# =============================================================================
cmd_kubernetes() {
  local action="${1:-help}"
  log_header "Kubernetes Local Cluster"

  case "$action" in
    create)
      local tool="${2:-kind}"
      log_step "Creating local Kubernetes cluster with $tool..."
      case "$tool" in
        kind)
          if ! command -v kind &>/dev/null; then
            log_error "kind not installed. Install: brew install kind"
            return 1
          fi
          run_cmd kind create cluster \
            --name cloud-learnings \
            --config infrastructure/kubernetes/kind-config.yaml \
            2>/dev/null || run_cmd kind create cluster --name cloud-learnings
          log_success "kind cluster 'cloud-learnings' created."
          log_info "Set KUBECONFIG: export KUBECONFIG=\$(kind get kubeconfig-path --name cloud-learnings)"
          ;;
        k3d)
          if ! command -v k3d &>/dev/null; then
            log_error "k3d not installed. Install: brew install k3d"
            return 1
          fi
          run_cmd k3d cluster create cloud-learnings \
            --agents 2 \
            --port "8888:80@loadbalancer"
          log_success "k3d cluster 'cloud-learnings' created."
          ;;
        *)
          log_error "Unknown tool: $tool. Use 'kind' or 'k3d'."
          return 1
          ;;
      esac
      ;;

    delete)
      local tool="${2:-kind}"
      log_warn "Deleting local Kubernetes cluster..."
      if confirm "Delete cluster cloud-learnings?"; then
        case "$tool" in
          kind) run_cmd kind delete cluster --name cloud-learnings ;;
          k3d)  run_cmd k3d cluster delete cloud-learnings ;;
        esac
        log_success "Cluster deleted."
      fi
      ;;

    status)
      if command -v kubectl &>/dev/null; then
        kubectl get nodes 2>/dev/null || log_warn "No cluster available or kubectl not configured"
      else
        log_warn "kubectl not installed"
      fi
      ;;

    help|*)
      echo ""
      echo "  Kubernetes is managed via kind or k3d, not Docker Compose."
      echo ""
      echo "  Commands:"
      echo "    ./run.sh kubernetes create kind    Create cluster with kind"
      echo "    ./run.sh kubernetes create k3d     Create cluster with k3d"
      echo "    ./run.sh kubernetes delete kind    Delete kind cluster"
      echo "    ./run.sh kubernetes status         Show cluster node status"
      echo ""
      echo "  Install:"
      echo "    brew install kind k3d kubectl helm"
      echo ""
      echo "  Labs: labs/kubernetes-local/"
      echo ""
      ;;
  esac
}

# =============================================================================
# Pull images
# =============================================================================
cmd_pull() {
  local profile="${1:-core}"
  log_header "Pulling Images for Profile: $profile"
  local resolved
  resolved=$(resolve_profiles "$profile")
  dc_profile "$resolved" pull
  log_success "Images pulled."
}

# =============================================================================
# Show resource usage
# =============================================================================
cmd_resources() {
  log_header "Resource Usage"
  docker stats --no-stream --format \
    "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
    2>/dev/null | grep -i "cloud-learnings" || \
    docker stats --no-stream 2>/dev/null | head -20
}

# =============================================================================
# Interactive menu
# =============================================================================
cmd_menu() {
  log_header "Cloud-Learnings Lab Platform v${VERSION}"
  echo "  Project: $PROJECT_NAME"
  echo "  Directory: $SCRIPT_DIR"
  echo ""
  echo "  ${BOLD}Main Actions:${RESET}"
  echo "    1) Setup (.env)"
  echo "    2) Doctor (check prerequisites)"
  echo "    3) Start core (lightweight)"
  echo "    4) Start profile..."
  echo "    5) Stop all services"
  echo "    6) Status"
  echo "    7) Show URLs"
  echo "    8) Open dashboard"
  echo ""
  echo "  ${BOLD}Labs:${RESET}"
  echo "    9)  List labs"
  echo "    10) Start a lab"
  echo ""
  echo "  ${BOLD}Maintenance:${RESET}"
  echo "    11) View logs"
  echo "    12) Validate services"
  echo "    13) Seed sample data"
  echo "    14) Backup volumes"
  echo "    15) Show resource usage"
  echo "    16) Clean (remove containers/volumes)"
  echo "    17) Nuke (full reset)"
  echo ""
  echo "    q)  Quit"
  echo ""
  echo -n "  ${BOLD}Select an option: ${RESET}"
  read -r choice
  echo ""

  case "$choice" in
    1)  cmd_setup ;;
    2)  cmd_doctor ;;
    3)  cmd_start core ;;
    4)
      echo -n "  Profile name (core/data/aws/azure/gcp/cloud/observability/security/cicd/iac/apps/all): "
      read -r p
      cmd_start "${p:-core}"
      ;;
    5)  cmd_stop ;;
    6)  cmd_status ;;
    7)  cmd_urls ;;
    8)  cmd_open ;;
    9)  cmd_lab list ;;
    10)
      echo -n "  Lab ID: "
      read -r lid
      cmd_lab start "$lid"
      ;;
    11)
      echo -n "  Service name (blank = all): "
      read -r svc
      cmd_logs "$svc"
      ;;
    12) cmd_validate ;;
    13) cmd_seed ;;
    14) cmd_backup ;;
    15) cmd_resources ;;
    16) cmd_clean ;;
    17) cmd_nuke ;;
    q|Q) log_info "Bye."; exit 0 ;;
    *)  log_warn "Unknown option: $choice" ;;
  esac
}

# =============================================================================
# Help text
# =============================================================================
cmd_help() {
  cat <<HELP
${BOLD}Cloud-Learnings Lab Platform${RESET} v${VERSION}
${CYAN}Usage:${RESET} ./run.sh [command] [args] [flags]

${BOLD}Commands:${RESET}
  setup                    Create .env from .env.example
  doctor                   Check prerequisites and system health
  start [profile]          Start services (default: core)
  stop                     Stop all services
  restart [service]        Restart all or specific service
  status / ps              Show running containers
  logs [service]           Tail logs (all or specific service)
  urls                     Print all service URLs
  open                     Open dashboard in browser
  validate                 Run health checks
  pull [profile]           Pre-pull images for profile
  resources                Show container resource usage
  seed                     Seed databases with sample data
  backup                   Backup database volumes
  clean                    Remove containers and volumes (confirmation)
  nuke                     Full reset (confirmation)
  kubernetes <action>      Manage local k8s cluster (kind/k3d)
  lab list                 List available labs
  lab start <lab_id>       Start a specific lab
  lab validate <lab_id>    Validate lab completion
  lab reset <lab_id>       Reset lab environment

${BOLD}Profiles:${RESET}
  core                     Traefik + Homepage + Nginx toolbox (default)
  dashboard                core + Portainer (opt-in)
  data                     core + PostgreSQL + MySQL + MongoDB + Redis + Adminer
  messaging                core + RabbitMQ + Redpanda
  aws                      core + LocalStack + AWS CLI
  azure                    core + Azurite + Azure CLI
  gcp                      core + GCP Pub/Sub + Firestore emulators
  cloud                    core + aws + azure + gcp
  observability            core + Prometheus + Grafana + Loki + Tempo + OTel
  security                 core + Vault + Keycloak + Trivy + Checkov
  cicd                     core + Gitea + Jenkins + Registry
  iac                      core + Terraform + OpenTofu + Ansible + kubectl + Helm
  apps                     core + Sample apps
  all                      Everything (16GB+ RAM recommended)

${BOLD}Flags:${RESET}
  --verbose / -v           Show debug output
  --dry-run                Print commands without executing
  --yes / -y               Auto-confirm destructive operations

${BOLD}Examples:${RESET}
  ./run.sh setup
  ./run.sh doctor
  ./run.sh start core
  ./run.sh start aws
  ./run.sh start observability
  ./run.sh start all
  ./run.sh lab start aws-001
  ./run.sh kubernetes create kind
  ./run.sh stop
  ./run.sh clean --yes
HELP
}

# =============================================================================
# Main entrypoint
# =============================================================================
main() {
  # Load env early (non-fatal)
  load_env 2>/dev/null || true

  # Parse global flags
  local args_str
  args_str=$(parse_global_flags "$@")
  # Convert string back to array
  local args=()
  if [[ -n "$args_str" ]]; then
    read -ra args <<< "$args_str"
  fi

  local command="${args[0]:-menu}"
  local rest=("${args[@]:1}")

  case "$command" in
    setup)                cmd_setup ;;
    doctor)               cmd_doctor ;;
    start)                cmd_start "${rest[0]:-core}" ;;
    stop)                 cmd_stop ;;
    restart)              cmd_restart "${rest[0]:-}" ;;
    status|ps)            cmd_status ;;
    logs)                 cmd_logs "${rest[0]:-}" ;;
    urls)                 cmd_urls ;;
    open)                 cmd_open ;;
    validate)             cmd_validate ;;
    pull)                 cmd_pull "${rest[0]:-core}" ;;
    resources)            cmd_resources ;;
    seed)                 cmd_seed ;;
    backup)               cmd_backup ;;
    clean)                cmd_clean ;;
    nuke)                 cmd_nuke ;;
    kubernetes|k8s)       cmd_kubernetes "${rest[@]:-}" ;;
    lab)                  cmd_lab "${rest[0]:-list}" "${rest[1]:-}" ;;
    menu)                 cmd_menu ;;
    help|--help|-h)       cmd_help ;;
    version|--version)    echo "cloud-learnings-lab run.sh v${VERSION}" ;;
    *)
      log_error "Unknown command: $command"
      echo ""
      cmd_help
      exit 1
      ;;
  esac
}

main "$@"
