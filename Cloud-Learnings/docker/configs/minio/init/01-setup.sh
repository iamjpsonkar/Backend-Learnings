#!/bin/bash
# MinIO initialization script
# Creates default buckets and policies

set -euo pipefail

echo "[MinIO Init] Starting MinIO configuration..."

# Wait for MinIO to be ready
until mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" 2>/dev/null; do
  echo "[MinIO Init] Waiting for MinIO..."
  sleep 2
done

echo "[MinIO Init] MinIO is ready."

# Create buckets
for bucket in lab-bucket lab-assets lab-logs lab-terraform-state lab-backups; do
  mc mb --ignore-existing "local/$bucket"
  echo "[MinIO Init]   Created bucket: $bucket"
done

# Set lab-bucket to download policy (public read)
mc anonymous set download local/lab-assets
echo "[MinIO Init]   Set lab-assets to public read."

# Upload sample files
echo "Hello from MinIO!" > /tmp/hello.txt
mc cp /tmp/hello.txt local/lab-bucket/hello.txt
echo "[MinIO Init]   Uploaded sample file."

echo "[MinIO Init] Initialization complete."
