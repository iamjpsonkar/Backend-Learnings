#!/bin/bash
# LocalStack initialization script
# Runs automatically on container start via /etc/localstack/init/ready.d/
# Creates default AWS resources for the labs

set -euo pipefail

echo "[LocalStack Init] Starting resource initialization..."

AWS="aws --endpoint-url=http://localhost:4566"
REGION="us-east-1"

# =============================================================================
# S3 Buckets
# =============================================================================
echo "[LocalStack Init] Creating S3 buckets..."

$AWS s3 mb s3://lab-bucket --region "$REGION" 2>/dev/null && \
  echo "[LocalStack Init]   Created: lab-bucket" || \
  echo "[LocalStack Init]   Already exists: lab-bucket"

$AWS s3 mb s3://lab-assets --region "$REGION" 2>/dev/null && \
  echo "[LocalStack Init]   Created: lab-assets" || \
  echo "[LocalStack Init]   Already exists: lab-assets"

$AWS s3 mb s3://lab-logs --region "$REGION" 2>/dev/null && \
  echo "[LocalStack Init]   Created: lab-logs" || \
  echo "[LocalStack Init]   Already exists: lab-logs"

$AWS s3 mb s3://lab-terraform-state --region "$REGION" 2>/dev/null && \
  echo "[LocalStack Init]   Created: lab-terraform-state" || \
  echo "[LocalStack Init]   Already exists: lab-terraform-state"

# Upload sample file
echo "Hello from LocalStack!" | $AWS s3 cp - s3://lab-bucket/hello.txt
echo "[LocalStack Init]   Uploaded sample file to lab-bucket/hello.txt"

# =============================================================================
# SQS Queues
# =============================================================================
echo "[LocalStack Init] Creating SQS queues..."

$AWS sqs create-queue --queue-name lab-queue --region "$REGION" \
  --attributes VisibilityTimeout=30,MessageRetentionPeriod=86400 \
  2>/dev/null && echo "[LocalStack Init]   Created: lab-queue" || true

$AWS sqs create-queue --queue-name lab-queue-dlq --region "$REGION" \
  2>/dev/null && echo "[LocalStack Init]   Created: lab-queue-dlq" || true

# =============================================================================
# SNS Topics
# =============================================================================
echo "[LocalStack Init] Creating SNS topics..."

$AWS sns create-topic --name lab-topic --region "$REGION" \
  2>/dev/null && echo "[LocalStack Init]   Created: lab-topic" || true

# =============================================================================
# DynamoDB Tables
# =============================================================================
echo "[LocalStack Init] Creating DynamoDB tables..."

$AWS dynamodb create-table \
  --table-name lab-items \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION" \
  2>/dev/null && echo "[LocalStack Init]   Created: lab-items" || true

# Insert sample item
$AWS dynamodb put-item \
  --table-name lab-items \
  --item '{"id": {"S": "item-001"}, "name": {"S": "Sample Item"}, "value": {"N": "42"}}' \
  --region "$REGION" \
  2>/dev/null || true

echo "[LocalStack Init] Initialization complete."
