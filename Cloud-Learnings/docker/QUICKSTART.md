# Quick Start Guide

Get the platform running in 5 minutes.

## Prerequisites

- Docker Desktop 4.x+ (macOS/Windows) or Docker Engine 24+ (Linux)
- Docker Compose v2 (included with Docker Desktop)
- 4GB RAM free minimum (8GB+ recommended for cloud profiles)
- 10GB disk free minimum

Check with:

```bash
docker version
docker compose version
```

## Step 1 — Clone and enter the directory

```bash
git clone https://github.com/iamjpsonkar/Cloud-Learnings.git
cd Cloud-Learnings/docker
```

## Step 2 — Make run.sh executable

```bash
chmod +x run.sh
```

## Step 3 — Check system health

```bash
./run.sh doctor
```

Expected output: all checks green. If any fail, see [REQUIREMENTS.md](REQUIREMENTS.md).

## Step 4 — Create environment file

```bash
./run.sh setup
```

This copies `.env.example` to `.env`. All credentials are fake and local-only.

## Step 5 — Start core services

```bash
./run.sh start core
```

This starts:
- **Traefik** — reverse proxy and router (port 80/8080)
- **Homepage** — dashboard showing all services (port 3000)
- **Nginx toolbox** — debug/toolbox container

Takes ~30 seconds on first run (image pull). Subsequent starts are instant.

## Step 6 — View the dashboard

```bash
./run.sh open
```

Or open http://localhost:3000 in your browser.

## Step 7 — Check status

```bash
./run.sh status
./run.sh urls
```

---

## Start Additional Services

### AWS practice (LocalStack)

```bash
./run.sh start aws
```

Then follow the labs in `labs/aws-localstack/`.

### Data services (PostgreSQL, MySQL, MongoDB, Redis)

```bash
./run.sh start data
```

Then open http://localhost:8081 for Adminer (database UI).

### Observability stack (Prometheus, Grafana, Loki, Tempo)

```bash
./run.sh start observability
```

Then open http://localhost:3001 for Grafana (admin/admin by default).

### Security tools (Vault, Keycloak)

```bash
./run.sh start security
```

Then open http://localhost:8200 for Vault UI.

### All cloud emulators (AWS + Azure + GCP)

```bash
./run.sh start cloud
```

### Everything (needs 16GB+ RAM)

```bash
./run.sh start all
```

---

## Run a Lab

```bash
./run.sh lab list              # See all available labs
./run.sh lab start aws-001     # Start lab aws-001
./run.sh lab validate aws-001  # Validate your answers
./run.sh lab reset aws-001     # Reset to clean state
```

Lab files are in `labs/<lab-name>/`:
- `README.md` — introduction
- `tasks.md` — what to do
- `commands.md` — commands reference
- `expected-output.md` — what success looks like
- `validate.md` — how to check your work
- `troubleshooting.md` — common issues
- `solution.md` — answers (try yourself first!)

---

## Stop Everything

```bash
./run.sh stop
```

## Clean Up

```bash
./run.sh clean   # Removes containers and volumes (confirmation required)
./run.sh nuke    # Full cleanup including networks (confirmation required)
```

**Never deletes files outside docker/. Always asks for confirmation before destructive operations.**

---

## Troubleshooting Quick Fixes

| Problem | Fix |
|---|---|
| Port already in use | `./run.sh clean` then edit `.env` to change port |
| Container keeps restarting | `./run.sh logs <service>` to see error |
| Out of memory | Stop heavy profiles, start only what you need |
| Docker socket denied | Don't run as root; add user to docker group |
| Slow startup | Wait 60s on first run for image pulls |

More at [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
