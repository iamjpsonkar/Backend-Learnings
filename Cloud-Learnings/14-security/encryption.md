← [Previous: Secrets Management](./secrets-management.md) | [Home](../README.md) | [Next: Vulnerability Management →](./vulnerability-management.md)

---

# Encryption

Encryption protects data at rest and in transit. Cloud providers offer managed key management services (KMS) that handle key storage, rotation, and access controls — you should almost never manage raw encryption keys yourself.

---

## Concepts

| Term | Meaning |
|------|---------|
| **Symmetric encryption** | Same key for encrypt and decrypt (AES-256) — fast, used for bulk data |
| **Asymmetric encryption** | Public key encrypts, private key decrypts (RSA, ECDSA) — used for key exchange and signatures |
| **Envelope encryption** | Encrypt data with a data encryption key (DEK), then encrypt the DEK with a master key (KEK) |
| **AEAD** | Authenticated Encryption with Associated Data — encryption + tamper detection (AES-GCM) |
| **HSM** | Hardware Security Module — tamper-proof hardware that stores keys; keys never leave the device |
| **TLS** | Transport Layer Security — encrypts data in transit; use TLS 1.2+ minimum, TLS 1.3 preferred |

---

## Envelope Encryption Pattern

```
┌─────────────────────────────────────────────────────────┐
│  Plaintext data                                         │
│       │                                                 │
│       ▼                                                 │
│  Encrypt with DEK (AES-256-GCM) → Ciphertext           │
│       │                                                 │
│       ▼                                                 │
│  Encrypt DEK with CMK (in KMS) → Encrypted DEK         │
│                                                         │
│  Store: Ciphertext + Encrypted DEK (no plaintext DEK)  │
└─────────────────────────────────────────────────────────┘

To decrypt:
  1. Send Encrypted DEK to KMS → KMS returns plaintext DEK
  2. Use plaintext DEK to decrypt Ciphertext → Plaintext data
  3. Zero out DEK from memory
```

---

## AWS KMS

```bash
# Create a customer-managed key (CMK)
aws kms create-key \
    --description "Production data encryption key" \
    --key-usage ENCRYPT_DECRYPT \
    --key-spec SYMMETRIC_DEFAULT \
    --region us-east-1

KEY_ID=$(aws kms create-key --query 'KeyMetadata.KeyId' --output text ...)

# Create an alias
aws kms create-alias \
    --alias-name alias/prod/my-app-data \
    --target-key-id $KEY_ID

# Enable automatic key rotation (yearly)
aws kms enable-key-rotation --key-id $KEY_ID

# Encrypt data (up to 4 KB directly)
aws kms encrypt \
    --key-id alias/prod/my-app-data \
    --plaintext fileb://secret.txt \
    --output text \
    --query CiphertextBlob | base64 --decode > secret.enc

# Decrypt
aws kms decrypt \
    --ciphertext-blob fileb://secret.enc \
    --output text \
    --query Plaintext | base64 --decode

# Generate a data key for envelope encryption
aws kms generate-data-key \
    --key-id alias/prod/my-app-data \
    --key-spec AES_256 \
    --query '[Plaintext, CiphertextBlob]' \
    --output text
```

### Python — Envelope Encryption with AWS KMS

```python
import base64
import logging
import os
import struct

import boto3
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

kms = boto3.client("kms", region_name=os.environ.get("AWS_REGION", "us-east-1"))
KEY_ALIAS = os.environ["KMS_KEY_ALIAS"]  # e.g., alias/prod/my-app-data


def encrypt(plaintext: bytes) -> bytes:
    """
    Envelope-encrypt plaintext using KMS + AES-256-GCM.
    Returns: 2-byte DEK length + encrypted DEK + nonce + ciphertext
    """
    logger.info("Generating data key", extra={"key_alias": KEY_ALIAS})
    response = kms.generate_data_key(
        KeyId=KEY_ALIAS,
        KeySpec="AES_256",
    )
    plaintext_dek: bytes = response["Plaintext"]
    encrypted_dek: bytes = response["CiphertextBlob"]

    try:
        nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
        aesgcm = AESGCM(plaintext_dek)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        logger.info("Data encrypted successfully")
    finally:
        # Zero out plaintext DEK from memory
        plaintext_dek = b"\x00" * len(plaintext_dek)

    dek_len = struct.pack(">H", len(encrypted_dek))
    return dek_len + encrypted_dek + nonce + ciphertext


def decrypt(blob: bytes) -> bytes:
    """Reverse envelope encryption."""
    dek_len = struct.unpack(">H", blob[:2])[0]
    encrypted_dek = blob[2 : 2 + dek_len]
    nonce = blob[2 + dek_len : 2 + dek_len + 12]
    ciphertext = blob[2 + dek_len + 12 :]

    logger.info("Decrypting data key via KMS", extra={"key_alias": KEY_ALIAS})
    response = kms.decrypt(CiphertextBlob=encrypted_dek)
    plaintext_dek: bytes = response["Plaintext"]

    try:
        aesgcm = AESGCM(plaintext_dek)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        logger.info("Data decrypted successfully")
        return plaintext
    finally:
        plaintext_dek = b"\x00" * len(plaintext_dek)
```

### KMS Key Policy (Least Privilege)

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowKeyAdmins",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::123456789012:role/KeyAdminRole"
            },
            "Action": ["kms:Create*", "kms:Describe*", "kms:Enable*",
                        "kms:List*", "kms:Put*", "kms:Update*", "kms:Revoke*",
                        "kms:Disable*", "kms:Get*", "kms:Delete*", "kms:ScheduleKeyDeletion"],
            "Resource": "*"
        },
        {
            "Sid": "AllowAppEncryptDecrypt",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
            },
            "Action": [
                "kms:GenerateDataKey",
                "kms:Decrypt"
            ],
            "Resource": "*"
        }
    ]
}
```

---

## GCP Cloud KMS

```bash
# Create keyring and key
gcloud kms keyrings create prod-keyring \
    --location=us-east1

gcloud kms keys create my-app-data-key \
    --keyring=prod-keyring \
    --location=us-east1 \
    --purpose=encryption \
    --rotation-period=90d \
    --next-rotation-time=$(date -u -d '90 days' +%Y-%m-%dT%H:%M:%SZ)

# Encrypt
gcloud kms encrypt \
    --keyring=prod-keyring \
    --key=my-app-data-key \
    --location=us-east1 \
    --plaintext-file=secret.txt \
    --ciphertext-file=secret.enc

# Decrypt
gcloud kms decrypt \
    --keyring=prod-keyring \
    --key=my-app-data-key \
    --location=us-east1 \
    --ciphertext-file=secret.enc \
    --plaintext-file=secret.txt

# CMEK for GCS bucket
gsutil mb -l us-east1 gs://my-encrypted-bucket
gcloud storage buckets update gs://my-encrypted-bucket \
    --default-encryption-key=projects/my-project/locations/us-east1/keyRings/prod-keyring/cryptoKeys/my-app-data-key
```

---

## Azure Key Vault

```bash
# Create Key Vault (Purge Protection prevents accidental deletion)
az keyvault create \
    --name my-app-kv-prod \
    --resource-group rg-production \
    --location eastus \
    --sku premium \
    --enable-purge-protection true \
    --retention-days 90

# Create an RSA key backed by HSM (Premium SKU)
az keyvault key create \
    --vault-name my-app-kv-prod \
    --name my-app-data-key \
    --kty RSA-HSM \
    --size 2048 \
    --ops encrypt decrypt

# Rotate key (creates new key version)
az keyvault key rotate \
    --vault-name my-app-kv-prod \
    --name my-app-data-key

# Set rotation policy
az keyvault key rotation-policy update \
    --vault-name my-app-kv-prod \
    --name my-app-data-key \
    --value @rotation-policy.json
```

```json
// rotation-policy.json
{
    "lifetimeActions": [
        {
            "trigger": { "timeAfterCreate": "P90D" },
            "action": { "type": "rotate" }
        },
        {
            "trigger": { "timeBeforeExpiry": "P30D" },
            "action": { "type": "notify" }
        }
    ],
    "attributes": {
        "expiryTime": "P1Y"
    }
}
```

---

## Encryption at Rest — Storage Services

| Service | Default encryption | CMEK option |
|---------|-------------------|-------------|
| AWS S3 | AES-256 (SSE-S3) | SSE-KMS with CMK |
| AWS RDS | AES-256 (at creation) | KMS CMK |
| AWS EBS | AES-256 | KMS CMK |
| GCS | AES-256 | Cloud KMS CMEK |
| GCP Cloud SQL | AES-256 | Cloud KMS CMEK |
| Azure Blob Storage | AES-256 | Key Vault key |
| Azure SQL | AES-256 (TDE) | Key Vault BYOK |

```bash
# AWS: Enforce S3 bucket encryption with CMK
aws s3api put-bucket-encryption \
    --bucket my-app-data \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "aws:kms",
                "KMSMasterKeyID": "alias/prod/my-app-data"
            },
            "BucketKeyEnabled": true
        }]
    }'

# Deny unencrypted S3 uploads
aws s3api put-bucket-policy --bucket my-app-data --policy '{
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "DenyUnencryptedUploads",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:PutObject",
        "Resource": "arn:aws:s3:::my-app-data/*",
        "Condition": {
            "StringNotEquals": {
                "s3:x-amz-server-side-encryption": "aws:kms"
            }
        }
    }]
}'

# AWS RDS: enable encryption at creation (cannot enable after)
aws rds create-db-instance \
    --db-instance-identifier prod-postgres \
    --storage-encrypted \
    --kms-key-id alias/prod/rds-key \
    --engine postgres \
    --db-instance-class db.t3.medium \
    --allocated-storage 100
```

---

## TLS Configuration

```bash
# Generate certificate with Let's Encrypt (certbot)
certbot certonly \
    --dns-route53 \
    -d api.my-app.com \
    --agree-tos \
    --email ops@my-app.com

# Check TLS certificate details
openssl s_client -connect api.my-app.com:443 -servername api.my-app.com </dev/null 2>/dev/null \
    | openssl x509 -noout -dates -subject -issuer

# Check for weak ciphers
nmap --script ssl-enum-ciphers -p 443 api.my-app.com

# Test TLS 1.3 support
curl -v --tls-max 1.3 https://api.my-app.com/health 2>&1 | grep "SSL connection"

# Nginx: secure TLS config
# ssl_protocols TLSv1.2 TLSv1.3;
# ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305;
# ssl_prefer_server_ciphers off;  # Let client pick (TLS 1.3 handles this)
# ssl_session_timeout 1d;
# ssl_session_cache shared:MozSSL:10m;
# add_header Strict-Transport-Security "max-age=63072000" always;
```

---

## References

- [AWS KMS Developer Guide](https://docs.aws.amazon.com/kms/latest/developerguide/)
- [GCP Cloud KMS](https://cloud.google.com/kms/docs)
- [Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/)
- [NIST SP 800-57 Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)
- [TLS Best Practices (Mozilla)](https://wiki.mozilla.org/Security/Server_Side_TLS)

---

← [Previous: Secrets Management](./secrets-management.md) | [Home](../README.md) | [Next: Vulnerability Management →](./vulnerability-management.md)
