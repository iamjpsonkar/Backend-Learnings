# Docker Basics: Run, Build, and Inspect Containers

**Difficulty**: Beginner | **Time**: 45 minutes | **Profile**: core

---

## Overview

In this lab you will learn the fundamental Docker CLI commands for working with containers and images.

---

## Prerequisites

- Docker is running (`docker info` succeeds)
- Platform core services are up (`make start-core`)

---

## Tasks

### Task 1: Pull the nginx:alpine image

```bash
docker pull nginx:alpine
docker images | grep nginx
```

### Task 2: Run a named nginx container

```bash
docker run -d --name lab-nginx -p 8090:80 nginx:alpine
docker ps
```

Verify it's serving:
```bash
curl http://localhost:8090
```

### Task 3: View container logs

```bash
docker logs lab-nginx
```

### Task 4: Run a command inside the container

```bash
docker exec lab-nginx nginx -v
docker exec -it lab-nginx sh
# inside: ls /etc/nginx/
# exit with: exit
```

### Task 5: Inspect the container

```bash
docker inspect lab-nginx
docker inspect --format='{{.NetworkSettings.IPAddress}}' lab-nginx
docker inspect --format='{{.State.Status}}' lab-nginx
```

### Task 6: Stop and remove the container

```bash
docker stop lab-nginx
docker rm lab-nginx
# Or in one command:
# docker rm -f lab-nginx
```

Verify it's gone:
```bash
docker ps -a | grep lab-nginx  # should show nothing
```

---

## Key Concepts

| Command | Description |
|---------|-------------|
| `docker pull` | Download an image from a registry |
| `docker run -d` | Start a container in detached mode |
| `docker run -p host:container` | Map a host port to a container port |
| `docker run --name` | Give a container a name |
| `docker ps` | List running containers |
| `docker ps -a` | List all containers (including stopped) |
| `docker logs` | View container stdout/stderr |
| `docker exec -it` | Start an interactive shell in a container |
| `docker inspect` | Get detailed container/image metadata |
| `docker stop` | Gracefully stop a container |
| `docker rm` | Remove a stopped container |
| `docker rm -f` | Force-stop and remove a container |

---

## Cleanup

When done:
```bash
docker stop lab-nginx 2>/dev/null; docker rm lab-nginx 2>/dev/null
```

---

## Related Topics

- Next: [Build Your First Image](../build-image/README.md)
- Docs: [Containers Overview](../../../09-containers/README.md)
- Cloud equivalent: AWS ECS, Azure ACI, GCP Cloud Run
