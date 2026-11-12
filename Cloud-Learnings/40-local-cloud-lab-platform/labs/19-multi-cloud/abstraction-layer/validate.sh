#!/usr/bin/env bash
# Validate lab: multi-cloud-abstraction
set -euo pipefail

echo "=== Multi-Cloud Storage Abstraction Layer Validation ==="

# Check Python 3 is available
if python3 --version &>/dev/null; then
    PY_VER=$(python3 --version)
    echo "PASS: $PY_VER"
else
    echo "FAIL: python3 not found"
    exit 1
fi

# Check boto3 is installed
if python3 -c "import boto3; print(boto3.__version__)" 2>/dev/null; then
    BOTO3_VER=$(python3 -c "import boto3; print(boto3.__version__)")
    echo "PASS: boto3 $BOTO3_VER installed"
else
    echo "WARN: boto3 not installed — pip3 install boto3"
fi

# Check azure-storage-blob
if python3 -c "from azure.storage.blob import BlobServiceClient; print('ok')" 2>/dev/null | grep -q ok; then
    echo "PASS: azure-storage-blob installed"
else
    echo "WARN: azure-storage-blob not installed — pip3 install azure-storage-blob"
fi

# Check LocalStack is running
if curl -sf http://localhost:4566 &>/dev/null; then
    echo "PASS: LocalStack (S3) is accessible on port 4566"
else
    echo "WARN: LocalStack not running — run: make start-aws-local"
fi

# Check Azurite is running
if curl -s http://localhost:10000 &>/dev/null || bash -c "echo > /dev/tcp/localhost/10000" 2>/dev/null; then
    echo "PASS: Azurite (Azure Blob) is accessible on port 10000"
else
    echo "WARN: Azurite not running — run: make start-azure-local"
fi

# Check fake-gcs-server
if curl -sf http://localhost:4443/storage/v1/b?project=test 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'buckets' in d.get('kind','') else 1)" 2>/dev/null; then
    echo "PASS: fake-gcs-server (GCS) is accessible on port 4443"
else
    echo "WARN: fake-gcs-server not running — start with: docker run -d --name fake-gcs -p 4443:4443 fsouza/fake-gcs-server:latest -scheme http -port 4443"
fi

# Check abstraction layer file exists
STORAGE_PATHS=(~/multi-cloud-lab/storage.py ~/multi-cloud-lab/cloud_storage.py ./storage.py ./cloud_storage.py)
for path in "${STORAGE_PATHS[@]}"; do
    if [ -f "$path" ]; then
        echo "PASS: Storage abstraction file found at $path"

        # Check for ABC pattern
        if grep -q "ABC\|abstractmethod\|class.*Storage" "$path" 2>/dev/null; then
            echo "PASS: File uses abstract class pattern"
        fi

        # Check for implementations
        for provider in S3 Azure GCS; do
            if grep -qi "$provider" "$path" 2>/dev/null; then
                echo "PASS: $provider implementation found"
            fi
        done
        break
    fi
done

# Check for test file
TEST_PATHS=(~/multi-cloud-lab/test_storage.py ./test_storage.py ~/multi-cloud-lab/tests.py)
for path in "${TEST_PATHS[@]}"; do
    if [ -f "$path" ]; then
        echo "PASS: Test file found at $path"
        TEST_COUNT=$(grep -c "def test_" "$path" 2>/dev/null || echo "0")
        echo "  Contains $TEST_COUNT test function(s)"
        break
    fi
done

echo ""
echo "=== Validation complete ==="
