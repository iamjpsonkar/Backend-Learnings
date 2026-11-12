← [Previous: Cloud Tasks](../08-serverless/cloud-tasks.md) | [Home](../../README.md) | [Next: Secret Manager →](./secret-manager.md)

---

# GCP Security

---

## Service Overview

| Service | AWS Equivalent | Purpose |
|---------|----------------|---------|
| **Secret Manager** | Secrets Manager | Store and access secrets — API keys, passwords, certs |
| **Cloud KMS** | KMS | Manage cryptographic keys — CMEK for GCP services |
| **Security Command Center** | Security Hub + GuardDuty | Security posture, threat detection, vulnerability findings |
| **Cloud Armor** | WAF + Shield Advanced | DDoS protection + Web Application Firewall |
| **VPC Service Controls** | — | API-level perimeter to prevent data exfiltration |
| **Binary Authorization** | — | Policy enforcement for container image deployments |
| **Access Context Manager** | — | Attribute-based access control (device posture, IP) |

---

## Secret Manager

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"
SA_EMAIL="api-backend@${PROJECT_ID}.iam.gserviceaccount.com"

# Create a secret
gcloud secrets create api-database-password \
    --project=$PROJECT_ID \
    --replication-policy=automatic \
    --labels=service=my-app,environment=production

# Add a secret version (the actual value)
echo -n "Str0ngP@ssw0rd!" | gcloud secrets versions add api-database-password \
    --project=$PROJECT_ID \
    --data-file=-

# Or from a file
gcloud secrets versions add api-database-password \
    --project=$PROJECT_ID \
    --data-file=./secret.txt

# Access a secret (retrieve the value)
gcloud secrets versions access latest \
    --secret=api-database-password \
    --project=$PROJECT_ID

# Access a specific version
gcloud secrets versions access 3 \
    --secret=api-database-password \
    --project=$PROJECT_ID

# List secret versions
gcloud secrets versions list api-database-password \
    --project=$PROJECT_ID \
    --format="table(name,state,createTime)"

# Disable an old version (does not delete)
gcloud secrets versions disable 1 \
    --secret=api-database-password \
    --project=$PROJECT_ID

# Destroy a version (irreversible — data is gone)
gcloud secrets versions destroy 1 \
    --secret=api-database-password \
    --project=$PROJECT_ID

# Grant a service account access to read a specific secret
gcloud secrets add-iam-policy-binding api-database-password \
    --project=$PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

# List all secrets
gcloud secrets list \
    --project=$PROJECT_ID \
    --format="table(name,replication.automatic,createTime)"
```

### Python SDK — Secret Manager

```python
import logging
import os
from functools import lru_cache
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

_secret_client = secretmanager.SecretManagerServiceClient()
_project_id = os.environ["GCP_PROJECT_ID"]


@lru_cache(maxsize=None)
def get_secret(secret_name: str, version: str = "latest") -> str:
    """Retrieve a secret from Secret Manager with process-lifetime caching."""
    name = f"projects/{_project_id}/secrets/{secret_name}/versions/{version}"
    logger.info("Fetching secret: secret=%s version=%s", secret_name, version)
    try:
        response = _secret_client.access_secret_version(request={"name": name})
        logger.debug("Secret retrieved: secret=%s version=%s", secret_name, version)
        return response.payload.data.decode("utf-8")
    except Exception as e:
        logger.error("Failed to retrieve secret: secret=%s version=%s error=%s",
                     secret_name, version, str(e))
        raise
```

---

## Cloud KMS

Cloud KMS manages encryption keys used to encrypt data at rest (CMEK) or for application-level encryption.

```bash
# Create a key ring
gcloud kms keyrings create my-app-prod \
    --project=$PROJECT_ID \
    --location=us-central1

# Create a symmetric encryption key (ENCRYPT_DECRYPT)
gcloud kms keys create my-app-data-key \
    --project=$PROJECT_ID \
    --location=us-central1 \
    --keyring=my-app-prod \
    --purpose=encryption \
    --rotation-period=90d \
    --next-rotation-time=$(date -u -v+1d +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d '+1 day' +"%Y-%m-%dT%H:%M:%SZ") \
    --labels=environment=production

# Create an asymmetric signing key (e.g., for JWT signing)
gcloud kms keys create my-app-signing-key \
    --project=$PROJECT_ID \
    --location=us-central1 \
    --keyring=my-app-prod \
    --purpose=asymmetric-signing \
    --default-algorithm=rsa-sign-pkcs1-4096-sha256

# Grant a service account permission to use the key
gcloud kms keys add-iam-policy-binding my-app-data-key \
    --project=$PROJECT_ID \
    --location=us-central1 \
    --keyring=my-app-prod \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudkms.cryptoKeyEncrypterDecrypter"

# Encrypt data using the CLI
echo -n "sensitive data" | gcloud kms encrypt \
    --project=$PROJECT_ID \
    --location=us-central1 \
    --keyring=my-app-prod \
    --key=my-app-data-key \
    --plaintext-file=- \
    --ciphertext-file=encrypted.bin

# Decrypt
gcloud kms decrypt \
    --project=$PROJECT_ID \
    --location=us-central1 \
    --keyring=my-app-prod \
    --key=my-app-data-key \
    --ciphertext-file=encrypted.bin \
    --plaintext-file=-

# Use CMEK with Cloud Storage
gcloud storage buckets update gs://${PROJECT_ID}-sensitive \
    --default-encryption-key=projects/$PROJECT_ID/locations/us-central1/keyRings/my-app-prod/cryptoKeys/my-app-data-key
```

---

## Security Command Center

Security Command Center (SCC) provides continuous security posture assessment, threat detection, and vulnerability findings across your GCP organization.

```bash
# List all active findings (requires Organization-level SCC)
gcloud scc findings list ORGANIZATION_ID \
    --filter="state=ACTIVE AND severity=HIGH OR severity=CRITICAL" \
    --format="table(name,category,resourceName,severity,eventTime)"

# List findings for a specific project
gcloud scc findings list ORGANIZATION_ID \
    --source=- \
    --filter="state=ACTIVE AND resourceName:my-app-production" \
    --format="table(category,resourceName,severity)"

# Mark a finding as muted (suppressed)
gcloud scc findings update FINDING_NAME \
    --organization=ORGANIZATION_ID \
    --mute=MUTED

# List security health analytics findings
gcloud scc findings list ORGANIZATION_ID \
    --source=SECURITY_HEALTH_ANALYTICS_SOURCE_ID \
    --filter="state=ACTIVE" \
    --format="table(category,resourceName,severity,eventTime)"
```

---

## Cloud Armor (WAF + DDoS)

```bash
# Create a security policy
gcloud compute security-policies create armor-my-app-prod \
    --project=$PROJECT_ID \
    --description="WAF policy for My App production"

# Allow traffic only from specific countries (geo-restriction)
gcloud compute security-policies rules create 1000 \
    --project=$PROJECT_ID \
    --security-policy=armor-my-app-prod \
    --expression="origin.region_code == 'CN' || origin.region_code == 'RU'" \
    --action=deny-403 \
    --description="Block high-risk geographies"

# Enable OWASP Top 10 managed rule set (Cloud Armor Managed Protection Plus)
gcloud compute security-policies rules create 2000 \
    --project=$PROJECT_ID \
    --security-policy=armor-my-app-prod \
    --expression="evaluatePreconfiguredExpr('xss-v33-stable')" \
    --action=deny-403

gcloud compute security-policies rules create 2001 \
    --project=$PROJECT_ID \
    --security-policy=armor-my-app-prod \
    --expression="evaluatePreconfiguredExpr('sqli-v33-stable')" \
    --action=deny-403

# Rate limit: block IPs exceeding 100 requests per minute
gcloud compute security-policies rules create 3000 \
    --project=$PROJECT_ID \
    --security-policy=armor-my-app-prod \
    --expression="true" \
    --action=rate-based-ban \
    --rate-limit-threshold-count=100 \
    --rate-limit-threshold-interval-sec=60 \
    --ban-duration-sec=300 \
    --conform-action=allow \
    --exceed-action=deny-429 \
    --enforce-on-key=IP

# Attach the policy to a backend service
gcloud compute backend-services update bs-my-app \
    --project=$PROJECT_ID \
    --global \
    --security-policy=armor-my-app-prod

# List rules
gcloud compute security-policies rules list armor-my-app-prod \
    --project=$PROJECT_ID
```

---

## VPC Service Controls

VPC Service Controls create a perimeter around GCP APIs to prevent data exfiltration (e.g., copying data to a bucket outside the org).

```bash
# Requires Access Context Manager and Organization-level permissions

# Create an access policy (once per org)
gcloud access-context-manager policies create \
    --organization=ORGANIZATION_ID \
    --title="My Org Access Policy"

POLICY_NAME=$(gcloud access-context-manager policies list \
    --organization=ORGANIZATION_ID \
    --format="value(name)")

# Create a service perimeter
gcloud access-context-manager perimeters create my-app-perimeter \
    --policy=$POLICY_NAME \
    --title="My App Perimeter" \
    --resources=projects/$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)") \
    --restricted-services=storage.googleapis.com,bigquery.googleapis.com,sqladmin.googleapis.com
```

---

## Binary Authorization

Binary Authorization ensures only verified, signed container images can be deployed to GKE or Cloud Run.

```bash
# Enable Binary Authorization
gcloud services enable binaryauthorization.googleapis.com --project=$PROJECT_ID

# Get the default policy
gcloud container binauthz policy export --project=$PROJECT_ID

# Set policy to require attestation
gcloud container binauthz policy import policy.yaml --project=$PROJECT_ID
```

```yaml
# policy.yaml — require all images to be attested before deployment
admissionWhitelistPatterns:
  - namePattern: gcr.io/google-containers/**
  - namePattern: gke.gcr.io/**
defaultAdmissionRule:
  evaluationMode: REQUIRE_ATTESTATION
  enforcementMode: ENFORCED_BLOCK_AND_AUDIT_LOG
  requireAttestationsBy:
    - projects/my-app-production/attestors/production-deployer
globalPolicyEvaluationMode: ENABLE
```

---

## Security Best Practices Checklist

- [ ] Enable Security Command Center at the organization level
- [ ] Use Workload Identity Federation instead of service account keys
- [ ] Rotate service account keys quarterly if keys are unavoidable
- [ ] Apply organization policy constraints: no public IPs, uniform bucket access, OS Login
- [ ] Restrict API access with VPC Service Controls for sensitive projects
- [ ] Attach Cloud Armor to all public-facing load balancers
- [ ] Grant secrets access at the individual secret level (not project-wide)
- [ ] Enable Cloud KMS CMEK for Cloud Storage, BigQuery, and Cloud SQL
- [ ] Audit IAM bindings regularly — remove `roles/owner` and `roles/editor` from individuals

---

## References

- [Secret Manager documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud KMS documentation](https://cloud.google.com/kms/docs)
- [Security Command Center](https://cloud.google.com/security-command-center/docs)
- [Cloud Armor documentation](https://cloud.google.com/armor/docs)
- [VPC Service Controls](https://cloud.google.com/vpc-service-controls/docs)
---

← [Previous: Cloud Tasks](../08-serverless/cloud-tasks.md) | [Home](../../README.md) | [Next: Secret Manager →](./secret-manager.md)
