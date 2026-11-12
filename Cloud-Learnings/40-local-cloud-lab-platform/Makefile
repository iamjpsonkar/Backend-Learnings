# Local Cloud Lab Platform — Makefile
#
# Usage: make <target>
# Run `make help` to see all available commands.

SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

# Detect project root (directory containing this Makefile)
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

# Load .env if it exists
ifneq (,$(wildcard $(ROOT_DIR)/.env))
    include $(ROOT_DIR)/.env
    export
endif

# Default values (overridden by .env)
LAB_API_PORT     ?= 4567
LAB_UI_PORT      ?= 3001
LOG_LEVEL        ?= INFO
LABS_DIR         ?= ./labs
LAB              ?=
SERVICE          ?=
VERBOSE          ?= 0
CONFIRM          ?=

# Docker Compose command (supports both v1 and v2)
COMPOSE := docker compose

# Color output
BOLD   := \033[1m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m

##@ Help
.PHONY: help
help: ## Show this help message
	@echo ""
	@echo "$(BOLD)Local Cloud Lab Platform$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make $(BOLD)<target>$(RESET)\n\n"} \
	  /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-30s$(RESET) %s\n", $$1, $$2 } \
	  /^##@/ { printf "\n$(BOLD)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Setup & Verification
.PHONY: setup
setup: ## First-time setup: venv, deps, DB init, Docker networks
	@echo "$(BOLD)Running first-time setup...$(RESET)"
	@bash $(ROOT_DIR)/scripts/setup.sh

.PHONY: doctor
doctor: ## Check all required tools and configurations
	@bash $(ROOT_DIR)/scripts/doctor.sh

.PHONY: health
health: ## Check health of all running services
	@bash $(ROOT_DIR)/scripts/health.sh

.PHONY: check-ports
check-ports: ## Check if required ports are available
	@bash $(ROOT_DIR)/scripts/check-ports.sh

.PHONY: validate-labs
validate-labs: ## Validate all lab YAML files against the schema
	@echo "$(BOLD)Validating lab definitions...$(RESET)"
	@python3 $(ROOT_DIR)/lab-runner/runner.py validate-all

##@ Starting Services
.PHONY: start-core
start-core: _require-env ## Start core services (MinIO, Traefik, API, UI)
	@echo "$(BOLD)Starting core services...$(RESET)"
	@$(COMPOSE) --profile core up -d
	@echo "$(GREEN)Core services started$(RESET)"
	@echo "  Dashboard:  http://localhost:$(LAB_UI_PORT)"
	@echo "  API:        http://localhost:$(LAB_API_PORT)"
	@echo "  MinIO:      http://localhost:9001"
	@echo "  Traefik:    http://localhost:8080"

.PHONY: start-observability
start-observability: _require-env ## Start observability stack (Prometheus, Grafana, Loki, Jaeger)
	@echo "$(BOLD)Starting observability services (~1.5 GB RAM)...$(RESET)"
	@$(COMPOSE) -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d

.PHONY: start-security
start-security: _require-env ## Start security services (Vault, Keycloak)
	@echo "$(BOLD)Starting security services (~1 GB RAM)...$(RESET)"
	@$(COMPOSE) -f docker-compose.yml -f docker-compose.security.yml --profile security up -d

.PHONY: start-cicd
start-cicd: _require-env ## Start CI/CD services (Gitea, Woodpecker CI)
	@echo "$(BOLD)Starting CI/CD services (~1.5 GB RAM)...$(RESET)"
	@$(COMPOSE) -f docker-compose.yml -f docker-compose.cicd.yml --profile cicd up -d

.PHONY: start-data
start-data: _require-env ## Start data services (PostgreSQL, MongoDB, Redis, Redpanda, RabbitMQ)
	@echo "$(BOLD)Starting data services (~2 GB RAM)...$(RESET)"
	@$(COMPOSE) -f docker-compose.yml -f docker-compose.data.yml --profile data up -d

.PHONY: start-aws-local
start-aws-local: _require-env ## Start LocalStack (AWS emulator)
	@echo "$(BOLD)Starting LocalStack...$(RESET)"
	@$(COMPOSE) -f docker-compose.yml -f docker-compose.aws-local.yml --profile aws-local up -d
	@echo "$(GREEN)LocalStack ready at http://localhost:4566$(RESET)"

.PHONY: start-azure-local
start-azure-local: _require-env ## Start Azurite (Azure storage emulator)
	@echo "$(BOLD)Starting Azurite...$(RESET)"
	@$(COMPOSE) -f docker-compose.yml -f docker-compose.azure-local.yml --profile azure-local up -d
	@echo "$(GREEN)Azurite ready at http://localhost:10000$(RESET)"

.PHONY: start-all
start-all: _require-env ## Start ALL services (requires ~8 GB RAM, 16 GB recommended)
	@echo "$(YELLOW)Warning: starting all profiles uses ~8 GB RAM$(RESET)"
	@echo "$(BOLD)Starting all services...$(RESET)"
	@$(COMPOSE) \
	  -f docker-compose.yml \
	  -f docker-compose.observability.yml \
	  -f docker-compose.security.yml \
	  -f docker-compose.cicd.yml \
	  -f docker-compose.data.yml \
	  -f docker-compose.aws-local.yml \
	  -f docker-compose.azure-local.yml \
	  --profile core --profile observability --profile security \
	  --profile cicd --profile data --profile aws-local --profile azure-local \
	  up -d

##@ Stopping Services
.PHONY: stop
stop: ## Stop all running lab services (keeps data volumes)
	@echo "$(BOLD)Stopping all services...$(RESET)"
	@$(COMPOSE) \
	  -f docker-compose.yml \
	  -f docker-compose.observability.yml \
	  -f docker-compose.security.yml \
	  -f docker-compose.cicd.yml \
	  -f docker-compose.data.yml \
	  -f docker-compose.aws-local.yml \
	  -f docker-compose.azure-local.yml \
	  down 2>/dev/null || true
	@echo "$(GREEN)All services stopped (data volumes preserved)$(RESET)"

.PHONY: stop-clean
stop-clean: ## Stop all services AND remove data volumes
	@echo "$(YELLOW)This will stop services and delete all volume data$(RESET)"
	@$(COMPOSE) \
	  -f docker-compose.yml \
	  -f docker-compose.observability.yml \
	  -f docker-compose.security.yml \
	  -f docker-compose.cicd.yml \
	  -f docker-compose.data.yml \
	  -f docker-compose.aws-local.yml \
	  -f docker-compose.azure-local.yml \
	  down -v 2>/dev/null || true
	@echo "$(GREEN)All services stopped and volumes removed$(RESET)"

.PHONY: stop-observability
stop-observability: ## Stop observability services only
	@$(COMPOSE) -f docker-compose.observability.yml stop prometheus grafana loki promtail jaeger otel-collector 2>/dev/null || true

.PHONY: stop-security
stop-security: ## Stop security services only
	@$(COMPOSE) -f docker-compose.security.yml stop vault keycloak 2>/dev/null || true

.PHONY: stop-cicd
stop-cicd: ## Stop CI/CD services only
	@$(COMPOSE) -f docker-compose.cicd.yml stop gitea woodpecker-server woodpecker-agent 2>/dev/null || true

##@ Status & Logs
.PHONY: status
status: ## Show status of all lab containers
	@echo "$(BOLD)Container Status:$(RESET)"
	@docker ps --filter "label=com.cloudlabs.project=local-cloud-lab" \
	  --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

.PHONY: logs
logs: ## Tail logs for a service: make logs SERVICE=api
	@if [ -z "$(SERVICE)" ]; then \
	  echo "$(RED)Error: specify SERVICE. Example: make logs SERVICE=api$(RESET)"; exit 1; \
	fi
	@$(COMPOSE) logs -f --tail=100 $(SERVICE)

.PHONY: logs-all
logs-all: ## Tail logs for all running services
	@$(COMPOSE) logs -f --tail=50

##@ Lab Operations
.PHONY: list-labs
list-labs: ## List all available labs
	@python3 $(ROOT_DIR)/lab-runner/runner.py list

.PHONY: run-lab
run-lab: ## Run a lab: make run-lab LAB=04-docker/docker-basics
	@if [ -z "$(LAB)" ]; then \
	  echo "$(RED)Error: specify LAB. Example: make run-lab LAB=04-docker/docker-basics$(RESET)"; exit 1; \
	fi
	@python3 $(ROOT_DIR)/lab-runner/runner.py run \
	  --lab=$(LAB) \
	  $(if $(filter 1,$(VERBOSE)),--verbose,)

.PHONY: validate-lab
validate-lab: ## Validate a lab without grading: make validate-lab LAB=04-docker/docker-basics
	@if [ -z "$(LAB)" ]; then \
	  echo "$(RED)Error: specify LAB$(RESET)"; exit 1; \
	fi
	@python3 $(ROOT_DIR)/lab-runner/runner.py validate --lab=$(LAB)

.PHONY: lab-info
lab-info: ## Show lab details: make lab-info LAB=04-docker/docker-basics
	@if [ -z "$(LAB)" ]; then \
	  echo "$(RED)Error: specify LAB$(RESET)"; exit 1; \
	fi
	@python3 $(ROOT_DIR)/lab-runner/runner.py info --lab=$(LAB)

.PHONY: progress
progress: ## Show lab progress summary
	@python3 $(ROOT_DIR)/lab-runner/runner.py progress

.PHONY: reset-progress
reset-progress: ## Reset all lab progress (keeps service data)
	@echo "$(YELLOW)This will reset all lab progress in the database$(RESET)"
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
	  python3 $(ROOT_DIR)/lab-runner/runner.py reset-progress; \
	  echo "$(GREEN)Progress reset$(RESET)"; \
	else \
	  echo "Cancelled"; \
	fi

##@ Database
.PHONY: db-shell
db-shell: ## Open SQLite shell for lab platform database
	@sqlite3 $(ROOT_DIR)/api/data/lab_platform.db

.PHONY: reset-db
reset-db: ## Reset the lab platform database (wipes progress and metadata)
	@echo "$(YELLOW)This will delete the lab platform database$(RESET)"
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
	  rm -f $(ROOT_DIR)/api/data/lab_platform.db; \
	  bash $(ROOT_DIR)/scripts/init-db.sh; \
	  echo "$(GREEN)Database reset$(RESET)"; \
	else \
	  echo "Cancelled"; \
	fi

##@ Kubernetes
.PHONY: k8s-create-cluster
k8s-create-cluster: ## Create the local kind cluster for Kubernetes labs
	@bash $(ROOT_DIR)/scripts/k8s-setup.sh create

.PHONY: k8s-delete-cluster
k8s-delete-cluster: ## Delete the local kind cluster
	@bash $(ROOT_DIR)/scripts/k8s-setup.sh delete

.PHONY: k8s-status
k8s-status: ## Show kind cluster status
	@kubectl cluster-info --context kind-cloud-lab 2>/dev/null || echo "Cluster not running. Run: make k8s-create-cluster"

.PHONY: k8s-dashboard
k8s-dashboard: ## Start the Kubernetes dashboard
	@bash $(ROOT_DIR)/scripts/k8s-dashboard.sh

##@ Vault
.PHONY: vault-init
vault-init: ## Initialize Vault with lab secrets
	@bash $(ROOT_DIR)/scripts/vault-init.sh

.PHONY: vault-status
vault-status: ## Check Vault status
	@VAULT_ADDR=http://localhost:8200 vault status 2>/dev/null || echo "Vault not running. Start with: make start-security"

##@ LocalStack
.PHONY: localstack-status
localstack-status: ## Check LocalStack health
	@curl -s http://localhost:4566/health | python3 -m json.tool 2>/dev/null || echo "LocalStack not running. Start with: make start-aws-local"

.PHONY: localstack-reset
localstack-reset: ## Reset LocalStack state (removes all fake AWS resources)
	@curl -s -X POST http://localhost:4566/_localstack/state/reset | python3 -m json.tool

##@ Building
.PHONY: build
build: ## Build all Docker images
	@$(COMPOSE) build

.PHONY: rebuild
rebuild: ## Force rebuild a service without cache: make rebuild SERVICE=api
	@if [ -z "$(SERVICE)" ]; then \
	  echo "$(RED)Error: specify SERVICE. Example: make rebuild SERVICE=api$(RESET)"; exit 1; \
	fi
	@$(COMPOSE) build --no-cache $(SERVICE)

.PHONY: pull
pull: ## Pull all Docker images (pre-download for offline use)
	@bash $(ROOT_DIR)/scripts/pull-images.sh

##@ Cleanup & Reset
.PHONY: cleanup
cleanup: ## Remove all lab Docker resources (requires --confirm or interactive prompt)
	@bash $(ROOT_DIR)/scripts/cleanup.sh $(if $(filter --confirm,$(MAKEFLAGS)),--confirm,)

.PHONY: reset
reset: ## Full reset: stop all, wipe volumes, delete database (requires --confirm)
	@bash $(ROOT_DIR)/scripts/reset.sh $(if $(filter --confirm,$(MAKEFLAGS)),--confirm,)

.PHONY: prune
prune: ## Clean Docker build cache for lab images only
	@docker image prune --filter "label=com.cloudlabs.project=local-cloud-lab" -f

##@ Reports
.PHONY: report
report: ## Generate a lab progress report
	@python3 $(ROOT_DIR)/lab-runner/runner.py report --output=$(ROOT_DIR)/reports/progress.json
	@echo "$(GREEN)Report saved to reports/progress.json$(RESET)"

.PHONY: bug-report
bug-report: ## Generate diagnostic info for bug reports
	@bash $(ROOT_DIR)/scripts/bug-report.sh

##@ Internal
.PHONY: _require-env
_require-env:
	@if [ ! -f "$(ROOT_DIR)/.env" ]; then \
	  echo "$(RED)Error: .env file not found$(RESET)"; \
	  echo "Run: cp .env.example .env"; \
	  exit 1; \
	fi

.PHONY: _create-network
_create-network:
	@docker network create cloud-lab-network --label com.cloudlabs.project=local-cloud-lab 2>/dev/null || true
