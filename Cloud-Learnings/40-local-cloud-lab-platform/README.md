# Local Cloud Lab Platform

A fully functional local practice environment for cloud, DevOps, SRE, Kubernetes, Terraform,
Linux, networking, security, monitoring, CI/CD, FinOps, databases, serverless, and real-world
architecture patterns — all running locally using Docker and free/open-source tools.

No cloud accounts required. No credit cards. No costs.

---

## What Is This?

This platform lets you practice every skill in the Cloud-Learnings curriculum hands-on,
locally. It spins up real services (not simulations) using Docker Compose profiles, provides
a lab runner that grades your work, and tracks your progress in a local dashboard.

---

## Quick Navigation

| Document | Purpose |
|----------|---------|
| [QUICKSTART.md](QUICKSTART.md) | Get running in 5 minutes |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Prerequisites and system requirements |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Platform design and component overview |
| [LAB_INDEX.md](LAB_INDEX.md) | Full catalog of all labs |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and fixes |
| [ROADMAP.md](ROADMAP.md) | Planned labs and features |

---

## What You Can Practice

| Category | Labs | Tools |
|----------|------|-------|
| Linux + Shell | 8 | Bash, cron, systemd (in containers) |
| Networking | 6 | Traefik, DNS, TLS, Wireshark-friendly |
| Docker | 8 | Docker, BuildKit, multi-stage, security |
| Kubernetes | 12 | kind, kubectl, Helm, K9s |
| Terraform / OpenTofu | 10 | Terraform, OpenTofu, LocalStack |
| Ansible | 6 | Ansible, molecule |
| AWS (local) | 10 | LocalStack (S3, SQS, Lambda, DynamoDB, IAM) |
| Azure (local) | 6 | Azurite (Blob, Queue, Table) |
| GCP (local) | 4 | Fake GCS, Pub/Sub emulator |
| Security | 10 | Vault, Keycloak, Trivy, Checkov, Falco |
| Observability | 10 | Prometheus, Grafana, Loki, Jaeger, OTel |
| CI/CD | 8 | Gitea, Woodpecker CI, ArgoCD |
| Databases | 10 | PostgreSQL, MongoDB, Redis, MySQL |
| Storage | 6 | MinIO (S3-compatible), NFS, object lifecycle |
| Serverless + Events | 8 | Knative, Redpanda, RabbitMQ, OpenFaaS |
| SRE | 8 | SLOs, chaos, runbooks, on-call simulation |
| FinOps | 4 | Cost allocation, tagging, Infracost |
| Multi-Cloud | 6 | Cross-cloud patterns, abstraction layers |
| Disaster Recovery | 6 | Backup, failover, chaos engineering |
| Production Troubleshooting | 8 | Real-world broken scenarios to debug |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Lab Platform                           │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌────────────────────┐  │
│  │ React UI │   │ FastAPI  │   │    Lab Runner      │  │
│  │ :3001    │◄──│ :4567    │◄──│  runner.py         │  │
│  └──────────┘   └──────────┘   └────────────────────┘  │
│                      │                  │               │
│               ┌──────┴──────┐    ┌──────┴──────┐        │
│               │   SQLite    │    │  labs/*.yaml │        │
│               │  (progress) │    │  (lab defs)  │        │
│               └─────────────┘    └─────────────┘        │
│                                                         │
│  Docker Compose Profiles (start only what you need):   │
│  core | observability | security | cicd | data |       │
│  aws-local | azure-local | kubernetes                  │
└─────────────────────────────────────────────────────────┘
```

---

## Getting Started

```bash
# 1. Check requirements
make doctor

# 2. One-time setup
make setup

# 3. Start core services (MinIO + Traefik + API + UI)
make start-core

# 4. Open the dashboard
open http://localhost:3001

# 5. Run your first lab
make run-lab LAB=04-docker/docker-basics

# 6. Stop everything when done
make stop
```

---

## Docker Compose Profiles

Start only what you need to conserve RAM:

```bash
make start-core           # ~512 MB — MinIO, Traefik, API, UI
make start-observability  # ~1.5 GB — Prometheus, Grafana, Loki, Jaeger
make start-security       # ~1 GB   — Vault, Keycloak
make start-cicd           # ~1.5 GB — Gitea, Woodpecker CI
make start-data           # ~2 GB   — PostgreSQL, MongoDB, Redis, Redpanda, RabbitMQ
make start-aws-local      # ~512 MB — LocalStack
make start-azure-local    # ~256 MB — Azurite
make start-all            # ~8 GB   — Everything (requires 16 GB RAM)
```

---

## Port Reference

| Port | Service |
|------|---------|
| 3001 | Lab Dashboard (UI) |
| 4567 | Lab API (FastAPI) |
| 8080 | Traefik Dashboard |
| 9000 | MinIO API |
| 9001 | MinIO Console |
| 9090 | Prometheus |
| 3000 | Grafana |
| 16686 | Jaeger UI |
| 8200 | Vault |
| 8888 | Keycloak |
| 18080 | Gitea |
| 18081 | Woodpecker CI |
| 5432 | PostgreSQL |
| 6379 | Redis |
| 27017 | MongoDB |
| 4566 | LocalStack |
| 10000 | Azurite |

---

## Safety

- All Docker resources labelled `com.cloudlabs.project=local-cloud-lab`
- Cleanup only removes resources with that label — your other Docker work is safe
- `make cleanup` requires `--confirm` before destroying data
- No writes outside this directory
- All credentials are fake/dev-only — never use in real environments
- Real cloud commands clearly marked `# [REAL CLOUD - OPTIONAL]`

---

## Related Documentation

Each lab links back to the relevant Cloud-Learnings docs:

- `../05-aws/` — AWS documentation
- `../10-kubernetes/` — Kubernetes documentation
- `../11-terraform-opentofu/` — IaC documentation
- `../15-observability/` — Observability documentation
- `../14-security/` — Security documentation

---

## System Requirements

Minimum: 8 GB RAM, 20 GB free disk, Docker 24+, Docker Compose v2.

See [REQUIREMENTS.md](REQUIREMENTS.md) for full details including macOS, Linux, and Windows/WSL2.
