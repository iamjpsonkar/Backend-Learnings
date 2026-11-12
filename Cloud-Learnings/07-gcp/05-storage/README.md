← [Previous: Managed Instance Groups](../04-compute/managed-instance-groups.md) | [Home](../../README.md) | [Next: Cloud Storage →](./cloud-storage.md)

---

# GCP Storage

---

## Service Overview

| Service | AWS Equivalent | Use Case |
|---------|----------------|---------|
| **Cloud Storage** | S3 | Object storage — any file at any scale |
| **Persistent Disk** | EBS | Block storage for Compute Engine VMs |
| **Filestore** | EFS / FSx | Managed NFS file shares |
| **Cloud Storage FUSE** | S3 FUSE | Mount Cloud Storage as a filesystem |

---

## Cloud Storage

Cloud Storage is globally accessible object storage. Buckets are project-scoped; objects are stored in buckets.

### Bucket Creation

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"
BUCKET_NAME="${PROJECT_ID}-assets"  # must be globally unique

# Create a bucket (regional — recommended for most use cases)
gcloud storage buckets create gs://$BUCKET_NAME \
    --project=$PROJECT_ID \
    --location=$REGION \
    --uniform-bucket-level-access \
    --no-public-access-prevention=false \
    --default-storage-class=STANDARD

# Multi-regional bucket (higher availability + cost)
gcloud storage buckets create gs://${PROJECT_ID}-backups \
    --project=$PROJECT_ID \
    --location=US \
    --default-storage-class=NEARLINE \
    --uniform-bucket-level-access

# Describe a bucket
gcloud storage buckets describe gs://$BUCKET_NAME

# Enable versioning
gcloud storage buckets update gs://$BUCKET_NAME \
    --versioning
```

### Storage Classes

| Class | AWS Equivalent | Min Duration | Use Case |
|-------|---------------|-------------|---------|
| **STANDARD** | S3 Standard | None | Frequently accessed — default |
| **NEARLINE** | S3-IA | 30 days | Accessed < once/month |
| **COLDLINE** | S3 Glacier Instant | 90 days | Accessed < once/quarter |
| **ARCHIVE** | S3 Glacier Deep Archive | 365 days | Long-term backup, rarely accessed |

### Object Operations

```bash
# Upload a file
gcloud storage cp ./report.pdf gs://$BUCKET_NAME/reports/2024/report.pdf

# Upload with content type and cache headers
gcloud storage cp ./report.pdf gs://$BUCKET_NAME/reports/2024/report.pdf \
    --content-type="application/pdf" \
    --cache-control="private, max-age=3600"

# Upload a directory recursively
gcloud storage cp -r ./dist gs://$BUCKET_NAME/static/ \
    --cache-control="public, max-age=31536000"

# Download
gcloud storage cp gs://$BUCKET_NAME/reports/2024/report.pdf /tmp/report.pdf

# List objects
gcloud storage ls gs://$BUCKET_NAME/reports/ --long

# Delete an object
gcloud storage rm gs://$BUCKET_NAME/reports/2024/report.pdf

# Move / rename
gcloud storage mv gs://$BUCKET_NAME/old-path/file.pdf gs://$BUCKET_NAME/new-path/file.pdf

# Sync a local directory (like aws s3 sync)
gcloud storage rsync -r ./dist gs://$BUCKET_NAME/static/ --delete-unmatched-destination-objects
```

### Lifecycle Rules

```bash
gcloud storage buckets update gs://$BUCKET_NAME \
    --lifecycle-file=lifecycle.json
```

```json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["data/"],
          "matchesStorageClass": ["STANDARD"]
        }
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["data/"],
          "matchesStorageClass": ["NEARLINE"]
        }
      },
      {
        "action": {"type": "Delete"},
        "condition": {"age": 365}
      },
      {
        "action": {"type": "Delete"},
        "condition": {"isLive": false, "numNewerVersions": 3}
      }
    ]
  }
}
```

### IAM and Access Control

```bash
# Grant a service account read access (uniform bucket-level access)
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
    --member="serviceAccount:api-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

# Grant a service account write access
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME \
    --member="serviceAccount:api-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"

# Make a specific object publicly readable (only if uniform access is OFF)
gcloud storage objects update gs://$BUCKET_NAME/static/logo.png \
    --predefined-acl=publicRead

# Generate a signed URL (time-limited access, no public ACL needed)
gcloud storage sign-url gs://$BUCKET_NAME/reports/2024/report.pdf \
    --duration=1h \
    --private-key-file=key.json \
    --service-account=$SA_EMAIL
```

### Python SDK

```python
import logging
import os
from datetime import datetime, timedelta, timezone
from google.cloud import storage
from google.auth import default as google_auth_default

logger = logging.getLogger(__name__)

# Uses Application Default Credentials (managed identity in GCP, GOOGLE_APPLICATION_CREDENTIALS locally)
_storage_client = storage.Client()
_bucket_name = os.environ["GCS_BUCKET_NAME"]


def upload_file(blob_name: str, file_path: str, content_type: str = "application/octet-stream") -> str:
    """Upload a file to Cloud Storage and return the gs:// URI."""
    logger.info("Uploading file: bucket=%s blob=%s path=%s", _bucket_name, blob_name, file_path)
    bucket = _storage_client.bucket(_bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path, content_type=content_type)
    uri = f"gs://{_bucket_name}/{blob_name}"
    logger.info("Upload complete: uri=%s size=%d", uri, blob.size)
    return uri


def generate_signed_url(blob_name: str, expiry_minutes: int = 60) -> str:
    """Generate a time-limited signed URL for downloading an object."""
    logger.info("Generating signed URL: bucket=%s blob=%s expiry_minutes=%d", _bucket_name, blob_name, expiry_minutes)
    bucket = _storage_client.bucket(_bucket_name)
    blob = bucket.blob(blob_name)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    url = blob.generate_signed_url(
        expiration=expiry,
        method="GET",
        version="v4",
    )
    logger.info("Signed URL generated: blob=%s expiry=%s", blob_name, expiry.isoformat())
    return url


def download_as_bytes(blob_name: str) -> bytes:
    """Download a blob and return its contents as bytes."""
    logger.info("Downloading blob: bucket=%s blob=%s", _bucket_name, blob_name)
    bucket = _storage_client.bucket(_bucket_name)
    blob = bucket.blob(blob_name)
    data = blob.download_as_bytes()
    logger.debug("Download complete: blob=%s size=%d", blob_name, len(data))
    return data
```

---

## Filestore

```bash
# Create a Filestore NFS instance (Basic HDD — dev/test)
gcloud filestore instances create fs-my-app-prod \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --tier=BASIC_HDD \
    --file-share=name=data,capacity=1TB \
    --network=name=vpc-my-app-prod,reserved-ip-range=10.0.100.0/29

# Get the instance IP
FS_IP=$(gcloud filestore instances describe fs-my-app-prod \
    --project=$PROJECT_ID \
    --zone=$ZONE \
    --format="value(networks[0].ipAddresses[0])")

# Mount on a Linux VM
sudo apt-get install -y nfs-common
sudo mkdir -p /mnt/my-app-data
sudo mount -t nfs -o vers=3 ${FS_IP}:/data /mnt/my-app-data

# Persistent mount via /etc/fstab
echo "${FS_IP}:/data /mnt/my-app-data nfs defaults,hard,intr 0 0" | sudo tee -a /etc/fstab
```

---

## References

- [Cloud Storage documentation](https://cloud.google.com/storage/docs)
- [Cloud Storage Python client](https://googleapis.dev/python/storage/latest/)
- [Filestore documentation](https://cloud.google.com/filestore/docs)
- [Signed URLs](https://cloud.google.com/storage/docs/access-control/signed-urls)
---

← [Previous: Managed Instance Groups](../04-compute/managed-instance-groups.md) | [Home](../../README.md) | [Next: Cloud Storage →](./cloud-storage.md)
