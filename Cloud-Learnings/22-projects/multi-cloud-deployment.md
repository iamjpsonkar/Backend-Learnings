← [Previous: DR Setup](./dr-setup.md) | [Home](../README.md) | [Next: Troubleshooting →](../23-troubleshooting/README.md)

---

# Project: Multi-Cloud Deployment

Deploy an application that runs compute on AWS (ECS Fargate) while streaming analytics data to GCP BigQuery. Both clouds are provisioned with a single Terraform run using OIDC authentication — no long-lived credentials anywhere.

**Estimated cost:** ~$60–100/month (ECS + RDS + BigQuery storage)
**Time to complete:** 4–5 hours

---

## Architecture

```
Users
  │
  ▼
AWS (us-east-1) — Application layer
  ├── API Gateway → ECS Fargate (order-api)
  ├── RDS PostgreSQL (operational data)
  └── Kinesis → Lambda → S3 (event stream)
        │
        │ S3 → GCS sync (DataSync or Lambda)
        ▼
GCP (us-central1) — Analytics layer
  ├── Cloud Storage (raw events)
  ├── BigQuery (analytics warehouse)
  └── Looker Studio / Grafana (dashboards)
```

---

## Step 1: Set Up OIDC for Both Clouds

### AWS OIDC for GitHub Actions

```bash
# Create OIDC provider (if not exists)
aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# Create deploy role
cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Federated": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):oidc-provider/token.actions.githubusercontent.com"
        },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
            "StringEquals": {
                "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
            },
            "StringLike": {
                "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:*"
            }
        }
    }]
}
EOF

aws iam create-role \
    --role-name github-actions-multicloud \
    --assume-role-policy-document file://trust-policy.json
```

### GCP Workload Identity for GitHub Actions

```bash
PROJECT_ID=$(gcloud config get-value project)

# Create Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
    --location global \
    --display-name "GitHub Actions"

# Create provider
gcloud iam workload-identity-pools providers create-oidc \
    github-provider \
    --location global \
    --workload-identity-pool github-pool \
    --issuer-uri "https://token.actions.githubusercontent.com" \
    --allowed-audiences "https://token.actions.githubusercontent.com" \
    --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository"

# Create service account for Terraform
gcloud iam service-accounts create terraform-sa \
    --display-name "Terraform service account"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member serviceAccount:terraform-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --role roles/owner  # Use more granular roles in production

# Allow GitHub Actions to impersonate the SA
POOL_NAME=$(gcloud iam workload-identity-pools describe github-pool \
    --location global --format 'value(name)')

gcloud iam service-accounts add-iam-policy-binding \
    terraform-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/myorg/myrepo"

echo "Workload Identity Provider: $(gcloud iam workload-identity-pools providers describe github-provider --location global --workload-identity-pool github-pool --format 'value(name)')"
```

---

## Step 2: Terraform Multi-Provider Configuration

```hcl
# terraform/versions.tf
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws    = { source = "hashicorp/aws",    version = "~> 5.0" }
    google = { source = "hashicorp/google", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.0" }
  }
  backend "s3" {
    bucket         = "myapp-terraform-state"
    key            = "multi-cloud/prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags { tags = { project = var.app, managed_by = "terraform" } }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}
```

```hcl
# terraform/aws.tf — AWS application layer

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.app}-cluster"
  setting { name = "containerInsights"; value = "enabled" }
}

# Kinesis stream for events
resource "aws_kinesis_stream" "events" {
  name             = "${var.app}-events"
  shard_count      = 2
  retention_period = 48
  encryption_type  = "KMS"
  kms_key_id       = "alias/aws/kinesis"
}

# Lambda to forward events to GCS (via S3 → DataSync)
resource "aws_lambda_function" "event_forwarder" {
  function_name = "${var.app}-event-forwarder"
  runtime       = "python3.12"
  handler       = "forwarder.handler"
  filename      = data.archive_file.forwarder.output_path
  role          = aws_iam_role.event_forwarder.arn

  environment {
    variables = {
      GCS_BUCKET   = google_storage_bucket.events.name
      KINESIS_NAME = aws_kinesis_stream.events.name
    }
  }
}

# Kinesis → Lambda trigger
resource "aws_lambda_event_source_mapping" "kinesis_to_lambda" {
  event_source_arn  = aws_kinesis_stream.events.arn
  function_name     = aws_lambda_function.event_forwarder.arn
  starting_position = "LATEST"
  batch_size        = 100
  bisect_batch_on_function_error = true
}
```

```hcl
# terraform/gcp.tf — GCP analytics layer

# Cloud Storage bucket for raw events
resource "google_storage_bucket" "events" {
  name          = "${var.app}-events-${var.gcp_project_id}"
  location      = "US"
  force_destroy = false

  lifecycle_rule {
    action { type = "SetStorageClass"; storage_class = "NEARLINE" }
    condition { age = 30 }
  }

  labels = { project = var.app, managed_by = "terraform" }
}

# BigQuery dataset
resource "google_bigquery_dataset" "analytics" {
  dataset_id  = "${replace(var.app, "-", "_")}_analytics"
  location    = "US"
  description = "Analytics data from ${var.app}"

  labels = { project = var.app, managed_by = "terraform" }
}

# Events table (partitioned + clustered for cost efficiency)
resource "google_bigquery_table" "events" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "events"
  deletion_protection = true

  time_partitioning {
    type  = "DAY"
    field = "event_timestamp"
    expiration_ms = 94608000000  # 3 years
  }

  clustering = ["event_type", "user_id"]

  schema = jsonencode([
    { name = "event_id",        type = "STRING",    mode = "REQUIRED" },
    { name = "event_type",      type = "STRING",    mode = "REQUIRED" },
    { name = "user_id",         type = "STRING",    mode = "NULLABLE" },
    { name = "event_timestamp", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "properties",      type = "JSON",      mode = "NULLABLE" },
    { name = "aws_region",      type = "STRING",    mode = "NULLABLE" },
    { name = "ingested_at",     type = "TIMESTAMP", mode = "REQUIRED" },
  ])

  labels = { project = var.app }
}

# GCP Workload Identity for AWS Lambda to write to GCS
resource "google_iam_workload_identity_pool" "aws" {
  workload_identity_pool_id = "aws-prod-pool"
  display_name              = "AWS Production"
}

resource "google_iam_workload_identity_pool_provider" "aws" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.aws.workload_identity_pool_id
  workload_identity_pool_provider_id = "aws-provider"

  aws { account_id = var.aws_account_id }

  attribute_mapping = {
    "google.subject" = "assertion.arn"
    "attribute.aws_role" = "assertion.arn.extract('assumed-role/{role}/')"
  }
}

resource "google_service_account" "aws_forwarder" {
  account_id   = "aws-event-forwarder"
  display_name = "AWS Event Forwarder"
}

resource "google_storage_bucket_iam_member" "aws_forwarder_gcs" {
  bucket = google_storage_bucket.events.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.aws_forwarder.email}"
}

resource "google_service_account_iam_member" "aws_lambda_identity" {
  service_account_id = google_service_account.aws_forwarder.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.aws.name}/attribute.aws_role/event-forwarder-role"
}
```

---

## Step 3: Lambda Event Forwarder

```python
# src/forwarder/forwarder.py
"""
Lambda function: consume from Kinesis and write to GCS.
Uses Workload Identity Federation — no GCP service account keys.
"""
import base64
import io
import json
import logging
import os
from datetime import datetime, timezone

import boto3
import google.auth
from google.cloud import storage as gcs

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

GCS_BUCKET = os.environ["GCS_BUCKET"]


def _get_gcs_client() -> gcs.Client:
    """Get GCS client using Workload Identity Federation from Lambda execution role."""
    # The GOOGLE_APPLICATION_CREDENTIALS env var should point to the
    # credential config JSON downloaded from the Workload Identity Pool
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return gcs.Client(credentials=credentials)


def handler(event: dict, context) -> dict:
    request_id = context.aws_request_id
    records = event.get("Records", [])

    logger.info("Processing Kinesis batch", extra={
        "request_id": request_id,
        "record_count": len(records),
    })

    events = []
    for record in records:
        try:
            payload = base64.b64decode(record["kinesis"]["data"]).decode()
            data = json.loads(payload)
            data["ingested_at"] = datetime.now(timezone.utc).isoformat()
            data["aws_region"] = os.environ.get("AWS_REGION", "us-east-1")
            events.append(json.dumps(data))
        except Exception as exc:
            logger.error("Failed to decode record", extra={
                "request_id": request_id, "error": str(exc),
            })

    if events:
        _write_to_gcs(events, request_id)

    return {"batchItemFailures": []}


def _write_to_gcs(events: list[str], request_id: str) -> None:
    """Write events as newline-delimited JSON to GCS."""
    now = datetime.now(timezone.utc)
    blob_name = (
        f"events/year={now.year}/month={now.month:02d}/"
        f"day={now.day:02d}/hour={now.hour:02d}/{request_id}.ndjson"
    )

    client = _get_gcs_client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_name)
    blob.upload_from_string("\n".join(events) + "\n", content_type="application/x-ndjson")

    logger.info("Events written to GCS", extra={
        "request_id": request_id,
        "blob_name": blob_name,
        "event_count": len(events),
    })
```

---

## Step 4: BigQuery Ingestion from GCS

```bash
# Create BigQuery transfer from GCS to events table
bq mk --transfer_config \
    --project_id=$GCP_PROJECT_ID \
    --target_dataset=${APP//-/_}_analytics \
    --display_name="GCS events ingestion" \
    --data_source=google_cloud_storage \
    --params='{
        "data_path_template": "gs://'"$APP"'-events-*/events/year={run_time|\"%Y\"}/month={run_time|\"%m\"}/day={run_time|\"%d\"}/hour={run_time|\"%H\"}/*.ndjson",
        "destination_table_name_template": "events",
        "file_format": "JSON",
        "write_disposition": "APPEND"
    }' \
    --schedule="every 60 minutes"

# Or use a Dataflow job for real-time ingestion (see data-pipeline.md)
```

---

## Step 5: Deploy

```bash
# GitHub Actions handles multi-cloud deploy via OIDC
# No credentials stored — both AWS and GCP auth via OIDC

cat > .github/workflows/deploy-multicloud.yml << 'EOF'
name: Multi-Cloud Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/github-actions-multicloud
          aws-region: us-east-1

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.GCP_WIF_PROVIDER }}
          service_account: terraform-sa@${{ vars.GCP_PROJECT_ID }}.iam.gserviceaccount.com

      - uses: hashicorp/setup-terraform@v3

      - name: Terraform apply
        run: |
          cd terraform
          terraform init
          terraform apply -auto-approve \
            -var="aws_account_id=${{ vars.AWS_ACCOUNT_ID }}" \
            -var="gcp_project_id=${{ vars.GCP_PROJECT_ID }}"
EOF
```

---

## Verification

```bash
# AWS: check Kinesis → Lambda pipeline
aws kinesis put-record \
    --stream-name "${APP}-events" \
    --partition-key "test-key" \
    --data '{"event_id":"test-001","event_type":"test","user_id":"u1","timestamp":"2024-01-15T10:00:00Z"}' \
    --region us-east-1

# Wait 1 min, then query BigQuery
bq query --use_legacy_sql=false \
    "SELECT event_id, event_type, ingested_at
     FROM ${APP//-/_}_analytics.events
     ORDER BY ingested_at DESC
     LIMIT 5"

# Check GCS objects
gsutil ls -l "gs://${APP}-events-${GCP_PROJECT_ID}/events/**/*.ndjson" | tail -10
```

---

## Teardown

```bash
# Destroy all infrastructure in both clouds
cd terraform
terraform destroy \
    -var="aws_account_id=$AWS_ACCOUNT_ID" \
    -var="gcp_project_id=$GCP_PROJECT_ID"
```

---

← [Previous: DR Setup](./dr-setup.md) | [Home](../README.md) | [Next: Troubleshooting →](../23-troubleshooting/README.md)
