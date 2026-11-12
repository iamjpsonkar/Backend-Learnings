# Cloud-Learnings Lab Platform

A complete self-contained Docker-based practice platform for learning AWS, Azure, GCP, Kubernetes, Terraform, observability, security, CI/CD, and more — all locally, for free.

## What Is This?

This `docker/` directory contains everything needed to practice cloud concepts without paying for cloud accounts. It uses Docker Compose profiles to let you start only what you need.

```
docker/
├── docker-compose.yml    # Single compose file — all services, all profiles
├── run.sh                # Main control script
├── .env.example          # Environment variable template
├── configs/              # Service configuration files
├── apps/                 # Sample apps (API, worker, frontend, event producer/consumer)
├── labs/                 # Guided labs with tasks, commands, solutions
├── practice/             # DIY exercises (beginner → advanced)
├── infrastructure/       # Terraform, Ansible, Kubernetes, Helm, Kustomize
├── data/                 # Seed data, sample bills, logs, events
├── reports/              # Lab results, scan reports, cost analysis
├── assets/               # Diagrams, screenshots, icons
└── docs/                 # Deep-dive documentation
```

## Quick Start

```bash
cd docker
chmod +x run.sh
./run.sh setup       # Create .env from .env.example
./run.sh doctor      # Check prerequisites
./run.sh start core  # Start lightweight core services
./run.sh urls        # Show all service URLs
```

## Profiles

| Profile | Services | Resources |
|---|---|---|
| `core` | Traefik, Homepage dashboard, Nginx toolbox | Light |
| `dashboard` | Homepage, Portainer (opt-in) | Light |
| `data` | PostgreSQL, MySQL, MongoDB, Redis, Adminer, Redis Commander | Medium |
| `messaging` | RabbitMQ, Redpanda | Medium |
| `aws` | LocalStack, AWS CLI | Medium |
| `azure` | Azurite, Azure CLI | Light |
| `gcp` | GCP Pub/Sub emulator, Firestore emulator, gcloud CLI | Medium |
| `cloud` | aws + azure + gcp combined | Heavy |
| `observability` | Prometheus, Grafana, Loki, Promtail, Tempo, OTel Collector | Heavy |
| `security` | Vault, Keycloak, Trivy, Checkov, Hadolint | Heavy |
| `cicd` | Gitea, Jenkins, Docker Registry | Heavy |
| `iac` | Terraform, OpenTofu, Ansible, kubectl, Helm | Light (CLI) |
| `apps` | Sample API, Worker, Frontend, Event Producer/Consumer | Medium |
| `all` | Everything | Very Heavy |

## Common Commands

```bash
./run.sh start              # Start core profile
./run.sh start aws          # Start core + AWS emulator
./run.sh start cloud        # Start core + all cloud emulators
./run.sh start observability
./run.sh start all          # Start everything (needs 16GB+ RAM)

./run.sh stop               # Stop all containers
./run.sh status             # Show running containers
./run.sh logs               # Tail all logs
./run.sh urls               # Print all service URLs
./run.sh open               # Open dashboard in browser

./run.sh lab list           # List available labs
./run.sh lab start aws-001  # Start a specific lab
./run.sh lab validate aws-001

./run.sh clean              # Remove containers/volumes (with confirmation)
./run.sh nuke               # Full cleanup (with confirmation)
./run.sh doctor             # Check prerequisites and system health
```

## Labs Available

See [LABS.md](LABS.md) for the full list. Quick overview:

- **AWS/LocalStack**: S3, SQS, SNS, DynamoDB, Lambda, Terraform
- **Azure/Azurite**: Blob storage, Queue, Table storage
- **GCP emulators**: Pub/Sub, Firestore, Cloud Run simulation
- **Docker/Networking**: Networks, DNS, reverse proxy, TLS
- **Kubernetes**: Pods, Deployments, Services, Ingress, Helm, Kustomize
- **Terraform/OpenTofu**: State, modules, LocalStack provider
- **Ansible**: Playbooks, templates, idempotency
- **Observability**: Metrics, logs, traces, Grafana dashboards
- **Security**: Vault, Keycloak, Trivy, Checkov, secret scanning
- **CI/CD**: Gitea, Jenkins, local registry, broken pipeline debug
- **Databases**: PostgreSQL, MySQL, MongoDB, Redis
- **Messaging**: RabbitMQ, Redpanda/Kafka
- **FinOps**: Cost simulation, tagging, idle resource detection
- **SRE**: Incident response, runbooks, postmortem practice

## Requirements

See [REQUIREMENTS.md](REQUIREMENTS.md) for system requirements.

## Ports

See [PORTS.md](PORTS.md) for a full port mapping table.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for network and service architecture.

## Security

See [SECURITY.md](SECURITY.md) for credential and security guidance.

**All credentials in `.env.example` are fake and local-only. Never use real cloud credentials here.**

## Cost Safety

See [COST-SAFETY.md](COST-SAFETY.md). Default mode costs nothing. Real cloud integrations may cost money.

## Documentation

See [docs/](docs/) for deep-dive guides:
- [How the platform works](docs/how-the-platform-works.md)
- [Docker Compose profiles](docs/docker-compose-profiles.md)
- [Local cloud emulators](docs/local-cloud-emulators.md)
- [Adding new labs](docs/adding-new-labs.md)
- [Troubleshooting playbook](docs/troubleshooting-playbook.md)
- [Real cloud extensions](docs/real-cloud-extensions.md)

## Windows Users

Windows is supported via WSL2. Run everything inside a WSL2 Ubuntu terminal with Docker Desktop (WSL2 backend enabled).

---

**Project**: `cloud-learnings-lab`
**Label prefix**: `com.cloudlearnings.project`
**Network**: 7 named networks (public_net, private_net, data_net, observability_net, security_net, ci_net, cloud_net)
