#!/usr/bin/env bash
# Validate lab: s3-operations
set -euo pipefail

ENDPOINT="http://localhost:4566"
BUCKET="lab-my-bucket"

export AWS_DEFAULT_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"

# Check LocalStack is running
if curl -sf "$ENDPOINT/health" | grep -q "running\|available"; then
    echo "PASS: LocalStack is running and healthy"
else
    echo "FAIL: LocalStack not reachable at $ENDPOINT — run: make start-aws-local"
    exit 0
fi

# Check S3 service is available
if curl -sf "$ENDPOINT/health" | grep -q '"s3"'; then
    echo "PASS: S3 service available in LocalStack"
else
    echo "FAIL: S3 service not available in LocalStack"
fi

# Check bucket exists
if aws --endpoint-url="$ENDPOINT" s3 ls 2>/dev/null | grep -q "$BUCKET"; then
    echo "PASS: Bucket $BUCKET exists"
else
    echo "FAIL: Bucket $BUCKET not found — create it with: aws --endpoint-url=$ENDPOINT s3 mb s3://$BUCKET"
fi

# Check versioning is enabled
VERSIONING=$(aws --endpoint-url="$ENDPOINT" s3api get-bucket-versioning \
    --bucket "$BUCKET" 2>/dev/null | grep -o '"Status": "[^"]*"' || echo "")
if echo "$VERSIONING" | grep -q "Enabled"; then
    echo "PASS: Versioning is enabled on $BUCKET"
else
    echo "FAIL: Versioning not enabled on $BUCKET"
fi

# Check objects exist in bucket
OBJECT_COUNT=$(aws --endpoint-url="$ENDPOINT" s3 ls s3://"$BUCKET" --recursive 2>/dev/null | wc -l || echo "0")
if [ "$OBJECT_COUNT" -ge 1 ]; then
    echo "PASS: Bucket has $OBJECT_COUNT object(s)"
else
    echo "FAIL: Bucket is empty — upload at least one file"
fi

# Check bucket policy
if aws --endpoint-url="$ENDPOINT" s3api get-bucket-policy --bucket "$BUCKET" &>/dev/null; then
    echo "PASS: Bucket policy is set"
else
    echo "FAIL: No bucket policy set on $BUCKET"
fi
