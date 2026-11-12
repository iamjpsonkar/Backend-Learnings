← [Previous: Dockerfile](./dockerfile.md) | [Home](../README.md) | [Next: Container Registries →](./container-registries.md)

---

# Docker Compose

Docker Compose defines and runs multi-container applications from a single YAML file. It is the standard tool for local development environments and integration testing.

---

## Installation

```bash
# Docker Desktop includes Compose v2 (plugin, not separate binary)
docker compose version

# Linux — install Compose v2 plugin
mkdir -p ~/.docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
    -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose
docker compose version
```

---

## Core Concepts

| Concept | Description |
|---------|------------|
| **Service** | A container definition — image, ports, volumes, env vars |
| **Volume** | Named persistent storage shared between services or preserved across restarts |
| **Network** | All services in a compose file share a default network and can reach each other by service name |
| **Profile** | Optional grouping — services only start when their profile is activated |
| **Depends_on** | Declare startup order and health dependencies between services |

---

## Complete Production-like docker-compose.yml

```yaml
# docker-compose.yml — full-stack local development environment
# Usage: docker compose up -d

services:

  # ─── Application API ─────────────────────────────────────────────────────────
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime          # use the `runtime` stage in a multi-stage build
    image: my-app/api:local
    container_name: my-app-api
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      APP_ENV: development
      DATABASE_URL: postgres://myapp:secret@postgres:5432/myapp
      REDIS_URL: redis://:redissecret@redis:6379/0
      SECRET_KEY: local-dev-secret-not-for-production
    env_file:
      - .env.local             # override with a local file if present
    volumes:
      - ./src:/app/src:ro      # mount source for hot-reload in dev
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s
    labels:
      com.example.service: "api"
      com.example.environment: "local"

  # ─── Background Worker ────────────────────────────────────────────────────────
  worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    image: my-app/api:local
    container_name: my-app-worker
    restart: unless-stopped
    command: ["celery", "-A", "myapp.tasks", "worker", "--loglevel=info", "--concurrency=4"]
    environment:
      APP_ENV: development
      DATABASE_URL: postgres://myapp:secret@postgres:5432/myapp
      REDIS_URL: redis://:redissecret@redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - backend
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M

  # ─── PostgreSQL ───────────────────────────────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    container_name: my-app-postgres
    restart: unless-stopped
    ports:
      - "5432:5432"            # expose to host for psql / database GUI tools
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: myapp
      POSTGRES_PASSWORD: secret
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    networks:
      - backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U myapp -d myapp"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s

  # ─── Redis ────────────────────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    container_name: my-app-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: ["redis-server", "--requirepass", "redissecret", "--appendonly", "yes"]
    volumes:
      - redis_data:/data
    networks:
      - backend
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redissecret", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ─── Nginx reverse proxy ──────────────────────────────────────────────────────
  nginx:
    image: nginx:1.27-alpine
    container_name: my-app-nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      api:
        condition: service_healthy
    networks:
      - backend

  # ─── Mailpit (local email testing) ───────────────────────────────────────────
  mailpit:
    image: axllent/mailpit:latest
    container_name: my-app-mailpit
    restart: unless-stopped
    ports:
      - "8025:8025"            # web UI
      - "1025:1025"            # SMTP
    networks:
      - backend
    profiles:
      - tools                  # only starts with: docker compose --profile tools up

  # ─── Adminer (DB GUI) ─────────────────────────────────────────────────────────
  adminer:
    image: adminer:latest
    container_name: my-app-adminer
    restart: unless-stopped
    ports:
      - "8081:8080"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - backend
    profiles:
      - tools

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  backend:
    driver: bridge
```

---

## Environment Variable Files

```bash
# .env — default values (committed — no secrets)
APP_NAME=my-app
LOG_LEVEL=INFO
PORT=8080

# .env.local — developer overrides (git-ignored)
DATABASE_URL=postgres://myapp:localpass@localhost:5432/myapp
SECRET_KEY=local-only-secret
```

```yaml
# Reference in compose
services:
  api:
    env_file:
      - .env
      - .env.local   # overrides .env when present
```

---

## Override Files

Use `docker-compose.override.yml` for local-only customizations. Docker Compose automatically merges it with `docker-compose.yml`.

```yaml
# docker-compose.override.yml — local dev overrides (git-ignored)
services:
  api:
    build:
      target: dev              # use dev stage with dev tools installed
    volumes:
      - .:/app                 # full mount for hot-reload
    command: ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8080"]
    environment:
      LOG_LEVEL: DEBUG
```

```bash
# Use a specific override file explicitly
docker compose -f docker-compose.yml -f docker-compose.test.yml up
```

---

## Essential Commands

```bash
# Start all services (build if needed, detached)
docker compose up -d

# Start with a specific profile
docker compose --profile tools up -d

# Rebuild images before starting
docker compose up -d --build

# Force recreate containers (even if config hasn't changed)
docker compose up -d --force-recreate

# Start specific services only
docker compose up -d api postgres redis

# Stop all services (containers remain, can be restarted)
docker compose stop

# Stop and remove containers, networks (volumes preserved)
docker compose down

# Stop and remove everything including volumes (DATA LOSS — use carefully)
docker compose down -v

# View status of all services
docker compose ps

# View logs (all services)
docker compose logs -f

# View logs for a specific service
docker compose logs -f api

# Execute a command in a running service
docker compose exec api bash
docker compose exec postgres psql -U myapp

# Run a one-off command in a new container (does not replace running service)
docker compose run --rm api python manage.py migrate
docker compose run --rm api pytest tests/

# Scale a service (create multiple replicas)
docker compose up -d --scale worker=4

# Pull latest images
docker compose pull

# Rebuild without cache
docker compose build --no-cache

# Validate compose file syntax
docker compose config
```

---

## Integration Testing with Compose

```yaml
# docker-compose.test.yml — CI test environment
services:
  api:
    build:
      context: .
      target: runtime
    environment:
      APP_ENV: test
      DATABASE_URL: postgres://test:test@postgres-test:5432/test
    depends_on:
      postgres-test:
        condition: service_healthy
    networks:
      - test

  test-runner:
    build:
      context: .
      target: runtime
    command: ["pytest", "tests/integration", "-v", "--tb=short", "--junitxml=/results/junit.xml"]
    environment:
      APP_ENV: test
      DATABASE_URL: postgres://test:test@postgres-test:5432/test
      API_BASE_URL: http://api:8080
    volumes:
      - ./test-results:/results
    depends_on:
      api:
        condition: service_healthy
    networks:
      - test

  postgres-test:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    networks:
      - test
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test -d test"]
      interval: 5s
      retries: 5

networks:
  test:
    driver: bridge
```

```bash
# Run integration tests in CI
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
TEST_EXIT=$(docker compose -f docker-compose.test.yml ps test-runner --format json | jq -r '.[0].ExitCode')
docker compose -f docker-compose.test.yml down -v
exit $TEST_EXIT
```

---

## Healthcheck Patterns

```yaml
# PostgreSQL
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
  interval: 5s
  timeout: 5s
  retries: 5

# MySQL
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
  interval: 5s
  timeout: 5s
  retries: 5

# Redis
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 5s
  timeout: 3s
  retries: 5

# HTTP endpoint
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 30s
```

---

## References

- [Docker Compose documentation](https://docs.docker.com/compose/)
- [Compose file reference](https://docs.docker.com/compose/compose-file/)
- [Compose CLI reference](https://docs.docker.com/compose/reference/)
---

← [Previous: Dockerfile](./dockerfile.md) | [Home](../README.md) | [Next: Container Registries →](./container-registries.md)
