#!/usr/bin/env bash
# Validate lab: troubleshoot-high-cpu
set -euo pipefail

echo "=== High CPU Troubleshooting Lab Validation ==="

# Check Docker is running
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker not running"
    exit 1
fi

# Check cpu-hog container exists
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^cpu-hog$"; then
    echo "PASS: cpu-hog container is running"

    # Check CPU usage
    CPU_USAGE=$(docker stats cpu-hog --no-stream --format '{{.CPUPerc}}' 2>/dev/null | tr -d '%')
    if echo "$CPU_USAGE" | grep -qE '^[0-9]'; then
        echo "PASS: cpu-hog CPU usage: ${CPU_USAGE}%"
    fi

    # Check it's running Python
    if docker exec cpu-hog sh -c 'pgrep python3 || pgrep python' 2>/dev/null | grep -qE '^[0-9]+'; then
        PID=$(docker exec cpu-hog sh -c 'pgrep python3 || pgrep python' 2>/dev/null | head -1)
        echo "PASS: Python process is running inside container (PID: $PID)"
    else
        echo "WARN: Could not find Python process inside container"
    fi

    # Check process list accessible
    if docker exec cpu-hog sh -c 'ps aux' 2>/dev/null | grep -qi python; then
        echo "PASS: Process list shows Python (ps aux works)"
    fi

    # Check resource limits set
    MEM_LIMIT=$(docker inspect cpu-hog 2>/dev/null | python3 -c "
import sys, json
c = json.load(sys.stdin)
mem = c[0]['HostConfig']['Memory']
cpu = c[0]['HostConfig']['NanoCpus']
print(f'Memory: {mem//1024//1024}MB, CPUs: {cpu/1e9:.1f}')
exit(0 if mem > 0 or cpu > 0 else 1)
" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "PASS: Container has resource limits: $MEM_LIMIT"
    else
        echo "WARN: Container has no resource limits set"
    fi
else
    echo "WARN: cpu-hog container not running"
    echo "      Start: docker run -d --name cpu-hog --cpus=0.5 --memory=128m python:3.11-alpine python3 -c 'while True: [x**2 for x in range(10000)]'"
fi

# Check post-incident report
if [ -f ~/post-incident-report.md ]; then
    echo "PASS: Post-incident report exists at ~/post-incident-report.md"
    LINE_COUNT=$(wc -l < ~/post-incident-report.md)
    echo "  Report has $LINE_COUNT lines"
else
    echo "INFO: Post-incident report not found (optional task)"
fi

echo ""
echo "=== Validation complete ==="
