# Scripts

Platform management scripts. All are invoked via `make` targets — you rarely need to call them directly.

## Script Reference

| Script | Make Target | Purpose |
|--------|------------|---------|
| `setup.sh` | `make setup` | First-time platform setup |
| `doctor.sh` | `make doctor` | Check all requirements |
| `health.sh` | `make health` | Check running service health |
| `check-ports.sh` | `make check-ports` | Check port availability |
| `init-db.sh` | Called by setup.sh | Initialize SQLite database |
| `cleanup.sh` | `make cleanup` | Remove lab Docker resources (safe) |
| `reset.sh` | `make reset` | Full platform reset (destructive) |
| `k8s-setup.sh` | `make k8s-create-cluster` | Create/delete kind cluster |
| `k8s-dashboard.sh` | `make k8s-dashboard` | Start K8s dashboard |
| `vault-init.sh` | `make vault-init` | Seed Vault with lab secrets |
| `pull-images.sh` | `make pull` | Pre-download all Docker images |
| `bug-report.sh` | `make bug-report` | Generate diagnostic report |

## Shared Utilities

`utils/common.sh` — sourced by all scripts. Provides:

- Color output functions: `log_info`, `log_warn`, `log_error`, `log_ok`, `log_fail`
- Docker helpers: `require_docker`, `container_running`, `wait_for_service`
- Port checking: `port_available`, `check_port`
- `load_env` — loads `.env` into environment
- `confirm_destructive` — prompts before risky operations
- `version_gte` — semver comparison

## Safety Rules

All scripts follow these rules:
- `set -euo pipefail` at the top
- Pre-flight checks before destructive actions
- Only remove resources labelled `com.cloudlabs.project=local-cloud-lab`
- `--confirm` flag or interactive prompt required for destructive operations
- No writes outside `40-local-cloud-lab-platform/`
- No logging of secrets, passwords, or tokens
