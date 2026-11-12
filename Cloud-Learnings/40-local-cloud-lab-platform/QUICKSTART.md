# Quickstart Guide

Get the local cloud lab platform running in under 5 minutes.

---

## Prerequisites (check these first)

```bash
docker --version          # need 24.0+
docker compose version    # need 2.20+
python3 --version         # need 3.11+
make --version            # any version
```

If any are missing, see [REQUIREMENTS.md](REQUIREMENTS.md).

---

## Step 1: Copy Environment File

```bash
cd 40-local-cloud-lab-platform
cp .env.example .env
```

The defaults work for local use. Edit `.env` only if you need to change ports.

---

## Step 2: Run the Doctor Check

```bash
make doctor
```

This checks Docker, Python, available ports, disk space, and RAM. Fix any failures before continuing.

---

## Step 3: One-Time Setup

```bash
make setup
```

This:
- Creates the Python venv for the API and lab runner
- Installs Python dependencies
- Initializes the SQLite database
- Validates all lab YAML files
- Creates Docker networks and volumes

---

## Step 4: Start Core Services

```bash
make start-core
```

This starts:
- MinIO (object storage, S3-compatible)
- Traefik (reverse proxy + dashboard)
- FastAPI backend (lab API)
- React dashboard (UI)

Wait about 15 seconds for all services to be healthy.

---

## Step 5: Verify Everything Works

```bash
make health
```

Expected output:
```
[OK] API      http://localhost:4567/health
[OK] UI       http://localhost:3001
[OK] MinIO    http://localhost:9001
[OK] Traefik  http://localhost:8080
```

---

## Step 6: Open the Dashboard

```bash
open http://localhost:3001        # macOS
xdg-open http://localhost:3001   # Linux
# Windows: open browser manually
```

The dashboard shows:
- Lab catalog with difficulty and estimated time
- Your progress and completed labs
- Service status for running Docker profiles
- Quick-start buttons for each profile

---

## Step 7: Run Your First Lab

```bash
make run-lab LAB=04-docker/docker-basics
```

This:
1. Checks that required services are running
2. Prints the lab brief
3. Waits for you to complete the tasks
4. Runs validation when you type `done`
5. Shows your score and feedback

---

## Step 8: Stop When Done

```bash
make stop          # stops all containers (keeps data)
make stop-clean    # stops and removes volumes (wipes data)
```

---

## Common First Labs (by skill level)

### Beginner (start here)
```bash
make run-lab LAB=00-foundations/platform-orientation
make run-lab LAB=01-linux/basic-commands
make run-lab LAB=04-docker/docker-basics
```

### Intermediate
```bash
make run-lab LAB=05-kubernetes/deploy-first-app
make run-lab LAB=06-terraform-opentofu/terraform-basics
make run-lab LAB=08-aws-local/s3-operations
```

### Advanced
```bash
make run-lab LAB=05-kubernetes/k8s-crashloopbackoff
make run-lab LAB=11-security/vault-secrets-injection
make run-lab LAB=12-observability/slo-error-budget
```

---

## Add More Services

```bash
make start-observability   # Prometheus + Grafana + Loki + Jaeger
make start-security        # Vault + Keycloak
make start-data            # PostgreSQL + MongoDB + Redis + Redpanda + RabbitMQ
make start-aws-local       # LocalStack (S3, SQS, Lambda, DynamoDB)
make start-azure-local     # Azurite (Blob, Queue, Table)
make start-cicd            # Gitea + Woodpecker CI
```

---

## Troubleshooting

If something doesn't work, run:

```bash
make logs SERVICE=api      # view API logs
make logs SERVICE=ui       # view UI logs
make status                # show all container statuses
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.

---

## What's Next?

- Browse [LAB_INDEX.md](LAB_INDEX.md) for the full lab catalog
- Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand how the platform works
- Check [ROADMAP.md](ROADMAP.md) for upcoming labs
