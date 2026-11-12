← [Previous: Network Security](./network-security.md) | [Home](../README.md) | [Next: Encryption →](./encryption.md)

---

# Secrets Management

Secrets — API keys, database passwords, TLS certificates, and tokens — must never appear in code, environment files, or container images. They require secure storage, access controls, versioning, and rotation.

---

## Anti-Patterns to Avoid

```bash
# ❌ NEVER do these:
export DB_PASSWORD="plaintext-in-shell-history"
echo "API_KEY=abc123" >> .env && git add .env   # Secrets in Git
docker run -e SECRET=abc123 ...                  # Secrets in container env visible to all
```

---

## Secret Detection in CI

```bash
# git-secrets (pre-commit hook)
brew install git-secrets
git secrets --install
git secrets --register-aws

# detect-secrets
pip install detect-secrets
detect-secrets scan > .secrets.baseline
detect-secrets audit .secrets.baseline

# Gitleaks (fast — scan entire history)
brew install gitleaks
gitleaks detect --source . --verbose    # Scan working directory
gitleaks detect --log-opts HEAD~10..    # Scan last 10 commits
gitleaks protect --staged               # Pre-commit hook

# TruffleHog
trufflehog git file://. --since-commit HEAD~5
```

---

## AWS Secrets Manager

```python
import boto3
import json
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

region = os.environ.get("AWS_REGION", "us-east-1")
sm = boto3.client("secretsmanager", region_name=region)


@lru_cache(maxsize=None)
def get_secret(secret_name: str, version: str = "AWSCURRENT") -> str:
    """Retrieve and cache a secret string."""
    logger.info("Fetching secret", extra={"secret_name": secret_name})
    response = sm.get_secret_value(
        SecretId=secret_name,
        VersionStage=version,
    )
    logger.info("Secret fetched", extra={"secret_name": secret_name})
    return response["SecretString"]


@lru_cache(maxsize=None)
def get_secret_dict(secret_name: str) -> dict:
    """Retrieve a JSON-formatted secret as a dictionary."""
    return json.loads(get_secret(secret_name))


def get_db_config() -> dict:
    """Load database credentials from Secrets Manager."""
    secret = get_secret_dict("prod/my-app/db-credentials")
    return {
        "host": os.environ["DB_HOST"],         # Non-sensitive config from env
        "port": int(os.environ.get("DB_PORT", "5432")),
        "dbname": os.environ["DB_NAME"],
        "user": secret["username"],
        "password": secret["password"],
    }
```

```bash
# Create a secret
aws secretsmanager create-secret \
    --name prod/my-app/db-credentials \
    --secret-string '{"username":"my_app","password":"generated-pass-here"}' \
    --region us-east-1

# Enable automatic rotation (Lambda rotator)
aws secretsmanager rotate-secret \
    --secret-id prod/my-app/db-credentials \
    --rotation-lambda-arn arn:aws:lambda:us-east-1:123456789012:function:SecretsManagerRotator \
    --rotation-rules AutomaticallyAfterDays=30

# Grant a role access
aws secretsmanager put-resource-policy \
    --secret-id prod/my-app/db-credentials \
    --resource-policy '{
        "Version":"2012-10-17",
        "Statement":[{
            "Effect":"Allow",
            "Principal":{"AWS":"arn:aws:iam::123456789012:role/MyAppRole"},
            "Action":"secretsmanager:GetSecretValue",
            "Resource":"*"
        }]
    }'
```

---

## HashiCorp Vault

```bash
# Start Vault dev server (local testing)
vault server -dev

export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'

# Enable KV secrets engine (version 2)
vault secrets enable -path=secret kv-v2

# Write a secret
vault kv put secret/my-app/db-credentials \
    username=my_app \
    password="$(openssl rand -base64 32)"

# Read a secret
vault kv get secret/my-app/db-credentials
vault kv get -field=password secret/my-app/db-credentials

# Rotate (add new version)
vault kv patch secret/my-app/db-credentials \
    password="$(openssl rand -base64 32)"

# Create a policy (least-privilege access)
vault policy write my-app-policy - <<EOF
path "secret/data/my-app/*" {
    capabilities = ["read"]
}
path "secret/metadata/my-app/*" {
    capabilities = ["list"]
}
EOF

# Enable Kubernetes auth
vault auth enable kubernetes
vault write auth/kubernetes/config \
    kubernetes_host=https://kubernetes.default.svc.cluster.local \
    kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# Create a role binding KSA → policy
vault write auth/kubernetes/role/my-app \
    bound_service_account_names=my-app \
    bound_service_account_namespaces=production \
    policies=my-app-policy \
    ttl=1h
```

### Vault Agent Sidecar (Kubernetes)

```yaml
# Kubernetes Pod with Vault Agent injector
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "my-app"
        vault.hashicorp.com/agent-inject-secret-db: "secret/data/my-app/db-credentials"
        vault.hashicorp.com/agent-inject-template-db: |
          {{- with secret "secret/data/my-app/db-credentials" -}}
          export DB_PASSWORD="{{ .Data.data.password }}"
          {{- end }}
    spec:
      serviceAccountName: my-app
      containers:
        - name: app
          image: my-app:latest
          command: ["/bin/sh", "-c"]
          args:
            - source /vault/secrets/db && exec my-app-server
```

---

## Kubernetes External Secrets Operator

```yaml
# SecretStore — connects to AWS Secrets Manager
apiVersion: external-secrets.io/v1beta1
kind: ClusterSecretStore
metadata:
  name: aws-secrets-manager
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: external-secrets
---
# ExternalSecret — sync a specific secret
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-credentials
    creationPolicy: Owner
    template:
      type: Opaque
  data:
    - secretKey: DB_PASSWORD
      remoteRef:
        key: prod/my-app/db-credentials
        property: password
    - secretKey: DB_USERNAME
      remoteRef:
        key: prod/my-app/db-credentials
        property: username
```

---

## Secret Rotation Patterns

```python
import logging
import boto3
import json

logger = logging.getLogger(__name__)

sm = boto3.client("secretsmanager")


def lambda_handler(event: dict, context) -> None:
    """
    AWS Secrets Manager rotation Lambda.
    Steps: createSecret → setSecret → testSecret → finishSecret
    """
    arn = event["SecretId"]
    token = event["ClientRequestToken"]
    step = event["Step"]

    logger.info("Rotation step", extra={"step": step, "arn": arn})

    if step == "createSecret":
        _create_secret(sm, arn, token)
    elif step == "setSecret":
        _set_secret(sm, arn, token)
    elif step == "testSecret":
        _test_secret(sm, arn, token)
    elif step == "finishSecret":
        _finish_secret(sm, arn, token)
    else:
        raise ValueError(f"Invalid step: {step}")


def _create_secret(sm, arn: str, token: str) -> None:
    """Generate and store new credentials as AWSPENDING."""
    import random, string
    new_password = "".join(random.choices(string.ascii_letters + string.digits, k=32))

    current = json.loads(sm.get_secret_value(SecretId=arn)["SecretString"])
    current["password"] = new_password

    sm.put_secret_value(
        SecretId=arn,
        ClientRequestToken=token,
        SecretString=json.dumps(current),
        VersionStages=["AWSPENDING"],
    )
    logger.info("New password staged as AWSPENDING", extra={"arn": arn})


def _set_secret(sm, arn: str, token: str) -> None:
    """Apply the new credentials to the database."""
    pending = json.loads(
        sm.get_secret_value(SecretId=arn, VersionStage="AWSPENDING")["SecretString"]
    )
    # Update the database password using current creds, set to pending
    logger.info("Applying new password to database", extra={"arn": arn})
    # ... actual DB ALTER USER statement here ...


def _test_secret(sm, arn: str, token: str) -> None:
    """Verify the new credentials work."""
    pending = json.loads(
        sm.get_secret_value(SecretId=arn, VersionStage="AWSPENDING")["SecretString"]
    )
    # Test a DB connection with pending credentials
    logger.info("Testing new credentials", extra={"arn": arn})
    # ... test connection ...


def _finish_secret(sm, arn: str, token: str) -> None:
    """Promote AWSPENDING to AWSCURRENT."""
    metadata = sm.describe_secret(SecretId=arn)
    current_version = next(
        v for v, stages in metadata["VersionIdsToStages"].items()
        if "AWSCURRENT" in stages
    )
    sm.update_secret_version_stage(
        SecretId=arn,
        VersionStage="AWSCURRENT",
        MoveToVersionId=token,
        RemoveFromVersionId=current_version,
    )
    logger.info("Rotation complete — AWSPENDING promoted to AWSCURRENT", extra={"arn": arn})
```

---

## References

- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/)
- [HashiCorp Vault](https://developer.hashicorp.com/vault/docs)
- [External Secrets Operator](https://external-secrets.io/)
- [Gitleaks](https://github.com/gitleaks/gitleaks)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

← [Previous: Network Security](./network-security.md) | [Home](../README.md) | [Next: Encryption →](./encryption.md)
