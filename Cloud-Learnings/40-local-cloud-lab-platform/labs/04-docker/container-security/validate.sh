#!/usr/bin/env bash
# Validate lab: docker-container-security
set -euo pipefail

echo "=== Container Security Lab Validation ==="

# Check Docker is running
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker not running"
    exit 1
fi

# Check Trivy is installed
if command -v trivy &>/dev/null; then
    TRIVY_VER=$(trivy --version 2>/dev/null | head -1)
    echo "PASS: Trivy installed — $TRIVY_VER"
else
    echo "WARN: Trivy not installed — install with: brew install aquasecurity/trivy/trivy"
    echo "      OR: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh"
fi

# Check non-root user container run
NON_ROOT_UID=$(docker run --rm --user 1000:1000 alpine:3.19 id 2>/dev/null | grep -oE 'uid=[0-9]+' | head -1)
if echo "$NON_ROOT_UID" | grep -q "uid=1000"; then
    echo "PASS: Container runs as non-root user (uid=1000)"
else
    echo "INFO: Test non-root with: docker run --rm --user 1000:1000 alpine:3.19 id"
fi

# Check read-only filesystem with tmpfs
if docker run --rm --read-only --tmpfs /tmp alpine:3.19 sh -c 'echo ok > /tmp/t && cat /tmp/t' 2>/dev/null | grep -q ok; then
    echo "PASS: Read-only filesystem with tmpfs /tmp works"
else
    echo "FAIL: Read-only + tmpfs test failed"
fi

# Check capability dropping
if docker run --rm --cap-drop=ALL alpine:3.19 echo "caps-dropped" 2>/dev/null | grep -q "caps-dropped"; then
    echo "PASS: Container runs with all capabilities dropped"
else
    echo "WARN: Capability drop test encountered issues"
fi

# Check resource limits (if 'limited' container exists)
if docker inspect limited 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
mem = d[0]['HostConfig']['Memory']
cpus = d[0]['HostConfig']['NanoCpus']
print(f'Memory limit: {mem // 1024 // 1024}MB, CPU: {cpus / 1e9} cores')
exit(0 if mem > 0 or cpus > 0 else 1)
" 2>/dev/null; then
    echo "PASS: 'limited' container has resource limits set"
else
    echo "INFO: Run 'docker run -d --name limited --cpus=0.5 --memory=128m nginx:alpine' to test resource limits"
fi

echo ""
echo "=== Validation complete ==="
