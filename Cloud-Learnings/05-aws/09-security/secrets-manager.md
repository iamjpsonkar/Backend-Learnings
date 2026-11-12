← [Previous: KMS](./kms.md) | [Home](../../README.md) | [Next: ACM →](./acm.md)

---

# AWS Secrets Manager

Secrets Manager stores, retrieves, and automatically rotates secrets such as database credentials, API keys, OAuth tokens, and SSH keys. Applications retrieve secrets at runtime using the SDK — no hardcoded credentials.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Secret** | An encrypted record containing a secret value (string or binary) |
| **Secret version** | A versioned copy of the secret value — multiple versions coexist during rotation |
| **Rotation** | Automated process that creates a new secret version, updates the target service, and marks the old version deprecated |
| **Resource policy** | Controls cross-account access to a secret (like an S3 bucket policy) |
| **KMS key** | The CMK used to encrypt/decrypt the secret (defaults to `aws/secretsmanager`) |

---

## Creating Secrets

```bash
# Store a simple string secret
SECRET_ARN=$(aws secretsmanager create-secret \
    --name prod/my-app/api-key \
    --description "Third-party API key for my-app production" \
    --secret-string "sk-live-abc123def456" \
    --kms-key-id alias/my-app-key \
    --tags Key=Environment,Value=production Key=Service,Value=my-app \
    --query 'ARN' --output text)

echo "Secret ARN: $SECRET_ARN"

# Store a JSON object (recommended for credentials)
aws secretsmanager create-secret \
    --name prod/my-app/database \
    --description "PostgreSQL credentials for my-app production" \
    --secret-string '{
        "username": "dbadmin",
        "password": "InitialPassword123!",
        "host": "my-db.abc.us-east-1.rds.amazonaws.com",
        "port": 5432,
        "dbname": "myapp",
        "engine": "postgres"
    }' \
    --kms-key-id alias/my-app-key

# Store binary data (e.g., TLS private key)
aws secretsmanager create-secret \
    --name prod/my-app/tls-key \
    --secret-binary fileb:///path/to/private.key
```

---

## Retrieving Secrets

```bash
# Retrieve the current secret value
aws secretsmanager get-secret-value \
    --secret-id prod/my-app/database \
    --query 'SecretString' --output text

# Retrieve a specific version
aws secretsmanager get-secret-value \
    --secret-id prod/my-app/database \
    --version-stage AWSPREVIOUS \
    --query 'SecretString' --output text

# List versions
aws secretsmanager list-secret-version-ids \
    --secret-id prod/my-app/database \
    --query 'Versions[*].{ID:VersionId,Stages:VersionStages,Created:CreatedDate}' \
    --output table
```

### Python — Recommended Application Pattern

```python
import boto3
import json
import logging
from functools import lru_cache
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Module-level client — reused across Lambda invocations
_sm_client = boto3.client("secretsmanager", region_name="us-east-1")


@lru_cache(maxsize=None)
def _get_secret_cached(secret_id: str) -> str:
    """
    Internal cached retrieval. Cache is valid for the lifetime of the process.
    In Lambda: cache persists across warm invocations (typically 5–15 minutes).
    """
    logger.info("Fetching secret from Secrets Manager: secret_id=%s", secret_id)
    try:
        response = _sm_client.get_secret_value(SecretId=secret_id)
        logger.debug("Secret retrieved: secret_id=%s", secret_id)
        return response.get("SecretString") or response.get("SecretBinary", b"").decode()
    except ClientError as e:
        code = e.response["Error"]["Code"]
        logger.error("Failed to retrieve secret: secret_id=%s error=%s", secret_id, code)
        if code in ("ResourceNotFoundException", "InvalidRequestException"):
            raise ValueError(f"Secret not found: {secret_id}") from e
        raise


def get_secret(secret_id: str) -> str:
    """Get a secret value as a string."""
    return _get_secret_cached(secret_id)


def get_secret_json(secret_id: str) -> dict:
    """Get a secret value parsed as JSON."""
    raw = get_secret(secret_id)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Secret is not valid JSON: secret_id=%s error=%s", secret_id, str(e))
        raise ValueError(f"Secret {secret_id} is not valid JSON") from e


# Usage example
def connect_to_database():
    creds = get_secret_json("prod/my-app/database")
    logger.info("Connecting to database: host=%s dbname=%s user=%s",
                creds["host"], creds["dbname"], creds["username"])
    # Use creds["host"], creds["username"], creds["password"], etc.
```

---

## Automatic Rotation

Secrets Manager uses a Lambda function to rotate secrets. AWS provides built-in rotation functions for RDS, Aurora, Redshift, DocumentDB, and third-party services.

```bash
SECRET_ARN="arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/my-app/database"

# Enable rotation using the AWS-managed Lambda for RDS PostgreSQL
aws secretsmanager rotate-secret \
    --secret-id $SECRET_ARN \
    --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRDSPostgreSQLRotationSingleUser \
    --rotation-rules AutomaticallyAfterDays=30

# Trigger an immediate rotation (useful after initial setup)
aws secretsmanager rotate-secret \
    --secret-id $SECRET_ARN \
    --rotate-immediately

# View rotation configuration
aws secretsmanager describe-secret \
    --secret-id $SECRET_ARN \
    --query '{
        Name:Name,
        RotationEnabled:RotationEnabled,
        RotationLambda:RotationLambdaARN,
        RotationRules:RotationRules,
        LastRotated:LastRotatedDate,
        NextRotation:NextRotationDate
    }'
```

### Custom Rotation Lambda

For third-party services without built-in rotation, implement a Lambda following the four-step rotation protocol:

```python
import boto3
import logging

logger = logging.getLogger(__name__)
sm = boto3.client("secretsmanager")


def handler(event, context):
    """
    AWS Secrets Manager rotation Lambda.
    Called four times per rotation cycle with different steps.
    """
    secret_id = event["SecretId"]
    token = event["ClientRequestToken"]
    step = event["Step"]

    logger.info("Rotation invoked: secret_id=%s step=%s token=%s", secret_id, step, token)

    if step == "createSecret":
        create_secret(secret_id, token)
    elif step == "setSecret":
        set_secret(secret_id, token)
    elif step == "testSecret":
        test_secret(secret_id, token)
    elif step == "finishSecret":
        finish_secret(secret_id, token)
    else:
        raise ValueError(f"Unknown step: {step}")


def create_secret(secret_id: str, token: str) -> None:
    """Step 1: Generate and store the new secret value as AWSPENDING."""
    logger.info("Creating new secret version: secret_id=%s", secret_id)
    try:
        sm.get_secret_value(SecretId=secret_id, VersionId=token, VersionStage="AWSPENDING")
        logger.info("AWSPENDING version already exists, skipping create: secret_id=%s", secret_id)
        return
    except sm.exceptions.ResourceNotFoundException:
        pass

    current = json.loads(sm.get_secret_value(SecretId=secret_id, VersionStage="AWSCURRENT")["SecretString"])
    new_password = generate_strong_password()   # implement your own generator

    sm.put_secret_value(
        SecretId=secret_id,
        ClientRequestToken=token,
        SecretString=json.dumps({**current, "password": new_password}),
        VersionStages=["AWSPENDING"],
    )
    logger.info("New secret version stored as AWSPENDING: secret_id=%s", secret_id)


def set_secret(secret_id: str, token: str) -> None:
    """Step 2: Apply the new password to the target service."""
    logger.info("Setting new password on target service: secret_id=%s", secret_id)
    pending = json.loads(sm.get_secret_value(SecretId=secret_id, VersionId=token, VersionStage="AWSPENDING")["SecretString"])
    # Apply pending["password"] to the target service (e.g., ALTER USER in PostgreSQL)
    logger.info("Password applied to target service: secret_id=%s user=%s", secret_id, pending.get("username"))


def test_secret(secret_id: str, token: str) -> None:
    """Step 3: Verify the new password works."""
    logger.info("Testing new secret: secret_id=%s", secret_id)
    pending = json.loads(sm.get_secret_value(SecretId=secret_id, VersionId=token, VersionStage="AWSPENDING")["SecretString"])
    # Try connecting with pending["password"]; raise an exception if it fails
    logger.info("Secret test passed: secret_id=%s", secret_id)


def finish_secret(secret_id: str, token: str) -> None:
    """Step 4: Promote AWSPENDING to AWSCURRENT."""
    logger.info("Promoting AWSPENDING to AWSCURRENT: secret_id=%s", secret_id)
    metadata = sm.describe_secret(SecretId=secret_id)
    current_version = [v for v, stages in metadata["VersionIdsToStages"].items()
                       if "AWSCURRENT" in stages][0]

    sm.update_secret_version_stage(
        SecretId=secret_id,
        VersionStage="AWSCURRENT",
        MoveToVersionId=token,
        RemoveFromVersionId=current_version,
    )
    logger.info("Rotation complete: secret_id=%s new_version=%s", secret_id, token)


def generate_strong_password() -> str:
    import secrets, string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(32))
```

---

## Cross-Account Access via Resource Policy

```bash
# Allow another account to read this secret
aws secretsmanager put-resource-policy \
    --secret-id $SECRET_ARN \
    --resource-policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowCrossAccountRead",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::222222222222:role/my-app-role"
            },
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": "*"
        }]
    }'

# In the consumer account, also grant via IAM policy:
# secretsmanager:GetSecretValue on the specific secret ARN
```

---

## Managing Secrets

```bash
# List all secrets (with rotation status)
aws secretsmanager list-secrets \
    --query 'SecretList[*].{
        Name:Name,
        LastChanged:LastChangedDate,
        LastRotated:LastRotatedDate,
        RotationEnabled:RotationEnabled,
        NextRotation:NextRotationDate
    }' \
    --output table

# Update a secret's value manually
aws secretsmanager update-secret \
    --secret-id prod/my-app/database \
    --secret-string '{"username": "dbadmin", "password": "NewPassword456!", "host": "..."}'

# Add tags
aws secretsmanager tag-resource \
    --secret-id prod/my-app/database \
    --tags Key=DataClassification,Value=sensitive

# Delete a secret (with 30-day recovery window by default)
aws secretsmanager delete-secret \
    --secret-id prod/my-app/database \
    --recovery-window-in-days 30

# Delete immediately (no recovery — use with caution)
aws secretsmanager delete-secret \
    --secret-id prod/my-app/database \
    --force-delete-without-recovery

# Restore a deleted secret (within recovery window)
aws secretsmanager restore-secret --secret-id prod/my-app/database
```

---

## Secrets Manager vs Parameter Store

| | Secrets Manager | SSM Parameter Store (SecureString) |
|--|----------------|-------------------------------------|
| Cost | $0.40/secret/month + $0.05/10K API calls | Free (standard); $0.05/advanced param/month |
| Auto-rotation | Built-in Lambda rotation | Manual only |
| Versioning | Full version history | Last version only |
| Cross-account | Resource policies | Not supported natively |
| Max value size | 65,536 bytes | 4KB (standard), 8KB (advanced) |
| Hierarchy | Flat names | Path-based (`/env/service/key`) |
| **Use when** | Credentials requiring rotation | Config values, feature flags, non-rotating secrets |

---

## References

- [Secrets Manager documentation](https://docs.aws.amazon.com/secretsmanager/latest/userguide/)
- [Rotation functions](https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_available-rotation-templates.html)
- [Rotation Lambda template](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets-lambda-function-overview.html)
---

← [Previous: KMS](./kms.md) | [Home](../../README.md) | [Next: ACM →](./acm.md)
