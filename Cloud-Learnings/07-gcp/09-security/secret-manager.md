← [Previous: GCP Security](./README.md) | [Home](../../README.md) | [Next: Cloud KMS →](./cloud-kms.md)

---

# Secret Manager

Secret Manager stores API keys, passwords, certificates, and other sensitive data. It provides versioning, auditing, IAM-controlled access, and automatic rotation integration.

---

## Creating and Managing Secrets

```bash
PROJECT="my-app-prod-123456"

# Create a secret
gcloud secrets create db-password \
    --project=$PROJECT \
    --replication-policy=automatic \
    --labels=environment=production,service=my-app

# Add the first version (from string)
echo -n "super-secret-password-123" | \
    gcloud secrets versions add db-password \
        --project=$PROJECT \
        --data-file=-

# Add a version from a file
gcloud secrets versions add tls-cert \
    --project=$PROJECT \
    --data-file=./certs/server.crt

# List secrets
gcloud secrets list \
    --project=$PROJECT \
    --filter="labels.environment=production" \
    --format="table(name,createTime,replication.automatic)"

# Access the latest version (for debugging — avoid in production scripts)
gcloud secrets versions access latest \
    --project=$PROJECT \
    --secret=db-password

# Access a specific version
gcloud secrets versions access 2 \
    --project=$PROJECT \
    --secret=db-password

# List versions
gcloud secrets versions list db-password \
    --project=$PROJECT \
    --format="table(name,state,createTime)"

# Disable an old version (non-destructive)
gcloud secrets versions disable 1 \
    --project=$PROJECT \
    --secret=db-password

# Destroy a version (irreversible)
gcloud secrets versions destroy 1 \
    --project=$PROJECT \
    --secret=db-password

# Delete a secret and all versions
gcloud secrets delete db-password \
    --project=$PROJECT
```

---

## IAM

```bash
# Grant a service account access to a specific secret
gcloud secrets add-iam-policy-binding db-password \
    --project=$PROJECT \
    --member="serviceAccount:sa-my-app@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Grant access to ALL secrets (project-level — use sparingly)
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:sa-my-app@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Grant ability to create/update secrets
gcloud secrets add-iam-policy-binding db-password \
    --project=$PROJECT \
    --member="serviceAccount:sa-cicd@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretVersionAdder"
```

---

## Python SDK

```python
import functools
import logging
import os
from typing import Any
from google.cloud import secretmanager
from google.api_core.exceptions import NotFound

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]

_client: secretmanager.SecretManagerServiceClient | None = None


def _get_client() -> secretmanager.SecretManagerServiceClient:
    global _client
    if _client is None:
        _client = secretmanager.SecretManagerServiceClient()
        logger.info("Secret Manager client created")
    return _client


@functools.lru_cache(maxsize=None)
def get_secret(secret_id: str, version: str = "latest") -> str:
    """Retrieve a secret value. Cached per (secret_id, version) for the process lifetime.

    Use version='latest' in development. In production, pin to a specific
    version number so a secret rotation doesn't surprise a running instance.
    """
    client = _get_client()
    name = f"projects/{PROJECT}/secrets/{secret_id}/versions/{version}"

    logger.info("Fetching secret", extra={"secret_id": secret_id, "version": version})

    try:
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("utf-8")
        logger.info("Secret fetched", extra={"secret_id": secret_id, "version": version})
        return payload
    except NotFound:
        logger.error("Secret not found", extra={"secret_id": secret_id, "version": version})
        raise


def create_or_update_secret(secret_id: str, value: str) -> str:
    """Create a secret (if needed) and add a new version. Returns version name."""
    client = _get_client()
    parent = f"projects/{PROJECT}"

    # Try to create the secret; ignore if it already exists
    try:
        client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        logger.info("Secret created", extra={"secret_id": secret_id})
    except Exception:
        logger.debug("Secret already exists", extra={"secret_id": secret_id})

    secret_name = f"{parent}/secrets/{secret_id}"
    response = client.add_secret_version(
        request={
            "parent": secret_name,
            "payload": {"data": value.encode("utf-8")},
        }
    )

    logger.info(
        "Secret version added",
        extra={"secret_id": secret_id, "version_name": response.name},
    )
    return response.name


# Usage
def get_db_config() -> dict[str, str]:
    """Load database config from Secret Manager."""
    return {
        "host": os.environ["DB_HOST"],
        "port": os.environ.get("DB_PORT", "5432"),
        "name": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": get_secret("db-password"),  # Cached after first call
    }
```

---

## Automatic Rotation with Cloud Functions

```bash
# Create a rotation schedule (Pub/Sub notification)
gcloud secrets update db-password \
    --project=$PROJECT \
    --rotation-period=7776000s \
    --next-rotation-time="2024-09-01T00:00:00Z"

# Add Pub/Sub notification on rotation
gcloud secrets update db-password \
    --project=$PROJECT \
    --add-topics=projects/$PROJECT/topics/secret-rotation

# The rotation Cloud Function receives a Pub/Sub message with:
# { "name": "projects/.../secrets/db-password", "etag": "..." }
# It should: generate new value → add version → update downstream → disable old version
```

---

## References

- [Secret Manager documentation](https://cloud.google.com/secret-manager/docs)
- [Python client library](https://cloud.google.com/python/docs/reference/secretmanager/latest)
- [Rotation best practices](https://cloud.google.com/secret-manager/docs/rotation-recommendations)

---

← [Previous: GCP Security](./README.md) | [Home](../../README.md) | [Next: Cloud KMS →](./cloud-kms.md)
