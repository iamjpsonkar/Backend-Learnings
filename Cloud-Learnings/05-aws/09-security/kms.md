← [Previous: AWS Security](./README.md) | [Home](../../README.md) | [Next: Secrets Manager →](./secrets-manager.md)

---

# AWS Key Management Service (KMS)

KMS is a managed service for creating and controlling cryptographic keys. It integrates natively with 100+ AWS services (S3, EBS, RDS, DynamoDB, Secrets Manager, etc.) and handles key storage, rotation, and access control without exposing raw key material.

---

## Key Types

| Type | Created by | Key material | Cross-region | Use |
|------|-----------|-------------|-------------|-----|
| **AWS managed key** | Automatically by AWS service | AWS | No | Default encryption for services (free to create, $0.03/10K API calls) |
| **Customer managed key (CMK)** | You | AWS or imported | No (use MRK) | Full control: policy, rotation, grants, audit |
| **Multi-Region Key (MRK)** | You | AWS (replicated) | Yes | Encrypt in one region, decrypt in another |
| **Imported key** | You | You provide | No | Bring-your-own-key (BYOK) compliance requirements |

**Pricing:** $1/month per CMK + $0.03 per 10,000 API calls (free tier: 20,000 API calls/month).

---

## Creating a CMK

```bash
# Create a symmetric CMK (AES-256-GCM — used for most AWS service encryption)
KEY_ID=$(aws kms create-key \
    --description "Production application encryption key" \
    --key-usage ENCRYPT_DECRYPT \
    --origin AWS_KMS \
    --tags TagKey=Environment,TagValue=production TagKey=Service,TagValue=my-app \
    --query 'KeyMetadata.KeyId' --output text)

echo "Key ID: $KEY_ID"
echo "Key ARN: arn:aws:kms:us-east-1:123456789012:key/$KEY_ID"

# Create a human-readable alias
aws kms create-alias \
    --alias-name alias/my-app-key \
    --target-key-id $KEY_ID

# Enable automatic annual rotation
aws kms enable-key-rotation --key-id $KEY_ID

# Verify rotation status
aws kms get-key-rotation-status --key-id $KEY_ID

# Describe the key
aws kms describe-key \
    --key-id alias/my-app-key \
    --query 'KeyMetadata.{
        ID:KeyId,
        Alias:null,
        State:KeyState,
        Created:CreationDate,
        Rotation:KeyRotationStatus,
        Usage:KeyUsage,
        Spec:CustomerMasterKeySpec
    }'
```

---

## Key Policy

The key policy is the primary access control mechanism for a CMK. Unlike IAM policies alone, **IAM policies have no effect unless the key policy grants access** (or enables IAM to manage access).

```bash
# View the current key policy
aws kms get-key-policy \
    --key-id alias/my-app-key \
    --policy-name default \
    --query 'Policy' --output text | python3 -m json.tool

# Set a key policy with controlled access
aws kms put-key-policy \
    --key-id $KEY_ID \
    --policy-name default \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "EnableIAMUserPermissions",
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                "Action": "kms:*",
                "Resource": "*"
            },
            {
                "Sid": "AllowAppRole",
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::123456789012:role/my-app-role"},
                "Action": [
                    "kms:Decrypt",
                    "kms:GenerateDataKey",
                    "kms:DescribeKey"
                ],
                "Resource": "*"
            },
            {
                "Sid": "AllowSecretsManagerRotation",
                "Effect": "Allow",
                "Principal": {"Service": "secretsmanager.amazonaws.com"},
                "Action": [
                    "kms:Decrypt",
                    "kms:GenerateDataKey",
                    "kms:CreateGrant"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "kms:CallerAccount": "123456789012"
                    }
                }
            },
            {
                "Sid": "DenyExternalPrincipals",
                "Effect": "Deny",
                "Principal": {"AWS": "*"},
                "Action": "kms:*",
                "Resource": "*",
                "Condition": {
                    "StringNotEquals": {
                        "kms:CallerAccount": "123456789012"
                    }
                }
            }
        ]
    }'
```

---

## Envelope Encryption

KMS does not encrypt large data directly. Instead it generates a **data key**, which your application uses to encrypt data locally. Only the encrypted data key is stored alongside the ciphertext — the plaintext data key is discarded after use.

```
GenerateDataKey(CMK)
    → Returns: plaintext data key + encrypted data key

Encrypt your data locally using the plaintext data key
Store: ciphertext + encrypted data key (together)
Discard: plaintext data key from memory

--- later, to decrypt ---
Decrypt(encrypted data key) → plaintext data key
Decrypt(ciphertext) using plaintext data key
```

```python
import boto3
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import logging

logger = logging.getLogger(__name__)
kms = boto3.client("kms", region_name="us-east-1")
KEY_ID = "alias/my-app-key"


def encrypt_data(plaintext: bytes) -> dict:
    """
    Encrypt data using KMS envelope encryption.
    Returns a dict with ciphertext and encrypted data key.
    """
    logger.info("Generating data key: key_id=%s", KEY_ID)
    response = kms.generate_data_key(KeyId=KEY_ID, KeySpec="AES_256")

    plaintext_key = response["Plaintext"]          # use for encryption, then discard
    encrypted_key = response["CiphertextBlob"]     # store alongside ciphertext

    try:
        nonce = os.urandom(12)   # 96-bit nonce for AES-GCM
        aesgcm = AESGCM(plaintext_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        logger.debug("Data encrypted: plaintext_bytes=%d ciphertext_bytes=%d", len(plaintext), len(ciphertext))
        return {
            "ciphertext": ciphertext,
            "nonce": nonce,
            "encrypted_key": encrypted_key,
        }
    finally:
        # Zero out the plaintext key from memory
        plaintext_key = b"\x00" * len(plaintext_key)


def decrypt_data(payload: dict) -> bytes:
    """Decrypt data using the stored encrypted data key."""
    logger.info("Decrypting data key via KMS")
    response = kms.decrypt(CiphertextBlob=payload["encrypted_key"])
    plaintext_key = response["Plaintext"]

    try:
        aesgcm = AESGCM(plaintext_key)
        plaintext = aesgcm.decrypt(payload["nonce"], payload["ciphertext"], None)
        logger.debug("Data decrypted: plaintext_bytes=%d", len(plaintext))
        return plaintext
    finally:
        plaintext_key = b"\x00" * len(plaintext_key)
```

---

## KMS Grants

Grants delegate specific KMS operations to a principal without modifying the key policy. Useful for temporary, programmatic access (e.g., EC2 Auto Scaling decrypting EBS volumes for a specific user's ASG).

```bash
# Grant a role the ability to decrypt (temporary delegation)
GRANT_TOKEN=$(aws kms create-grant \
    --key-id $KEY_ID \
    --grantee-principal arn:aws:iam::123456789012:role/data-processing-role \
    --operations Decrypt GenerateDataKey DescribeKey \
    --name "data-processing-grant" \
    --constraints '{"EncryptionContextSubset": {"Purpose": "data-processing"}}' \
    --query 'GrantToken' --output text)

# List grants on a key
aws kms list-grants \
    --key-id $KEY_ID \
    --query 'Grants[*].{Name:Name,Grantee:GranteePrincipal,Ops:Operations,Created:CreationDate}' \
    --output table

# Revoke a grant
aws kms revoke-grant \
    --key-id $KEY_ID \
    --grant-id $(aws kms list-grants --key-id $KEY_ID \
        --query 'Grants[?Name==`data-processing-grant`].GrantId' --output text)
```

---

## Encryption Context

Encryption context is a set of key-value pairs that are cryptographically bound to the ciphertext. The same context must be provided for decryption, providing an additional verification layer.

```bash
# Encrypt with context
aws kms encrypt \
    --key-id alias/my-app-key \
    --plaintext "supersecret" \
    --encryption-context "Purpose=backup,Environment=production" \
    --query 'CiphertextBlob' --output text | base64 -d > /tmp/encrypted.bin

# Decrypt — must provide the same context
aws kms decrypt \
    --ciphertext-blob fileb:///tmp/encrypted.bin \
    --encryption-context "Purpose=backup,Environment=production" \
    --query 'Plaintext' --output text | base64 -d
```

---

## Multi-Region Keys

```bash
# Create a primary MRK in us-east-1
PRIMARY_KEY=$(aws kms create-key \
    --description "Multi-region key — primary" \
    --key-usage ENCRYPT_DECRYPT \
    --multi-region \
    --query 'KeyMetadata.KeyId' --output text)

# Replicate to eu-west-1 (same key material, different ARN)
aws kms replicate-key \
    --key-id $PRIMARY_KEY \
    --replica-region eu-west-1 \
    --description "Multi-region key — eu-west-1 replica"

# Use case: encrypt in us-east-1, decrypt in eu-west-1 without re-encryption
# Both keys share the same key material — ciphertext is interoperable
```

---

## Disabling and Scheduling Deletion

```bash
# Disable a key (encryption/decryption fail; key is retained)
aws kms disable-key --key-id $KEY_ID

# Re-enable
aws kms enable-key --key-id $KEY_ID

# Schedule deletion (7–30 day waiting period — cannot be cancelled)
aws kms schedule-key-deletion \
    --key-id $KEY_ID \
    --pending-window-in-days 30

# Cancel pending deletion
aws kms cancel-key-deletion --key-id $KEY_ID
```

---

## Common Patterns

| Scenario | Pattern |
|----------|---------|
| S3 bucket encryption | SSE-KMS with CMK ARN in bucket policy |
| EBS volume encryption | Specify `--kms-key-id` in `aws ec2 create-volume` |
| RDS/Aurora at-rest encryption | `--kms-key-id` in `create-db-instance` / `create-db-cluster` |
| Secrets Manager secret | Default or custom CMK via `--kms-key-id` |
| Lambda environment variables | `--kms-key-arn` in function configuration |
| Cross-account access | Add target account principal to key policy + target account IAM policy |

---

## References

- [KMS documentation](https://docs.aws.amazon.com/kms/latest/developerguide/)
- [Key policies](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)
- [Envelope encryption](https://docs.aws.amazon.com/kms/latest/developerguide/concepts.html#enveloping)
- [Multi-Region keys](https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html)
---

← [Previous: AWS Security](./README.md) | [Home](../../README.md) | [Next: Secrets Manager →](./secrets-manager.md)
