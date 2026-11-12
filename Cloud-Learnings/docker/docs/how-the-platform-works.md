# How the Platform Works

## Overview

The Cloud-Learnings Lab Platform is a Docker Compose application with:

- **1 compose file** — all services, all profiles, no separate files
- **7 named networks** — simulating cloud network topology
- **1 control script** — `run.sh` handles everything
- **Profiles** — start only what you need

## Startup Sequence

When you run `./run.sh start core`:

1. `run.sh` loads `.env` (creates it from `.env.example` if missing)
2. Maps "core" to compose profiles: `["core"]`
3. Runs: `docker compose --project-name cloud-learnings-lab --file docker-compose.yml --profile core up -d`
4. Docker pulls any missing images
5. Docker creates named networks with labels
6. Docker starts containers (Traefik, Homepage, Nginx)
7. Health checks run until services are ready
8. `run.sh` prints status and URLs

## Profile Loading

When you run `./run.sh start aws`:

1. `run.sh` maps "aws" → profiles: `["core", "aws"]`
2. Compose starts: `--profile core --profile aws`
3. All services with `profiles: [core]` OR `profiles: [aws]` start
4. Services without a matching profile stay stopped

## Docker Compose Project Name

All resources use project name: `cloud-learnings-lab`

This means:
- Containers are prefixed: `cloud-learnings-lab-traefik-1`
- You can run `docker compose --project-name cloud-learnings-lab ps` to list containers
- The label `com.cloudlearnings.project=cloud-learnings-lab` is on every container
- `./run.sh clean` only removes containers/volumes/networks with this label — nothing else

## Network Flow

### HTTP Request Flow (Traefik)

```
Browser → localhost:80 → Traefik (public_net) → Service (public_net)
```

Traefik reads Docker container labels to discover services. Services opt-in with:
```yaml
labels:
  traefik.enable: "true"
  traefik.http.routers.myservice.rule: "PathPrefix(`/myapp`)"
```

### Database Access Flow

```
App Container (private_net + data_net) → PostgreSQL (data_net only)
```

PostgreSQL is on `data_net` (internal=true). Apps connect via Docker DNS: `postgres:5432`.
The database port 5432 is also exposed to localhost for external tools.

### Observability Flow

```
App → OTel SDK → OTLP gRPC → OTel Collector (port 4317)
                                     ↓ traces → Tempo
                                     ↓ logs   → Loki
                                     ↓ metrics → Prometheus

Promtail → reads Docker container logs → Loki

Grafana → queries → Prometheus + Loki + Tempo
```

## Docker DNS

Inside Docker networks, containers resolve each other by container name:
- `postgres` resolves to the PostgreSQL container IP
- `redis` resolves to the Redis container IP
- `localstack` resolves to the LocalStack container IP

This is why:
- App code uses `postgres:5432` not `localhost:5432`
- Grafana data sources use `http://prometheus:9090` not `http://localhost:9090`
- The AWS CLI container uses `--endpoint-url=http://localstack:4566`

## Volumes

Named volumes are used for persistence:
- `cloud-learnings-postgres-data` — PostgreSQL data
- `cloud-learnings-grafana-data` — Grafana dashboards/settings
- etc.

Volumes survive `docker compose down` but are removed by `./run.sh clean`.

## Labels

Every resource carries labels for identification:
```yaml
labels:
  com.cloudlearnings.project: "cloud-learnings-lab"
  com.cloudlearnings.component: "database"
```

This allows `./run.sh clean` to remove exactly this project's resources without affecting other Docker projects.

## Health Checks

All stateful services have health checks. Docker Compose `depends_on` with `condition: service_healthy` ensures dependent services don't start until the dependency is ready.

Check health status:
```bash
docker inspect --format='{{.State.Health.Status}}' cloud-learnings-postgres
# Expected: healthy
```
