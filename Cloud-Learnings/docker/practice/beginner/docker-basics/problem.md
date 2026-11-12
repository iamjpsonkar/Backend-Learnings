# Problem: Docker Basics

## Goal

Build a simple containerized Python web application that responds to HTTP requests and passes health checks.

## Requirements

1. Write a Python HTTP server (using only stdlib — no frameworks) that:
   - Listens on port `8080`
   - Responds to `GET /` with `{"message": "Hello from Docker!"}`
   - Responds to `GET /health` with `{"status": "ok"}`
   - Responds to any other path with `404 Not Found`

2. Write a `Dockerfile` that:
   - Uses `python:3.12-slim` as base
   - Runs as a non-root user
   - Exposes port `8080`
   - Has a `HEALTHCHECK` instruction
   - Follows Dockerfile best practices

3. Build and run the container:
   - Build: `docker build -t my-hello-app .`
   - Run: `docker run -p 8080:8080 my-hello-app`
   - Test: `curl http://localhost:8080/health`

## Constraints

- No external Python packages
- Container must pass health check within 30 seconds
- Container must run as non-root user (UID >= 1000)
- Image size should be under 200MB

## Validation

```bash
# Start the container
docker run -d -p 8080:8080 --name my-hello-app my-hello-app

# Test health endpoint
curl http://localhost:8080/health
# Expected: {"status": "ok"}

# Test main endpoint
curl http://localhost:8080/
# Expected: {"message": "Hello from Docker!"}

# Test 404
curl -o /dev/null -s -w "%{http_code}" http://localhost:8080/notfound
# Expected: 404

# Check user
docker exec my-hello-app whoami
# Expected: NOT root

# Check health status
docker inspect --format='{{.State.Health.Status}}' my-hello-app
# Expected: healthy
```

## Cleanup

```bash
docker stop my-hello-app
docker rm my-hello-app
docker rmi my-hello-app
```

## Extension Challenge

1. Add a `/metrics` endpoint that returns request counts as Prometheus text format
2. Add an environment variable `APP_PORT` to configure the port
3. Make the `/` endpoint return the container hostname
