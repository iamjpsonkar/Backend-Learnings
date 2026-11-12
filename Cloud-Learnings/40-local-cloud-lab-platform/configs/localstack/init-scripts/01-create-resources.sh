#!/usr/bin/env bash
# configs/localstack/init-scripts/01-create-resources.sh
# Runs automatically when LocalStack starts (placed in /etc/localstack/init/ready.d/)
# Creates default S3 buckets, SQS queues, and DynamoDB tables for labs

set -euo pipefail

echo "[LocalStack Init] Creating default lab resources..."

# ─── S3 Buckets ──────────────────────────────
echo "[LocalStack] Creating S3 buckets..."
awslocal s3 mb s3://lab-bucket
awslocal s3 mb s3://lab-uploads
awslocal s3 mb s3://lab-backups
awslocal s3 mb s3://lab-terraform-state

# Enable versioning on lab-bucket
awslocal s3api put-bucket-versioning \
    --bucket lab-bucket \
    --versioning-configuration Status=Enabled

echo "[LocalStack] S3 buckets created: lab-bucket, lab-uploads, lab-backups, lab-terraform-state"

# ─── SQS Queues ──────────────────────────────
echo "[LocalStack] Creating SQS queues..."
awslocal sqs create-queue --queue-name lab-queue
awslocal sqs create-queue --queue-name lab-dlq
awslocal sqs create-queue \
    --queue-name lab-queue.fifo \
    --attributes FifoQueue=true,ContentBasedDeduplication=true

echo "[LocalStack] SQS queues created"

# ─── SNS Topics ──────────────────────────────
echo "[LocalStack] Creating SNS topics..."
awslocal sns create-topic --name lab-topic
awslocal sns create-topic --name lab-alerts

echo "[LocalStack] SNS topics created"

# ─── DynamoDB Tables ─────────────────────────
echo "[LocalStack] Creating DynamoDB tables..."
awslocal dynamodb create-table \
    --table-name lab-items \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

awslocal dynamodb create-table \
    --table-name lab-sessions \
    --attribute-definitions \
        AttributeName=session_id,AttributeType=S \
        AttributeName=user_id,AttributeType=S \
    --key-schema \
        AttributeName=session_id,KeyType=HASH \
        AttributeName=user_id,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST

echo "[LocalStack] DynamoDB tables created"

# ─── IAM ─────────────────────────────────────
echo "[LocalStack] Creating IAM resources..."
awslocal iam create-user --user-name lab-service-account
awslocal iam create-policy \
    --policy-name lab-s3-readonly \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"], "Resource": "*"}
        ]
    }'

echo "[LocalStack] IAM resources created"

echo "[LocalStack Init] All lab resources initialized successfully!"
