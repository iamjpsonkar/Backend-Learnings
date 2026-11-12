#!/usr/bin/env bash
# Validate lab: troubleshoot-memory-leak
set -euo pipefail

echo "=== Memory Leak Detection Lab Validation ==="

# Check Docker is running
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker not running"
    exit 1
fi

# Check leaky-app container is running
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^leaky-app$"; then
    echo "PASS: leaky-app container is running"

    # Check memory usage
    MEM_USAGE=$(docker stats leaky-app --no-stream --format '{{.MemUsage}}' 2>/dev/null)
    echo "INFO: Current memory usage: $MEM_USAGE"

    # Check service responds
    if curl -sf http://localhost:9998 2>/dev/null | grep -qi "ok\|hello\|response"; then
        echo "PASS: leaky-app responds to HTTP on port 9998"
    else
        echo "WARN: HTTP on port 9998 not responding as expected"
    fi

    # Check Python is running
    if docker exec leaky-app ps aux 2>/dev/null | grep -qi python; then
        echo "PASS: Python process running inside container"
    fi

    # Simulate 5 requests and re-check memory
    echo "INFO: Sending 5 test requests to trigger leak..."
    for _ in $(seq 5); do curl -sf http://localhost:9998 >/dev/null 2>&1 || true; done
    MEM_AFTER=$(docker stats leaky-app --no-stream --format '{{.MemUsage}}' 2>/dev/null)
    echo "INFO: Memory after 5 requests: $MEM_AFTER"
else
    echo "WARN: leaky-app container not running"
    echo "      See lab instructions to create leak_server.py and start container"
fi

# Check leak server script exists
if [ -f ~/leak_server.py ]; then
    echo "PASS: leak_server.py found at ~/leak_server.py"

    # Check it has the leaky pattern
    if grep -qi "CACHE\|append\|leak\|deque" ~/leak_server.py 2>/dev/null; then
        echo "PASS: leak_server.py contains memory management code"

        # Check if fix has been applied (deque/maxlen is the fix)
        if grep -q "deque\|maxlen\|lru_cache" ~/leak_server.py 2>/dev/null; then
            echo "PASS: Fix applied — bounded cache (deque/maxlen) detected"
        else
            echo "INFO: Fix not yet applied (deque/maxlen/lru_cache not found)"
        fi
    fi
else
    echo "WARN: ~/leak_server.py not found — create it to start the lab"
fi

# Check Prometheus is up (for memory metrics)
if curl -sf http://localhost:9090/-/ready &>/dev/null; then
    echo "PASS: Prometheus is running (can be used to track memory growth)"
else
    echo "INFO: Prometheus not running — run: make start-observability"
fi

echo ""
echo "=== Validation complete ==="
