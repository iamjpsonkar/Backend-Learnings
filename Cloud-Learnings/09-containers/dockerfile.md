← [Previous: Docker Basics](./docker-basics.md) | [Home](../README.md) | [Next: Docker Compose →](./docker-compose.md)

---

# Dockerfile

A Dockerfile is a text file of instructions Docker reads top-to-bottom to build a container image. Each instruction creates a layer. Understanding layer caching is the key to fast, efficient builds.

---

## Instruction Reference

| Instruction | Purpose |
|-------------|---------|
| `FROM` | Base image — always first |
| `RUN` | Execute a shell command and commit the result as a new layer |
| `COPY` | Copy files from build context into the image |
| `ADD` | Like COPY, but also extracts tar archives and supports URLs (prefer COPY) |
| `WORKDIR` | Set working directory for subsequent instructions |
| `ENV` | Set environment variables available at build and runtime |
| `ARG` | Build-time variable (not available at runtime unless also set with ENV) |
| `EXPOSE` | Document the port the container listens on (does not publish) |
| `VOLUME` | Declare a mount point for a volume |
| `USER` | Switch to a non-root user |
| `CMD` | Default command run when the container starts (overridable) |
| `ENTRYPOINT` | Fixed executable — CMD becomes default arguments |
| `HEALTHCHECK` | Command Docker runs to check if the container is healthy |
| `LABEL` | Add metadata key-value pairs to the image |
| `ONBUILD` | Trigger instruction when the image is used as a base |

---

## Python Application — Production Dockerfile

```dockerfile
# syntax=docker/dockerfile:1
# Enable BuildKit for cache mounts and better performance

# ─── Stage 1: dependency builder ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Install build tools needed to compile Python packages with C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only the dependency files first — leverages Docker layer cache.
# If requirements.txt hasn't changed, pip install is skipped on rebuild.
COPY requirements.txt .

# Use BuildKit cache mount to persist pip's HTTP cache across builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/your-org/your-repo" \
      org.opencontainers.image.description="My App API" \
      org.opencontainers.image.version="1.0.0"

# Install only runtime system dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy compiled dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy application source (changes frequently — last to maximize cache hits)
COPY --chown=appuser:appgroup . .

# Drop root privileges
USER appuser

# Document the port (informational — does not publish it)
EXPOSE 8080

# Health check — Docker marks the container unhealthy if this fails 3 times
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# ENTRYPOINT: always run gunicorn
# CMD: default arguments — override with `docker run ... gunicorn --workers=8 ...`
ENTRYPOINT ["gunicorn"]
CMD ["--bind=0.0.0.0:8080", "--workers=4", "--timeout=30", "--log-level=info", "main:app"]
```

---

## Node.js Application — Production Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

# ─── Stage 1: install dependencies ───────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

# Copy package files first for layer caching
COPY package.json package-lock.json ./

# Install production + dev dependencies (dev needed for build)
RUN --mount=type=cache,target=/root/.npm \
    npm ci --frozen-lockfile

# ─── Stage 2: build ───────────────────────────────────────────────────────────
FROM deps AS builder

COPY . .

RUN npm run build

# ─── Stage 3: minimal runtime ─────────────────────────────────────────────────
FROM node:20-alpine AS runtime

LABEL org.opencontainers.image.description="My App Node API"

# Install dumb-init for proper signal handling (PID 1 problem)
RUN apk add --no-cache dumb-init

# Create non-root user
RUN addgroup --gid 1001 appgroup && \
    adduser --uid 1001 --ingroup appgroup --disabled-password appuser

WORKDIR /app

# Copy only production node_modules and built output
COPY --from=deps --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --chown=appuser:appgroup package.json ./

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:3000/health || exit 1

# dumb-init ensures signals are forwarded correctly to the Node process
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/index.js"]
```

---

## Go Application — Distroless Dockerfile

Go produces a statically linked binary — the runtime image can be completely empty.

```dockerfile
# syntax=docker/dockerfile:1

# ─── Stage 1: build ───────────────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

WORKDIR /src

# Download dependencies separately (cache them)
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Build statically linked binary (no CGO, no external library deps)
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-s -w" -o /app/server ./cmd/server

# ─── Stage 2: distroless runtime (no shell, no package manager) ───────────────
FROM gcr.io/distroless/static-debian12:nonroot

LABEL org.opencontainers.image.description="My App Go API"

# Copy only the binary
COPY --from=builder /app/server /server

EXPOSE 8080

# nonroot image runs as user 65532 by default
ENTRYPOINT ["/server"]
```

---

## Layer Caching Best Practices

The order of instructions determines cache efficiency. Put **infrequently changing** instructions early; **frequently changing** ones late.

```dockerfile
# WRONG — application code change busts pip install cache
FROM python:3.12-slim
COPY . .                        # ← busts cache on any file change
RUN pip install -r requirements.txt

# CORRECT — pip install only reruns when requirements.txt changes
FROM python:3.12-slim
COPY requirements.txt .         # ← only this file invalidates pip cache
RUN pip install -r requirements.txt
COPY . .                        # ← copies rest of app after installing deps
```

---

## .dockerignore

The `.dockerignore` file prevents unnecessary files from being sent to the build context — speeds up builds and reduces image size.

```
# .dockerignore
.git/
.gitignore
.github/
**/__pycache__/
**/*.pyc
**/*.pyo
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/
.ruff_cache/
.venv/
venv/
env/
dist/
build/
node_modules/
.npm/
*.log
.env
.env.*
!.env.example
Dockerfile*
docker-compose*.yml
README.md
docs/
tests/
```

---

## Multi-Platform Builds

```bash
# Enable multi-platform builds with BuildKit
docker buildx create --name multiplatform --use

# Build and push for both x86 and ARM
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    --tag your-registry/my-app:v1.2.3 \
    --tag your-registry/my-app:latest \
    --push \
    .

# Inspect the manifest (verify both platforms are present)
docker manifest inspect your-registry/my-app:latest
```

---

## Build Arguments vs Environment Variables

```dockerfile
# ARG — available only at build time
ARG APP_VERSION=unknown
ARG BUILD_DATE

# ENV — available at both build and runtime
ENV APP_VERSION=${APP_VERSION} \
    PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Usage: docker build --build-arg APP_VERSION=1.2.3 .
# WARNING: ARG values appear in `docker history` — never use for secrets
```

---

## Security Hardening Checklist

- [ ] Use a minimal base image (`-slim`, `-alpine`, distroless, or scratch)
- [ ] Run as a non-root user (`USER appuser`)
- [ ] Pin base image to a specific digest or version tag — never use `latest` in production
- [ ] Use multi-stage builds to exclude build tools from the final image
- [ ] Never `COPY` `.env` files or secrets — pass secrets at runtime via env vars or mounts
- [ ] Add a `HEALTHCHECK` instruction
- [ ] Set `--no-install-recommends` (apt) or `--no-cache` (apk) to avoid extra packages
- [ ] Scan images for vulnerabilities: `docker scout cves my-app:latest` or Trivy
- [ ] Use `COPY --chown=appuser:appgroup` instead of a separate `chown` RUN layer
- [ ] Minimize the number of `RUN` layers — chain with `&&` and clean up in the same layer

---

## Image Scanning

```bash
# Docker Scout (built into Docker Desktop / CLI)
docker scout cves my-app:latest
docker scout quickview my-app:latest

# Trivy (open-source — works with any registry)
trivy image my-app:latest
trivy image --severity HIGH,CRITICAL my-app:latest
trivy image --format sarif --output trivy-results.sarif my-app:latest

# Snyk
snyk container test my-app:latest
```

---

## References

- [Dockerfile reference](https://docs.docker.com/engine/reference/builder/)
- [Best practices for writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [BuildKit documentation](https://docs.docker.com/build/buildkit/)
- [Distroless base images](https://github.com/GoogleContainerTools/distroless)
- [Trivy vulnerability scanner](https://trivy.dev)
---

← [Previous: Docker Basics](./docker-basics.md) | [Home](../README.md) | [Next: Docker Compose →](./docker-compose.md)
