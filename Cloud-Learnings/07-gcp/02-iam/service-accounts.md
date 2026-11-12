← [Previous: IAM Basics](./iam-basics.md) | [Home](../../README.md) | [Next: Workload Identity Federation →](./workload-identity-federation.md)

---

# GCP Service Accounts

Service accounts are non-human identities used by applications, VMs, and GKE workloads to authenticate to GCP APIs. They are both a principal (can be granted roles) and a resource (can have IAM policies controlling who can use them).

---

## Service Account Types

| Type | Description |
|------|-------------|
| **User-managed** | You create and manage — used for your applications |
| **Default** | Auto-created per project for App Engine, Compute Engine — avoid using in production |
| **Google-managed** | Created by GCP for internal use — do not modify |

---

## Creating Service Accounts

```bash
PROJECT="my-app-prod-123456"

# Create a service account
gcloud iam service-accounts create sa-my-app \
    --display-name="My App Service Account" \
    --description="Used by my-app deployment on GKE" \
    --project=$PROJECT

# The full email format is:
# sa-my-app@my-app-prod-123456.iam.gserviceaccount.com
SA_EMAIL="sa-my-app@$PROJECT.iam.gserviceaccount.com"

# Grant the service account permissions
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudtrace.agent"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/monitoring.metricWriter"

gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/logging.logWriter"

# List service accounts in a project
gcloud iam service-accounts list \
    --project=$PROJECT \
    --format="table(email,displayName,disabled)"

# Describe a service account
gcloud iam service-accounts describe $SA_EMAIL \
    --project=$PROJECT
```

---

## Service Account Keys (Avoid When Possible)

Key files are a security risk — prefer Workload Identity or service account impersonation instead. Use keys only for accessing GCP from outside GCP.

```bash
# Create a key file (use only when Workload Identity is not available)
gcloud iam service-accounts keys create key.json \
    --iam-account=$SA_EMAIL \
    --project=$PROJECT

# IMMEDIATELY store key.json in a secret manager — never commit to git
# Use it:
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/key.json"

# List keys for a service account
gcloud iam service-accounts keys list \
    --iam-account=$SA_EMAIL \
    --project=$PROJECT \
    --format="table(name.basename(),validAfterTime,validBeforeTime,keyType)"

# Rotate a key: create new, update application, delete old
gcloud iam service-accounts keys create new-key.json --iam-account=$SA_EMAIL
# ... update app to use new-key.json ...
gcloud iam service-accounts keys delete OLD_KEY_ID --iam-account=$SA_EMAIL --quiet

# Disable a key without deleting (reversible)
gcloud iam service-accounts keys disable KEY_ID \
    --iam-account=$SA_EMAIL \
    --project=$PROJECT
```

---

## Service Account Impersonation

Instead of key files, let a principal (user or another SA) impersonate a service account.

```bash
# Grant a user the ability to impersonate a service account
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --member="user:developer@example.com" \
    --role="roles/iam.serviceAccountTokenCreator"

# Grant a CI/CD service account to impersonate the deployment SA
gcloud iam service-accounts add-iam-policy-binding sa-deploy@$PROJECT.iam.gserviceaccount.com \
    --member="serviceAccount:sa-cicd@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountTokenCreator"

# Use impersonation with gcloud
gcloud compute instances list \
    --impersonate-service-account=$SA_EMAIL \
    --project=$PROJECT

# Use impersonation in code (Python)
# from google.auth import impersonated_credentials
# target_credentials = impersonated_credentials.Credentials(
#     source_credentials=source_creds,
#     target_principal=SA_EMAIL,
#     target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
# )
```

---

## Attaching Service Accounts to Compute Resources

```bash
# Attach SA to a VM at creation (VM can call GCP APIs as this SA)
gcloud compute instances create my-vm \
    --zone=us-central1-a \
    --machine-type=n2-standard-2 \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \  # Full access to all APIs the SA has permissions for
    --image-family=debian-12 \
    --image-project=debian-cloud

# Change SA on existing VM (requires stopping VM)
gcloud compute instances stop my-vm --zone=us-central1-a
gcloud compute instances set-service-account my-vm \
    --zone=us-central1-a \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform
gcloud compute instances start my-vm --zone=us-central1-a

# Attach SA to Cloud Run service
gcloud run deploy my-service \
    --image=gcr.io/$PROJECT/my-app:latest \
    --service-account=$SA_EMAIL \
    --region=us-central1
```

---

## Best Practices

```bash
# 1. One SA per application (principle of least privilege)
# Bad: one SA for all services
# Good: sa-web@project, sa-worker@project, sa-db-proxy@project

# 2. Disable unused SAs (don't delete — helps with audit trail)
gcloud iam service-accounts disable $SA_EMAIL --project=$PROJECT

# 3. Set up org policy to restrict SA key creation
gcloud org-policies set-policy - <<EOF
name: projects/$PROJECT/policies/iam.disableServiceAccountKeyCreation
spec:
  rules:
    - enforce: true
EOF

# 4. Monitor SA key age — alert if key > 90 days old
gcloud iam service-accounts keys list \
    --iam-account=$SA_EMAIL \
    --managed-by=USER \
    --format="table(name.basename(),validAfterTime)" \
    --project=$PROJECT

# 5. Use workload identity for GKE instead of key files (see workload-identity-federation.md)
```

---

## Python — Application Default Credentials

```python
import os
import logging
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import google.auth

logger = logging.getLogger(__name__)

def get_credentials():
    """
    Get credentials using Application Default Credentials (ADC).
    ADC automatically uses:
    1. GOOGLE_APPLICATION_CREDENTIALS env var (key file)
    2. gcloud auth application-default login (local dev)
    3. Attached service account (Compute Engine, GKE, Cloud Run, etc.)
    4. gcloud user credentials as fallback
    """
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    logger.info("Credentials loaded", extra={"project": project, "type": type(credentials).__name__})
    return credentials, project


def get_service_account_credentials(sa_email: str, scopes: list[str]) -> service_account.Credentials:
    """Get credentials by impersonating a service account (no key file needed)."""
    from google.auth import impersonated_credentials

    source_credentials, _ = google.auth.default()
    target_credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=sa_email,
        target_scopes=scopes,
        lifetime=3600,
    )
    logger.info("Impersonating service account", extra={"sa_email": sa_email})
    return target_credentials
```

---

## References

- [Service accounts overview](https://cloud.google.com/iam/docs/service-accounts)
- [Service account best practices](https://cloud.google.com/iam/docs/best-practices-for-using-and-managing-service-accounts)
- [Impersonation](https://cloud.google.com/iam/docs/create-short-lived-credentials-direct)

---

← [Previous: IAM Basics](./iam-basics.md) | [Home](../../README.md) | [Next: Workload Identity Federation →](./workload-identity-federation.md)
