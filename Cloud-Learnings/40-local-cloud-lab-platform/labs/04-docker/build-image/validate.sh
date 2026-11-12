#!/usr/bin/env bash
# Validate lab: docker-build-image
set -euo pipefail

echo "=== Docker Build Image Lab Validation ==="

# Check Docker is running
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker not running"
    exit 1
fi

# Check image exists
if docker image ls my-server:v1 2>/dev/null | grep -q my-server; then
    echo "PASS: Image my-server:v1 exists"
    SIZE=$(docker image ls my-server:v1 --format '{{.Size}}')
    echo "  Image size: $SIZE"
else
    echo "WARN: Image my-server:v1 not found — build it first with: docker build -t my-server:v1 ."
fi

# Check image has layers
if docker image ls my-server:v1 &>/dev/null; then
    LAYER_COUNT=$(docker history my-server:v1 2>/dev/null | wc -l)
    if [ "$LAYER_COUNT" -gt 2 ]; then
        echo "PASS: Image has $LAYER_COUNT layers"
    else
        echo "FAIL: Image has too few layers ($LAYER_COUNT)"
    fi

    # Check EXPOSE instruction
    if docker image inspect my-server:v1 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
exposed = d[0].get('Config', {}).get('ExposedPorts', {})
print(f'Exposed ports: {list(exposed.keys())}')
exit(0 if exposed else 1)
" 2>/dev/null; then
        echo "PASS: Image has EXPOSE instruction"
    else
        echo "WARN: No EXPOSE instruction found in image"
    fi

    # Try running the image
    docker stop grade-build-test 2>/dev/null || true
    docker rm grade-build-test 2>/dev/null || true

    docker run -d -p 8888:8000 --name grade-build-test my-server:v1 2>/dev/null
    sleep 2
    if curl -sf http://localhost:8888 >/dev/null 2>&1; then
        echo "PASS: Image runs and serves HTTP on port 8888"
    else
        echo "WARN: Could not reach http://localhost:8888 — image may serve on a different path"
    fi
    docker stop grade-build-test 2>/dev/null || true
    docker rm grade-build-test 2>/dev/null || true
fi

# Check .dockerignore exists (if in a docker-lab directory)
if [ -f ~/.dockerignore ] || [ -f ~/docker-lab/.dockerignore ]; then
    echo "PASS: .dockerignore file exists"
else
    echo "INFO: .dockerignore not found at ~/docker-lab/.dockerignore (optional for this validation)"
fi

echo ""
echo "=== Validation complete ==="
