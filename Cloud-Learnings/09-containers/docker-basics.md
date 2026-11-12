← [Previous: Containers](./README.md) | [Home](../README.md) | [Next: Dockerfile →](./dockerfile.md)

---

# Docker Basics

---

## Installation

```bash
# macOS — Docker Desktop (includes CLI, daemon, compose)
brew install --cask docker

# Linux (Ubuntu/Debian) — Docker Engine (server)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER  # add yourself to the docker group (re-login after)
newgrp docker                   # activate group in current shell without re-login

# Verify
docker version
docker info
```

---

## Images

An **image** is a read-only template built from layers. Pull from a registry, build locally, or both.

```bash
# Pull an image from Docker Hub
docker pull python:3.12-slim
docker pull nginx:1.27-alpine
docker pull postgres:16

# Pull a specific digest (immutable — good for production)
docker pull python@sha256:abc123...

# List local images
docker images
docker image ls --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Inspect image metadata (layers, env, cmd, etc.)
docker inspect python:3.12-slim

# Show image history (layers and their sizes)
docker history python:3.12-slim

# Remove an image
docker rmi python:3.12-slim

# Remove all dangling images (untagged layers from old builds)
docker image prune

# Remove all unused images
docker image prune -a

# Save an image to a tar file (for air-gapped transfer)
docker save python:3.12-slim | gzip > python-3.12-slim.tar.gz

# Load from tar file
docker load < python-3.12-slim.tar.gz
```

---

## Containers

A **container** is a running instance of an image.

```bash
# Run a container (foreground — exits when process exits)
docker run python:3.12-slim python -c "print('hello')"

# Run interactively (-it = interactive + pseudo-TTY)
docker run -it python:3.12-slim bash

# Run in detached mode (background) with a name
docker run -d --name my-app -p 8080:8080 my-app:latest

# Port mapping: -p HOST_PORT:CONTAINER_PORT
docker run -d -p 80:80 -p 443:443 nginx:1.27-alpine

# Set environment variables
docker run -d \
    --name my-app \
    -e APP_ENV=production \
    -e DATABASE_URL=postgres://user:pass@host/db \
    my-app:latest

# Pass environment from a file
docker run --env-file .env my-app:latest

# Limit resources (important in production to prevent noisy-neighbor)
docker run -d \
    --name my-app \
    --memory=512m \
    --cpus=1.0 \
    my-app:latest

# Remove container automatically when it exits (--rm)
docker run --rm python:3.12-slim python -c "print('one-off')"

# List running containers
docker ps
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

# List all containers (including stopped)
docker ps -a

# Inspect a container (full metadata, networking, mounts, etc.)
docker inspect my-app

# View logs
docker logs my-app
docker logs -f my-app          # follow (streaming)
docker logs --tail=100 my-app  # last 100 lines
docker logs --since=1h my-app  # last 1 hour

# Execute a command inside a running container
docker exec -it my-app bash
docker exec my-app python -c "import django; print(django.__version__)"

# Copy files between host and container
docker cp ./config.json my-app:/app/config.json
docker cp my-app:/app/logs/app.log ./app.log

# Stop, start, restart
docker stop my-app    # SIGTERM, then SIGKILL after timeout (default 10s)
docker start my-app
docker restart my-app

# Kill immediately (SIGKILL)
docker kill my-app

# Remove a container
docker rm my-app
docker rm -f my-app  # force-remove running container

# Remove all stopped containers
docker container prune

# View container resource usage
docker stats
docker stats my-app --no-stream
```

---

## Volumes

Volumes persist data beyond the lifecycle of a container. They are managed by Docker and stored in `/var/lib/docker/volumes/` on the host.

```bash
# Create a named volume
docker volume create my-app-data

# List volumes
docker volume ls

# Inspect a volume (see mount point on host)
docker volume inspect my-app-data

# Mount a volume into a container
docker run -d \
    --name postgres \
    -v my-app-data:/var/lib/postgresql/data \
    -e POSTGRES_PASSWORD=secret \
    postgres:16

# Bind mount (host directory → container path)
# Good for local development — changes on host are immediately visible in container
docker run -d \
    --name my-app-dev \
    -v $(pwd):/app \
    -w /app \
    python:3.12-slim \
    python -m uvicorn main:app --reload --host 0.0.0.0 --port 8080

# Read-only bind mount (safer for config files)
docker run -d \
    -v $(pwd)/config:/app/config:ro \
    my-app:latest

# tmpfs mount (in-memory, not persisted — for secrets or temp files)
docker run -d \
    --tmpfs /app/tmp:size=100m \
    my-app:latest

# Remove a volume
docker volume rm my-app-data

# Remove all unused volumes
docker volume prune
```

---

## Networks

```bash
# List networks
docker network ls

# Docker default networks:
# bridge  — default for standalone containers (isolated from host)
# host    — shares host network stack (no isolation)
# none    — no network access

# Create a user-defined bridge network (recommended — provides DNS by container name)
docker network create my-app-net

# Connect containers to the network
docker run -d --name postgres --network my-app-net postgres:16
docker run -d --name my-app --network my-app-net my-app:latest
# my-app can reach postgres at hostname "postgres"

# Connect a running container to an additional network
docker network connect my-app-net my-app

# Disconnect
docker network disconnect my-app-net my-app

# Inspect network (see connected containers and their IPs)
docker network inspect my-app-net

# Remove unused networks
docker network prune
```

---

## Build

```bash
# Build an image from the Dockerfile in the current directory
docker build -t my-app:latest .

# Tag with a version
docker build -t my-app:1.2.3 -t my-app:latest .

# Build with build args
docker build --build-arg APP_VERSION=1.2.3 -t my-app:1.2.3 .

# Build for a specific platform (cross-compilation)
docker buildx build --platform linux/amd64,linux/arm64 -t my-app:latest --push .

# Build without using cache (force full rebuild)
docker build --no-cache -t my-app:latest .

# Use a specific Dockerfile
docker build -f Dockerfile.prod -t my-app:latest .

# Build context from stdin (no local files)
docker build - <<'EOF'
FROM python:3.12-slim
RUN pip install requests
CMD ["python", "-c", "import requests; print(requests.__version__)"]
EOF

# Show BuildKit output (verbose — useful for debugging)
DOCKER_BUILDKIT=1 docker build --progress=plain -t my-app:latest .
```

---

## Push and Pull

```bash
# Tag an image for a registry
docker tag my-app:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:latest

# Push to a registry (must be authenticated)
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:latest

# Pull from a private registry
docker pull 123456789.dkr.ecr.us-east-1.amazonaws.com/my-app:latest

# Authenticate to Docker Hub
docker login

# Authenticate to AWS ECR
aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin \
    123456789.dkr.ecr.us-east-1.amazonaws.com

# Authenticate to GCP Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Authenticate to Azure Container Registry
az acr login --name myregistry
```

---

## System Cleanup

```bash
# Full system prune (removes stopped containers, unused images, networks, build cache)
docker system prune

# Also remove volumes (careful!)
docker system prune --volumes

# Show disk usage
docker system df

# Detailed disk usage
docker system df -v
```

---

## Useful One-Liners

```bash
# Stop all running containers
docker stop $(docker ps -q)

# Remove all containers
docker rm $(docker ps -aq)

# Remove all images
docker rmi $(docker images -q)

# Get the IP of a running container
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' my-app

# Follow logs with timestamps
docker logs -f --timestamps my-app

# Run a one-off command in a new container and auto-remove it
docker run --rm -v $(pwd):/work -w /work python:3.12-slim pip install -r requirements.txt

# Open a shell in a running container
docker exec -it $(docker ps -qf name=my-app) sh
```

---

## References

- [Docker documentation](https://docs.docker.com)
- [Docker CLI reference](https://docs.docker.com/engine/reference/commandline/cli/)
- [Docker Hub](https://hub.docker.com)
---

← [Previous: Containers](./README.md) | [Home](../README.md) | [Next: Dockerfile →](./dockerfile.md)
