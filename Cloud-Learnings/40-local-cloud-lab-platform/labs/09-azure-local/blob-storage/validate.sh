#!/usr/bin/env bash
# Validate lab: azurite-blob-storage
set -euo pipefail

AZURITE_CONN="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1"

echo "=== Azure Blob Storage (Azurite) Lab Validation ==="

# Check Azurite is running
if curl -sf http://localhost:10000 &>/dev/null || curl -s http://localhost:10000 2>/dev/null | head -1 | grep -q "HTTP"; then
    echo "PASS: Azurite is responding on port 10000"
elif curl -s http://localhost:10000/devstoreaccount1?comp=list 2>/dev/null | grep -qi "EnumerationResults"; then
    echo "PASS: Azurite blob service is accessible"
else
    echo "FAIL: Azurite not reachable on port 10000"
    echo "      Run: make start-azure-local"
    exit 1
fi

# Check az CLI is installed
if command -v az &>/dev/null; then
    AZ_VER=$(az --version 2>/dev/null | head -1)
    echo "PASS: Azure CLI installed — $AZ_VER"
else
    echo "WARN: az CLI not installed"
    echo "      Install: brew install azure-cli  OR  pip3 install azure-cli"
fi

# Check lab-blobs container
export AZURE_STORAGE_CONNECTION_STRING="$AZURITE_CONN"

if command -v az &>/dev/null; then
    if az storage container list 2>/dev/null | python3 -c "
import sys, json
containers = json.load(sys.stdin)
names = [c['name'] for c in containers]
print(f'Containers: {names}')
exit(0 if 'lab-blobs' in names else 1)
" 2>/dev/null; then
        echo "PASS: lab-blobs container exists"
    else
        echo "WARN: lab-blobs container not found"
        echo "      Create: az storage container create --name lab-blobs"
    fi

    # Check blobs in container
    BLOB_COUNT=$(az storage blob list --container-name lab-blobs 2>/dev/null | python3 -c "
import sys, json
blobs = json.load(sys.stdin)
print(len(blobs))
" 2>/dev/null || echo "0")

    if [ "$BLOB_COUNT" -gt 0 ]; then
        echo "PASS: lab-blobs has $BLOB_COUNT blob(s)"
    else
        echo "WARN: No blobs found in lab-blobs container"
    fi

    if [ "$BLOB_COUNT" -ge 3 ]; then
        echo "PASS: At least 3 blobs uploaded (goal: 3+)"
    else
        echo "INFO: Upload more blobs to complete the exercise (currently: $BLOB_COUNT)"
    fi
fi

echo ""
echo "=== Validation complete ==="
