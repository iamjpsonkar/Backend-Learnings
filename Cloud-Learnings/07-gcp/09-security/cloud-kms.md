← [Previous: Secret Manager](./secret-manager.md) | [Home](../../README.md) | [Next: Cloud Armor →](./cloud-armor.md)

---

# Cloud KMS

Cloud KMS manages cryptographic keys for encrypting data. It supports AES-256, RSA, and Elliptic Curve keys. CMEK (Customer-Managed Encryption Keys) lets you control encryption keys for GCP services.

---

## Key Hierarchy

```
Project
└── Key Ring (regional)
    └── CryptoKey
        └── CryptoKeyVersion (actual key material — never leaves KMS)
```

---

## Creating Key Rings and Keys

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
KEY_RING="my-app-prod"

# Create a key ring (regional — must match the data it protects)
gcloud kms keyrings create $KEY_RING \
    --project=$PROJECT \
    --location=$REGION

# Create a symmetric encryption key (AES-256-GCM)
gcloud kms keys create app-data-key \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --purpose=encryption \
    --rotation-period=7776000s \
    --next-rotation-time="2024-09-01T00:00:00Z" \
    --labels=environment=production,service=my-app

# Create an asymmetric signing key (RSA-PSS-SHA-256)
gcloud kms keys create signing-key \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --purpose=asymmetric-signing \
    --default-algorithm=rsa-sign-pss-4096-sha512

# List keys
gcloud kms keys list \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --format="table(name,purpose,primary.state,rotationPeriod)"

# Get key resource name (for CMEK config)
gcloud kms keys describe app-data-key \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --format="value(name)"
# projects/my-app-prod-123456/locations/us-central1/keyRings/my-app-prod/cryptoKeys/app-data-key
```

---

## Encrypt and Decrypt

```bash
KEY_RESOURCE="projects/$PROJECT/locations/$REGION/keyRings/$KEY_RING/cryptoKeys/app-data-key"

# Encrypt a file
gcloud kms encrypt \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --key=app-data-key \
    --plaintext-file=./config.json \
    --ciphertext-file=./config.json.enc

# Decrypt
gcloud kms decrypt \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --key=app-data-key \
    --ciphertext-file=./config.json.enc \
    --plaintext-file=./config.json.dec
```

---

## Python SDK

```python
import base64
import logging
import os
from google.cloud import kms

logger = logging.getLogger(__name__)

PROJECT = os.environ["GCP_PROJECT"]
LOCATION = os.environ.get("KMS_LOCATION", "us-central1")
KEY_RING = os.environ["KMS_KEY_RING"]
KEY_NAME = os.environ["KMS_KEY_NAME"]

_client: kms.KeyManagementServiceClient | None = None


def _get_client() -> kms.KeyManagementServiceClient:
    global _client
    if _client is None:
        _client = kms.KeyManagementServiceClient()
        logger.info("KMS client created")
    return _client


def _key_name() -> str:
    client = _get_client()
    return client.crypto_key_path(PROJECT, LOCATION, KEY_RING, KEY_NAME)


def encrypt(plaintext: str) -> str:
    """Encrypt plaintext using Cloud KMS. Returns base64-encoded ciphertext."""
    client = _get_client()
    key_name = _key_name()

    logger.info("Encrypting data", extra={"key_ring": KEY_RING, "key_name": KEY_NAME})

    response = client.encrypt(
        request={
            "name": key_name,
            "plaintext": plaintext.encode("utf-8"),
        }
    )

    ciphertext = base64.b64encode(response.ciphertext).decode("utf-8")
    logger.info(
        "Data encrypted",
        extra={
            "key_ring": KEY_RING,
            "key_name": KEY_NAME,
            "ciphertext_version": response.name,
        },
    )
    return ciphertext


def decrypt(ciphertext_b64: str) -> str:
    """Decrypt a base64-encoded ciphertext using Cloud KMS."""
    client = _get_client()
    key_name = _key_name()

    logger.info("Decrypting data", extra={"key_ring": KEY_RING, "key_name": KEY_NAME})

    ciphertext = base64.b64decode(ciphertext_b64)
    response = client.decrypt(
        request={
            "name": key_name,
            "ciphertext": ciphertext,
        }
    )

    plaintext = response.plaintext.decode("utf-8")
    logger.info("Data decrypted", extra={"key_ring": KEY_RING, "key_name": KEY_NAME})
    return plaintext
```

---

## CMEK — Customer-Managed Encryption Keys

```bash
KEY_RESOURCE="projects/$PROJECT/locations/$REGION/keyRings/$KEY_RING/cryptoKeys/app-data-key"

# Grant GCS service agent encrypt/decrypt permission (for CMEK-protected bucket)
GCS_SA="service-$(gcloud projects describe $PROJECT --format='value(projectNumber)')@gs-project-accounts.iam.gserviceaccount.com"
gcloud kms keys add-iam-policy-binding app-data-key \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --member="serviceAccount:$GCS_SA" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"

# Create a CMEK-protected GCS bucket
gcloud storage buckets create gs://my-app-prod-secure \
    --project=$PROJECT \
    --location=$REGION \
    --default-encryption-key=$KEY_RESOURCE

# Grant BigQuery service agent access for CMEK-protected dataset
BQ_SA="bq-$(gcloud projects describe $PROJECT --format='value(projectNumber)')@bigquery-encryption.iam.gserviceaccount.com"
gcloud kms keys add-iam-policy-binding app-data-key \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --member="serviceAccount:$BQ_SA" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"

# Create CMEK-protected BigQuery dataset
bq mk \
    --project_id=$PROJECT \
    --dataset \
    --location=US \
    --customer_managed_encryption_key=$KEY_RESOURCE \
    $PROJECT:my_secure_dataset
```

---

## Key Rotation

```bash
# Manual rotation (creates new primary version, old version still active for decrypt)
gcloud kms keys versions create \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --key=app-data-key

# Set a different version as primary
gcloud kms keys update app-data-key \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --primary-version=3

# List versions
gcloud kms keys versions list \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --key=app-data-key \
    --format="table(name,state,createTime)"

# Disable an old version
gcloud kms keys versions disable 1 \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --key=app-data-key

# Destroy an old version (48-hour pending destruction period)
gcloud kms keys versions destroy 1 \
    --project=$PROJECT \
    --location=$REGION \
    --keyring=$KEY_RING \
    --key=app-data-key
```

---

## References

- [Cloud KMS documentation](https://cloud.google.com/kms/docs)
- [Python client library](https://cloud.google.com/python/docs/reference/cloudkms/latest)
- [CMEK overview](https://cloud.google.com/kms/docs/cmek)
- [Key rotation](https://cloud.google.com/kms/docs/key-rotation)

---

← [Previous: Secret Manager](./secret-manager.md) | [Home](../../README.md) | [Next: Cloud Armor →](./cloud-armor.md)
