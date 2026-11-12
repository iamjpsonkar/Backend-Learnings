# Docker Compose Profiles

The platform uses a single `docker-compose.yml` file with Docker Compose profiles.

## What Are Profiles?

Profiles let you define groups of services and start only the group you need:

```bash
# Start only core services
docker compose --profile core up -d

# Start core + data
docker compose --profile core --profile data up -d
```

## How run.sh Handles Profiles

`run.sh` maps friendly names to profile combinations:

| `./run.sh start X` | Compose profiles activated |
|---|---|
| `core` | `core` |
| `dashboard` | `core dashboard` |
| `data` | `core data` |
| `messaging` | `core messaging` |
| `aws` | `core aws` |
| `azure` | `core azure` |
| `gcp` | `core gcp` |
| `cloud` | `core aws azure gcp cloud` |
| `observability` | `core observability` |
| `security` | `core security` |
| `cicd` | `core cicd` |
| `iac` | `core iac` |
| `apps` | `core apps` |
| `all` | all profiles |

## Profile to Service Mapping

### core
- `traefik` — reverse proxy
- `homepage` — dashboard
- `nginx-toolbox` — network toolbox

### dashboard
- `portainer` — Docker UI (opt-in, needs Docker socket)

### data
- `postgres` — PostgreSQL 16
- `mysql` — MySQL 8
- `mongo` — MongoDB 7
- `redis` — Redis 7
- `adminer` — DB management UI
- `redis-commander` — Redis UI

### messaging
- `rabbitmq` — RabbitMQ with management
- `redpanda` — Kafka-compatible
- `redpanda-console` — Redpanda UI

### aws
- `localstack` — AWS emulator
- `aws-cli` — AWS CLI helper
- `minio` — S3-compatible storage

### azure
- `azurite` — Azure storage emulator
- `azure-cli` — Azure CLI helper

### gcp
- `gcp-pubsub` — GCP Pub/Sub emulator
- `gcp-firestore` — GCP Firestore emulator
- `gcloud-cli` — gcloud CLI helper

### observability
- `prometheus` — metrics
- `grafana` — dashboards
- `loki` — logs
- `promtail` — log collector
- `tempo` — traces
- `otel-collector` — telemetry pipeline

### security
- `vault` — secrets (dev mode)
- `keycloak` — identity/SSO
- `trivy` — container scanning
- `checkov` — IaC scanning
- `hadolint` — Dockerfile linting

### cicd
- `gitea` — Git hosting
- `jenkins` — CI automation
- `registry` — Docker registry

### iac
- `terraform` — Terraform CLI
- `opentofu` — OpenTofu CLI
- `ansible` — Ansible CLI
- `kubectl` — kubectl CLI
- `helm` — Helm CLI

### apps
- `sample-api` — FastAPI application
- `sample-worker` — background worker
- `sample-frontend` — static frontend
- `event-producer` — event publisher
- `event-consumer` — event subscriber

## Resource Estimates

Start heavy profiles one at a time and monitor memory:

```bash
# Monitor resource usage
./run.sh resources
# or
docker stats --no-stream
```

## Combining Profiles

You can run multiple profiles simultaneously:

```bash
# Start AWS + observability (most common combination)
./run.sh start aws
./run.sh start observability

# This works because each run.sh start call includes "core"
# and compose starts the union of all running profiles
```

## Stopping Individual Services

```bash
# Stop just one service
docker compose --project-name cloud-learnings-lab stop grafana

# Restart just one service
docker compose --project-name cloud-learnings-lab restart grafana
```
