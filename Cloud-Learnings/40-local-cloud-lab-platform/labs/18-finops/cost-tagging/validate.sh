#!/usr/bin/env bash
# Validate lab: finops-cost-tagging
set -euo pipefail

echo "=== FinOps Cost Tagging Lab Validation ==="

# Check Docker is running
if docker info &>/dev/null; then
    echo "PASS: Docker is running"
else
    echo "FAIL: Docker not running"
    exit 1
fi

# Check tagged-app container exists with correct labels
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^tagged-app$"; then
    echo "PASS: tagged-app container is running"

    # Verify mandatory tags
    LABELS=$(docker inspect tagged-app 2>/dev/null | python3 -c "
import sys, json
c = json.load(sys.stdin)
labels = c[0]['Config']['Labels'] or {}
mandatory = ['environment', 'team', 'cost-center', 'project']
missing = [k for k in mandatory if k not in labels]
if missing:
    print(f'Missing mandatory labels: {missing}')
    exit(1)
else:
    print(f'All mandatory labels present: {dict((k,labels[k]) for k in mandatory)}')
    exit(0)
" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "PASS: tagged-app has all mandatory labels (environment, team, cost-center, project)"
        echo "  $LABELS"
    else
        echo "FAIL: tagged-app missing mandatory labels"
        echo "  $LABELS"
    fi
else
    echo "WARN: tagged-app container not running"
    echo "      Start: docker run -d --name tagged-app -l environment=dev -l team=platform -l cost-center=CC-1234 -l project=lab-platform nginx:alpine"
fi

# Check tagged-db container
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^tagged-db$"; then
    echo "PASS: tagged-db container is running"
else
    echo "WARN: tagged-db not running"
fi

# Check filtering by label works
FILTERED=$(docker ps --filter 'label=team' --format '{{.Names}}' 2>/dev/null | wc -l)
if [ "$FILTERED" -gt 0 ]; then
    echo "PASS: $FILTERED container(s) have the 'team' label"
fi

# Check LocalStack S3 bucket tagging
if curl -sf http://localhost:4566 &>/dev/null; then
    echo "PASS: LocalStack is accessible"

    BUCKET_TAGS=$(AWS_DEFAULT_REGION=us-east-1 AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
        aws --endpoint-url http://localhost:4566 s3api get-bucket-tagging --bucket prod-web-assets 2>/dev/null || echo "NONE")

    if echo "$BUCKET_TAGS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
tags = {t['Key']: t['Value'] for t in d.get('TagSet', [])}
if 'environment' in tags:
    print(f'Tags: {tags}')
    exit(0)
exit(1)
" 2>/dev/null; then
        echo "PASS: prod-web-assets S3 bucket has cost attribution tags"
    else
        echo "WARN: prod-web-assets bucket not found or has no tags"
    fi
else
    echo "INFO: LocalStack not running — skip S3 tag validation"
fi

# Check for compliance audit script
for script_path in ~/finops-lab/audit-tags.sh ~/finops-lab/audit.sh ./audit-tags.sh; do
    if [ -f "$script_path" ]; then
        echo "PASS: Compliance audit script found at $script_path"
        break
    fi
done

echo ""
echo "=== Validation complete ==="
