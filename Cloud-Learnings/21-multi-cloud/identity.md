← [Previous: Networking](./networking.md) | [Home](../README.md) | [Next: Data Replication →](./data-replication.md)

---

# Cross-Cloud Identity

The core problem in multi-cloud identity: your workloads on AWS need to call GCP APIs (or vice versa) without storing long-lived credentials. The solution is Workload Identity Federation using OIDC — each cloud trusts the other's identity tokens.

---

## Cross-Cloud OIDC Federation

### Architecture

```
AWS Workload (EC2/ECS/Lambda)          GCP Workload
        │                                    │
        │  1. Get OIDC token from            │  1. Get OIDC token from
        │     EC2 IMDS or STS               │     GCE metadata server
        │                                   │
        ▼                                   ▼
   AWS STS                            GCP STS
   (OIDC issuer)                      (OIDC issuer)
        │                                   │
        │  2. Token exchanged for            │  2. Token exchanged for
        │     GCP credentials               │     AWS credentials
        ▼                                   ▼
   GCP Workload Identity           AWS IAM Role (via STS AssumeRoleWithWebIdentity)
   Pool + Provider
        │                                   │
        ▼                                   ▼
   GCP service calls                AWS service calls
```

### AWS → GCP: Allow AWS Workloads to Call GCP APIs

```bash
# On GCP: Create a Workload Identity Pool
gcloud iam workload-identity-pools create aws-pool \
    --location global \
    --display-name "AWS Workload Identity Pool" \
    --description "Allows AWS workloads to authenticate to GCP"

# Create a provider within the pool (trusts AWS STS)
gcloud iam workload-identity-pools providers create-aws \
    aws-provider \
    --location global \
    --workload-identity-pool aws-pool \
    --account-id $AWS_ACCOUNT_ID \
    --attribute-mapping \
        "google.subject=assertion.arn,
         attribute.aws_role=assertion.arn.extract('assumed-role/{role}/'),
         attribute.aws_account=assertion.account"

# Grant a specific AWS IAM role access to a GCP service account
# "The AWS role arn:aws:iam::ACCOUNT:assumed-role/my-role/* can impersonate gcp-svc-account"
gcloud iam service-accounts add-iam-policy-binding \
    gcp-analytics@my-project.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "principalSet://iam.googleapis.com/projects/$GCP_PROJECT_NUMBER/locations/global/workloadIdentityPools/aws-pool/attribute.aws_role/my-role"

# Grant the GCP service account the permissions it needs
gcloud projects add-iam-policy-binding my-project \
    --role roles/bigquery.dataViewer \
    --member serviceAccount:gcp-analytics@my-project.iam.gserviceaccount.com
```

```python
# AWS workload calling GCP APIs using Workload Identity Federation

import logging
import boto3
import google.auth
from google.auth import aws as google_auth_aws
from google.cloud import bigquery

logger = logging.getLogger(__name__)


def get_gcp_credentials_from_aws(
    project_id: str,
    pool_id: str,
    provider_id: str,
    service_account: str,
) -> google.auth.credentials.Credentials:
    """
    Exchange AWS credentials for GCP credentials using Workload Identity Federation.
    No long-lived keys stored anywhere.
    """
    logger.info("Exchanging AWS credentials for GCP credentials", extra={
        "project_id": project_id,
        "pool_id": pool_id,
        "service_account": service_account,
    })

    # Build credential configuration (this would normally come from a downloaded JSON file)
    credential_config = {
        "type": "external_account",
        "audience": (
            f"//iam.googleapis.com/projects/{project_id}/locations/global/"
            f"workloadIdentityPools/{pool_id}/providers/{provider_id}"
        ),
        "subject_token_type": "urn:ietf:params:aws:token-type:aws4_request",
        "token_url": "https://sts.googleapis.com/v1/token",
        "credential_source": {
            "environment_id": "aws1",
            "region_url": "http://169.254.169.254/latest/meta-data/placement/availability-zone",
            "url": "http://169.254.169.254/latest/meta-data/iam/security-credentials",
            "regional_cred_verification_url": (
                "https://sts.{region}.amazonaws.com?Action=GetCallerIdentity&Version=2011-06-15"
            ),
        },
        "service_account_impersonation_url": (
            f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
            f"{service_account}:generateAccessToken"
        ),
        "scopes": ["https://www.googleapis.com/auth/cloud-platform"],
    }

    credentials, _ = google.auth.load_credentials_from_dict(credential_config)
    logger.info("GCP credentials obtained successfully")
    return credentials


def query_bigquery_from_aws(sql: str, request_id: str) -> list[dict]:
    """Run a BigQuery query from an AWS workload without stored GCP keys."""
    logger.info("Running BigQuery query from AWS workload", extra={"request_id": request_id})

    credentials = get_gcp_credentials_from_aws(
        project_id=os.environ["GCP_PROJECT_ID"],
        pool_id="aws-pool",
        provider_id="aws-provider",
        service_account="gcp-analytics@my-project.iam.gserviceaccount.com",
    )

    client = bigquery.Client(
        project=os.environ["GCP_PROJECT_ID"],
        credentials=credentials,
    )

    query_job = client.query(sql)
    results = [dict(row) for row in query_job.result()]

    logger.info("BigQuery query completed", extra={
        "request_id": request_id,
        "row_count": len(results),
    })
    return results
```

---

### GCP → AWS: Allow GCP Workloads to Call AWS APIs

```python
# GCP workload calling AWS APIs using STS AssumeRoleWithWebIdentity

import logging
import os

import boto3
import google.auth
import google.auth.transport.requests

logger = logging.getLogger(__name__)


def get_aws_credentials_from_gcp(aws_role_arn: str, session_name: str) -> dict:
    """
    Exchange GCP identity token for temporary AWS credentials.
    Runs on GCP compute — no AWS access keys stored.
    """
    logger.info("Exchanging GCP identity for AWS credentials", extra={
        "role_arn": aws_role_arn,
        "session_name": session_name,
    })

    # Get GCP OIDC token from metadata server
    credentials, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)

    id_token = credentials.token
    logger.debug("GCP identity token obtained")

    # Exchange for AWS credentials
    sts = boto3.client("sts", region_name="us-east-1")
    response = sts.assume_role_with_web_identity(
        RoleArn=aws_role_arn,
        RoleSessionName=session_name,
        WebIdentityToken=id_token,
        DurationSeconds=3600,
    )

    creds = response["Credentials"]
    logger.info("AWS credentials obtained via OIDC exchange", extra={
        "role_arn": aws_role_arn,
        "expiration": str(creds["Expiration"]),
    })
    return creds


def call_aws_s3_from_gcp(bucket: str, key: str, request_id: str) -> bytes:
    """Download from S3 using GCP-federated credentials."""
    aws_creds = get_aws_credentials_from_gcp(
        aws_role_arn=os.environ["AWS_ROLE_ARN"],
        session_name=f"gcp-workload-{request_id}",
    )

    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_creds["AccessKeyId"],
        aws_secret_access_key=aws_creds["SecretAccessKey"],
        aws_session_token=aws_creds["SessionToken"],
    )

    response = s3.get_object(Bucket=bucket, Key=key)
    data = response["Body"].read()

    logger.info("S3 download complete", extra={
        "bucket": bucket, "key": key,
        "size": len(data), "request_id": request_id,
    })
    return data
```

```bash
# On AWS: create IAM role trusted by GCP via OIDC
# GCP OIDC issuer: https://accounts.google.com

cat > gcp-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Federated": "accounts.google.com"},
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
            "StringEquals": {
                "accounts.google.com:aud": "aws-cross-cloud-role",
                "accounts.google.com:sub": "$GCP_SERVICE_ACCOUNT_UNIQUE_ID"
            }
        }
    }]
}
EOF

aws iam create-role \
    --role-name gcp-workload-role \
    --assume-role-policy-document file://gcp-trust-policy.json

# Attach permissions for what GCP workloads need to do on AWS
aws iam attach-role-policy \
    --role-name gcp-workload-role \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

---

## Centralized Identity with Azure Entra ID

When your organization uses Azure Entra ID (formerly Azure AD) as the primary identity provider, federate it to both AWS and GCP.

```bash
# AWS: Create SAML provider for Entra ID SSO
aws iam create-saml-provider \
    --saml-metadata-document file://azure-ad-metadata.xml \
    --name AzureAD

# Create IAM role for Entra ID-authenticated users
cat > azure-ad-trust.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Federated": "arn:aws:iam::123456789012:saml-provider/AzureAD"
        },
        "Action": "sts:AssumeRoleWithSAML",
        "Condition": {
            "StringEquals": {
                "SAML:aud": "https://signin.aws.amazon.com/saml"
            }
        }
    }]
}
EOF

aws iam create-role \
    --role-name AzureAD-DevOps-Engineer \
    --assume-role-policy-document file://azure-ad-trust.json

aws iam attach-role-policy \
    --role-name AzureAD-DevOps-Engineer \
    --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

```bash
# GCP: Federate Entra ID using OIDC
gcloud iam workload-identity-pools create azure-pool \
    --location global \
    --display-name "Azure Entra ID Pool"

gcloud iam workload-identity-pools providers create-oidc \
    azure-provider \
    --location global \
    --workload-identity-pool azure-pool \
    --issuer-uri "https://login.microsoftonline.com/$TENANT_ID/v2.0" \
    --allowed-audiences "api://AzureADTokenExchange" \
    --attribute-mapping "google.subject=assertion.sub,attribute.groups=assertion.groups"
```

---

## Secrets Management Across Clouds

```python
"""
Multi-cloud secret retrieval with provider abstraction.
"""
import logging
import os
from abc import ABC, abstractmethod
from functools import lru_cache

logger = logging.getLogger(__name__)


class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self, name: str) -> str: ...


class AWSSecretProvider(SecretProvider):
    def __init__(self):
        import boto3
        self._client = boto3.client("secretsmanager")

    @lru_cache(maxsize=64)
    def get_secret(self, name: str) -> str:
        logger.debug("Fetching secret from AWS Secrets Manager", extra={"name": name})
        response = self._client.get_secret_value(SecretId=name)
        return response["SecretString"]


class GCPSecretProvider(SecretProvider):
    def __init__(self, project_id: str):
        from google.cloud import secretmanager
        self._client = secretmanager.SecretManagerServiceClient()
        self._project = project_id

    @lru_cache(maxsize=64)
    def get_secret(self, name: str) -> str:
        logger.debug("Fetching secret from GCP Secret Manager", extra={"name": name})
        secret_name = f"projects/{self._project}/secrets/{name}/versions/latest"
        response = self._client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")


def get_secret_provider() -> SecretProvider:
    """Instantiate the correct provider based on runtime environment."""
    cloud = os.environ.get("CLOUD_PROVIDER", "aws").lower()
    if cloud == "aws":
        return AWSSecretProvider()
    elif cloud == "gcp":
        return GCPSecretProvider(project_id=os.environ["GCP_PROJECT_ID"])
    else:
        raise ValueError(f"Unknown CLOUD_PROVIDER: {cloud}")
```

---

## References

- [GCP Workload Identity Federation for AWS](https://cloud.google.com/iam/docs/workload-identity-federation-with-aws)
- [AWS AssumeRoleWithWebIdentity](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html)
- [Azure Entra ID with AWS](https://learn.microsoft.com/en-us/azure/active-directory/saas-apps/amazon-web-service-tutorial)

---

← [Previous: Networking](./networking.md) | [Home](../README.md) | [Next: Data Replication →](./data-replication.md)
