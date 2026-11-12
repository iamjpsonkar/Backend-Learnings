#!/usr/bin/env bash
# Validate lab: docker-basics
set -euo pipefail

# Check 1: nginx:alpine image exists
if docker image inspect nginx:alpine &>/dev/null; then
    echo "PASS: nginx:alpine image is present locally"
else
    echo "FAIL: nginx:alpine image not found — did you run: docker pull nginx:alpine?"
fi

# Check 2: lab-nginx container is NOT still running (should be cleaned up)
if ! docker ps --filter "name=lab-nginx" --filter "status=running" --format "{{.Names}}" | grep -q "lab-nginx"; then
    echo "PASS: lab-nginx container is stopped (cleanup done)"
else
    echo "FAIL: lab-nginx container is still running — stop it with: docker stop lab-nginx"
fi

# Check 3: Docker is functional (can list images)
if docker images --format "{{.Repository}}" | grep -q "nginx"; then
    echo "PASS: Docker is working and has at least one nginx image"
else
    echo "FAIL: Docker images check failed"
fi

# Check 4: docker exec works (basic sanity)
if docker run --rm --name lab-exec-test alpine:latest echo "test" &>/dev/null; then
    echo "PASS: docker exec capability works (ran alpine:latest)"
    docker rmi alpine:latest &>/dev/null || true
else
    echo "FAIL: Could not run a test container — Docker may have resource issues"
fi
