#!/usr/bin/env bash
# Validate lab: gcs-emulator
set -euo pipefail

echo "=== GCS Emulator (fake-gcs-server) Lab Validation ==="

# Check Docker is running
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker not running"
    exit 1
fi

# Check fake-gcs container is running
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "fake-gcs"; then
    echo "PASS: fake-gcs container is running"
else
    echo "WARN: fake-gcs container not running"
    echo "      Start: docker run -d --name fake-gcs -p 4443:4443 fsouza/fake-gcs-server:latest -scheme http -port 4443"
fi

# Check API is accessible
if curl -sf http://localhost:4443/storage/v1/b?project=test 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
exit(0 if d.get('kind') == 'storage#buckets' else 1)
" 2>/dev/null; then
    echo "PASS: GCS emulator API responds correctly"
else
    echo "FAIL: GCS emulator API not responding at http://localhost:4443"
fi

# Check lab-gcs-bucket exists
if curl -sf http://localhost:4443/storage/v1/b/lab-gcs-bucket 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
exit(0 if d.get('name') == 'lab-gcs-bucket' else 1)
" 2>/dev/null; then
    echo "PASS: lab-gcs-bucket exists"
else
    echo "WARN: lab-gcs-bucket not found"
    echo "      Create: curl -X POST 'http://localhost:4443/storage/v1/b?project=test' -H 'Content-Type: application/json' -d '{\"name\": \"lab-gcs-bucket\"}'"
fi

# Check objects in bucket
OBJECT_COUNT=$(curl -sf http://localhost:4443/storage/v1/b/lab-gcs-bucket/o 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d.get('items', []) or []
print(len(items))
" 2>/dev/null || echo "0")

if [ "$OBJECT_COUNT" -gt 0 ]; then
    echo "PASS: lab-gcs-bucket has $OBJECT_COUNT object(s)"
    if [ "$OBJECT_COUNT" -ge 2 ]; then
        echo "PASS: At least 2 objects uploaded (goal met)"
    fi
else
    echo "WARN: No objects found in lab-gcs-bucket"
fi

echo ""
echo "=== Validation complete ==="
