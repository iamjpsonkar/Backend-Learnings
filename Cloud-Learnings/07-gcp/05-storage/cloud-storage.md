← [Previous: GCP Storage](./README.md) | [Home](../../README.md) | [Next: Filestore →](./filestore.md)

---

# Cloud Storage

Cloud Storage is GCP's object storage service. Buckets are globally unique, regionally/multi-regionally located, and support multiple storage classes for cost optimization.

---

## Storage Classes

| Class | SLA | Min Storage Duration | Use Case |
|-------|-----|---------------------|----------|
| **Standard** | 99.99% (multi-region) | None | Frequently accessed data |
| **Nearline** | 99.9% | 30 days | Monthly backups |
| **Coldline** | 99.9% | 90 days | Quarterly backups |
| **Archive** | 99.9% | 365 days | Long-term archives |

**Autoclass** (recommended): GCP automatically moves objects between classes based on access patterns.

---

## Creating Buckets

```bash
PROJECT="my-app-prod-123456"

# Create a regional bucket with uniform bucket-level access (recommended)
gcloud storage buckets create gs://my-app-prod-data \
    --project=$PROJECT \
    --location=us-central1 \
    --default-storage-class=standard \
    --uniform-bucket-level-access \
    --public-access-prevention=enforced \
    --labels=environment=production,team=platform

# Create a multi-region bucket for global static assets
gcloud storage buckets create gs://my-app-prod-assets \
    --project=$PROJECT \
    --location=US \
    --default-storage-class=standard \
    --uniform-bucket-level-access

# Create a bucket with Autoclass
gcloud storage buckets create gs://my-app-prod-backups \
    --project=$PROJECT \
    --location=us-central1 \
    --enable-autoclass \
    --uniform-bucket-level-access

# List buckets
gcloud storage buckets list --project=$PROJECT \
    --format="table(name,location,storageClass,publicAccessPrevention)"
```

---

## Object Operations

```bash
# Upload a file
gcloud storage cp local-file.txt gs://my-app-prod-data/path/

# Upload multiple files (parallel composite upload for large files)
gcloud storage cp --recursive ./dist gs://my-app-prod-assets/
gcloud storage rsync --recursive ./dist gs://my-app-prod-assets/ \
    --delete-unmatched-destination-objects

# Download a file
gcloud storage cp gs://my-app-prod-data/path/file.txt ./

# Copy between buckets
gcloud storage cp gs://source-bucket/file.txt gs://dest-bucket/

# Move/rename an object
gcloud storage mv gs://my-app-prod-data/old-name.txt gs://my-app-prod-data/new-name.txt

# Delete an object
gcloud storage rm gs://my-app-prod-data/file.txt

# Delete all objects with a prefix
gcloud storage rm "gs://my-app-prod-data/logs/**"

# List objects
gcloud storage ls gs://my-app-prod-data/
gcloud storage ls --long "gs://my-app-prod-data/logs/"

# Get object metadata
gcloud storage stat gs://my-app-prod-data/path/file.txt
```

---

## IAM — Access Control

Uniform bucket-level access (recommended) means all objects inherit bucket IAM.

```bash
BUCKET="gs://my-app-prod-data"

# Grant a service account read access
gcloud storage buckets add-iam-policy-binding $BUCKET \
    --member="serviceAccount:sa-my-app@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

# Grant write access (upload + delete)
gcloud storage buckets add-iam-policy-binding $BUCKET \
    --member="serviceAccount:sa-cicd@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Grant public read access (for static websites/CDN — use with caution)
gcloud storage buckets add-iam-policy-binding $BUCKET \
    --member="allUsers" \
    --role="roles/storage.objectViewer"

# View IAM policy
gcloud storage buckets get-iam-policy $BUCKET

# Grant object-level access (for buckets NOT using uniform bucket-level access)
gcloud storage objects add-iam-policy-binding gs://my-bucket/specific-file.txt \
    --member="user:alice@example.com" \
    --role="roles/storage.objectViewer"
```

---

## Lifecycle Management

```bash
# Set lifecycle policy via JSON file
cat <<EOF > lifecycle.json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 30, "matchesPrefix": ["logs/"]}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 365,
          "isLive": true
        }
      },
      {
        "action": {"type": "Delete"},
        "condition": {
          "numNewerVersions": 3,
          "isLive": false
        }
      }
    ]
  }
}
EOF

gcloud storage buckets update gs://my-app-prod-data \
    --lifecycle-file=lifecycle.json

# Enable versioning (required for noncurrent version rules)
gcloud storage buckets update gs://my-app-prod-data \
    --versioning
```

---

## Signed URLs

Signed URLs grant temporary access to private objects without modifying bucket IAM.

```python
import datetime
import logging
from google.cloud import storage
from google.oauth2 import service_account
from google.auth.transport import requests as google_requests
import google.auth

logger = logging.getLogger(__name__)


def generate_signed_url(
    bucket_name: str,
    blob_name: str,
    expiration_minutes: int = 60,
    method: str = "GET",
) -> str:
    """Generate a signed URL for temporary object access."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    expiration = datetime.timedelta(minutes=expiration_minutes)
    logger.info(
        "Generating signed URL",
        extra={"bucket": bucket_name, "blob": blob_name, "expiration_minutes": expiration_minutes, "method": method},
    )

    url = blob.generate_signed_url(
        version="v4",
        expiration=expiration,
        method=method,
        # For service accounts using ADC (Workload Identity):
        # service_account_email and access_token required if not using key file
    )

    logger.info("Signed URL generated", extra={"bucket": bucket_name, "blob": blob_name})
    return url


def upload_object(bucket_name: str, source_path: str, destination_blob: str) -> str:
    """Upload a file to Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)

    logger.info("Uploading object", extra={"bucket": bucket_name, "destination": destination_blob})
    blob.upload_from_filename(source_path)
    logger.info("Upload complete", extra={"bucket": bucket_name, "destination": destination_blob, "size": blob.size})
    return f"gs://{bucket_name}/{destination_blob}"


def download_object(bucket_name: str, blob_name: str, destination_path: str) -> None:
    """Download an object from Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    logger.info("Downloading object", extra={"bucket": bucket_name, "blob": blob_name})
    blob.download_to_filename(destination_path)
    logger.info("Download complete", extra={"bucket": bucket_name, "blob": blob_name, "dest": destination_path})
```

---

## Object Retention and WORM

```bash
# Set a default retention policy (WORM — write once read many)
gcloud storage buckets update gs://my-app-prod-audit-logs \
    --retention-period=7y  # Objects cannot be deleted for 7 years

# Lock the retention policy (makes it permanent — use with caution)
gcloud storage buckets update gs://my-app-prod-audit-logs \
    --lock-retention-policy

# Set individual object retention (override bucket retention)
gcloud storage objects update gs://my-app-prod-audit-logs/2024/logs.gz \
    --retain-until=2035-01-01T00:00:00Z \
    --override-unlocked-retention
```

---

## Cross-Region Replication

```bash
# Create a turbo replication bucket (sub-15 min RPO to secondary)
gcloud storage buckets create gs://my-app-prod-critical-data \
    --location=us-central1 \
    --rpo=ASYNC_TURBO  # Enable turbo replication

# Point-in-time recovery (soft delete for 30–90 days)
gcloud storage buckets update gs://my-app-prod-data \
    --soft-delete-duration=30d
```

---

## References

- [Cloud Storage documentation](https://cloud.google.com/storage/docs)
- [Storage classes](https://cloud.google.com/storage/docs/storage-classes)
- [IAM for Cloud Storage](https://cloud.google.com/storage/docs/access-control/iam)
- [Signed URLs](https://cloud.google.com/storage/docs/access-control/signed-urls)
- [Python client library](https://cloud.google.com/python/docs/reference/storage/latest)

---

← [Previous: GCP Storage](./README.md) | [Home](../../README.md) | [Next: Filestore →](./filestore.md)
