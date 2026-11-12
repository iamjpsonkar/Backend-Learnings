# Architecture

## Overview

The Cloud-Learnings Lab Platform is a single Docker Compose project with 7 named networks, structured to simulate cloud network topology concepts locally.

```
┌─────────────────────────────────────────────────────────────────┐
│                         HOST MACHINE                            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   public_net                              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────┐              │  │
│  │  │ Traefik  │  │Homepage  │  │  Adminer  │  ...          │  │
│  │  └────┬─────┘  └──────────┘  └───────────┘              │  │
│  └───────┼──────────────────────────────────────────────────┘  │
│          │                                                      │
│  ┌───────┼──────────────────────────────────────────────────┐  │
│  │       │          private_net (internal)                   │  │
│  │  ┌────┴──────┐  ┌───────────────┐  ┌──────────────┐     │  │
│  │  │   Nginx   │  │ Sample Worker │  │Event Consumer│     │  │
│  │  └───────────┘  └───────────────┘  └──────────────┘     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    data_net (internal)                    │  │
│  │  ┌──────────┐  ┌─────────┐  ┌───────────┐  ┌────────┐  │  │
│  │  │PostgreSQL│  │  MySQL  │  │  MongoDB  │  │ Redis  │  │  │
│  │  └──────────┘  └─────────┘  └───────────┘  └────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  observability_net                        │  │
│  │  ┌──────────┐  ┌─────────┐  ┌────────┐  ┌────────────┐ │  │
│  │  │Prometheus│  │ Grafana │  │  Loki  │  │   Tempo    │ │  │
│  │  └──────────┘  └─────────┘  └────────┘  └────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               security_net (internal)                     │  │
│  │  ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌──────────┐ │  │
│  │  │  Vault  │  │ Keycloak  │  │  Trivy  │  │ Checkov  │ │  │
│  │  └─────────┘  └───────────┘  └─────────┘  └──────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      ci_net                               │  │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────────────────────┐ │  │
│  │  │  Gitea  │  │ Jenkins │  │  Docker Registry :5000   │ │  │
│  │  └─────────┘  └─────────┘  └──────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     cloud_net                             │  │
│  │  ┌───────────┐  ┌──────────┐  ┌─────────┐  ┌─────────┐ │  │
│  │  │LocalStack │  │  MinIO   │  │Azurite  │  │GCP Emu. │ │  │
│  │  └───────────┘  └──────────┘  └─────────┘  └─────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Networks

| Network | Type | Purpose | Services |
|---|---|---|---|
| `public_net` | bridge | Public-facing; Traefik routes to these | Traefik, Homepage, Adminer, Grafana, Gitea, Vault (UI), Sample API, Sample Frontend |
| `private_net` | bridge (internal) | Internal only; no external exposure | Nginx toolbox, Sample Worker, Event Consumer, Ansible |
| `data_net` | bridge (internal) | Database isolation | PostgreSQL, MySQL, MongoDB, Redis |
| `observability_net` | bridge | Metrics/logs/traces between tools | Prometheus, Grafana, Loki, Promtail, Tempo, OTel Collector |
| `security_net` | bridge (internal) | Security tools isolation | Vault, Keycloak, Trivy, Checkov, Hadolint |
| `ci_net` | bridge | CI/CD tool network | Gitea, Jenkins, Registry |
| `cloud_net` | bridge | Cloud emulator services | LocalStack, MinIO, Azurite, GCP emulators, CLI helpers |

### Internal networks

Networks marked `internal: true` have no internet routing. Services on them can only communicate with each other and with services that share the same network. This simulates:

- `private_net` → private subnets (backend services with no public exposure)
- `data_net` → data tier (databases not directly reachable from public)
- `security_net` → security zone (Vault and Keycloak isolated)

### Multi-network services

Services that span networks bridge between tiers:

- **Traefik** — `public_net` only (reads Docker socket, routes traffic)
- **Sample API** — `public_net` + `data_net` + `observability_net` (public-facing, needs DB + telemetry)
- **Adminer** — `public_net` + `data_net` (UI on public, data on private)
- **Grafana** — `observability_net` + `public_net` (dashboard accessible publicly)
- **Vault** — `security_net` + `public_net` (UI accessible, backend isolated)

## Profiles and Dependency Graph

```
core
 └── traefik, homepage, nginx-toolbox

dashboard
 └── core + portainer

data
 └── core + postgres, mysql, mongo, redis, adminer, redis-commander

messaging
 └── core + rabbitmq, redpanda, redpanda-console

aws
 └── core + localstack, aws-cli, minio

azure
 └── core + azurite, azure-cli

gcp
 └── core + gcp-pubsub, gcp-firestore, gcloud-cli

cloud  (run.sh alias)
 └── aws + azure + gcp

observability
 └── core + prometheus, grafana, loki, promtail, tempo, otel-collector

security
 └── core + vault, keycloak, trivy, checkov, hadolint

cicd
 └── core + gitea, jenkins, registry

iac
 └── core + terraform, opentofu, ansible, kubectl, helm

apps
 └── core + sample-api, sample-worker, sample-frontend, event-producer, event-consumer

all
 └── core + data + messaging + aws + azure + gcp + observability + security + cicd + iac + apps
```

## Service Categories

### Reverse Proxy + Dashboard
- **Traefik v3** routes all web traffic. Services opt-in via labels.
- **Homepage** provides a unified service dashboard with real-time health status.

### Cloud Emulators
- **LocalStack 3.0** — emulates S3, SQS, SNS, DynamoDB, Lambda, IAM, KMS, Secrets Manager, and more
- **Azurite** — emulates Azure Blob, Queue, and Table storage
- **MinIO** — S3-compatible object storage (more stable than LocalStack S3 for some use cases)
- **GCP Pub/Sub emulator** — topic/subscription messaging without real GCP
- **GCP Firestore emulator** — NoSQL document database without real GCP

### Observability Stack
Full LGTM stack: Loki (logs), Grafana (dashboards), Tempo (traces), Prometheus (metrics) + OTel Collector.

```
App → OTel SDK → OTel Collector → Tempo (traces)
                              ↘ Loki (logs)
                              ↘ Prometheus (metrics)
                                    ↓
                               Grafana (visualization)
```

### Security Stack
- **Vault** (dev mode) — secrets management, KV store, dynamic credentials
- **Keycloak** — OIDC/OAuth2 identity provider, SSO simulation
- **Trivy** — container image vulnerability scanning
- **Checkov** — IaC security scanning (Terraform, Ansible, K8s manifests)
- **Hadolint** — Dockerfile linting

### CI/CD Stack
- **Gitea** — GitHub-like Git hosting (repos, webhooks, pull requests)
- **Jenkins** — CI pipeline automation
- **Docker Registry** — local image storage

### Data Layer
Simulates a multi-database production environment:
- PostgreSQL 16 (primary relational DB)
- MySQL 8 (legacy/compatibility)
- MongoDB 7 (document store)
- Redis 7 (cache + sessions)

## Directory Structure

```
docker/
├── docker-compose.yml      # All services, one file
├── run.sh                  # Control script
├── .env                    # Local secrets (not committed)
├── .env.example            # Template with fake values
├── configs/                # Static service configurations
│   ├── traefik/            # traefik.yaml, dynamic.yaml
│   ├── homepage/           # config.yaml, services.yaml
│   ├── prometheus/         # prometheus.yml, rules/
│   ├── grafana/            # provisioning/datasources/, dashboards/
│   ├── loki/               # loki-config.yaml
│   ├── promtail/           # promtail-config.yaml
│   ├── tempo/              # tempo.yaml
│   ├── otel-collector/     # otel-config.yaml
│   ├── vault/              # vault.hcl
│   ├── keycloak/           # realm-export.json
│   ├── localstack/init/    # AWS resource init scripts
│   ├── nginx/              # nginx.conf
│   ├── postgres/init/      # SQL init scripts
│   ├── mysql/init/         # SQL init scripts
│   ├── mongo/init/         # JS init scripts
│   ├── redis/              # redis.conf
│   ├── rabbitmq/           # rabbitmq.conf, definitions.json
│   └── jenkins/            # Custom Dockerfile
├── apps/                   # Sample application source code
├── labs/                   # Guided practice labs
├── practice/               # DIY exercises
├── infrastructure/         # Terraform, Ansible, K8s, Helm
├── data/                   # Seed data, sample datasets
├── reports/                # Scan and lab result output
└── docs/                   # Deep-dive documentation
```

## Kubernetes

Kubernetes is NOT included as a Compose service. Local Kubernetes uses `kind` or `k3d` on the host:

```bash
./run.sh kubernetes create kind   # Creates a kind cluster
./run.sh kubernetes create k3d    # Creates a k3d cluster
```

This avoids privileged containers and Docker-in-Docker complexity. See `labs/kubernetes-local/` for guided labs.
