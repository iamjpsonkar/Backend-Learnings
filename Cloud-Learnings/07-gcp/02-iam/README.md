← [Previous: Billing](../01-account-setup/billing.md) | [Home](../../README.md) | [Next: IAM Basics →](./iam-basics.md)

---

# GCP IAM

---

## Core Concepts

| Concept | Description |
|---------|------------|
| **Principal** | Who — a Google account, service account, Google group, or domain |
| **Role** | What — a collection of permissions (e.g., `roles/storage.objectViewer`) |
| **Policy** | Binding of principal → role at a resource scope |
| **Service Account** | A non-human identity for workloads (similar to AWS IAM role) |
| **Workload Identity Federation** | Allow external identities (GitHub, AWS, etc.) to impersonate a service account — no keys needed |

IAM follows the **principle of least privilege**: grant the minimum role at the narrowest scope.

---

## Role Types

| Type | Description | Example |
|------|-------------|---------|
| **Basic** | Coarse-grained legacy roles — avoid in production | `roles/owner`, `roles/editor`, `roles/viewer` |
| **Predefined** | Service-specific roles — recommended | `roles/storage.objectViewer`, `roles/run.invoker` |
| **Custom** | User-defined — combine specific permissions | `roles/my-app.apiReader` |

```bash
PROJECT_ID="my-app-production"

# List all predefined roles for a service
gcloud iam roles list --filter="name:roles/storage" --format="table(name,title)"

# Describe a role (see its permissions)
gcloud iam roles describe roles/storage.objectAdmin
```

---

## Granting Roles

```bash
# Grant a predefined role on a project
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:engineer@example.com" \
    --role="roles/compute.instanceAdmin.v1"

# Grant a role to a Google group
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="group:backend-team@example.com" \
    --role="roles/run.developer"

# Grant a role on a specific resource (not the whole project)
gcloud storage buckets add-iam-policy-binding gs://my-app-production-assets \
    --member="serviceAccount:api-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

# View the IAM policy for a project
gcloud projects get-iam-policy $PROJECT_ID \
    --format=json

# Remove a binding
gcloud projects remove-iam-policy-binding $PROJECT_ID \
    --member="user:contractor@example.com" \
    --role="roles/viewer"
```

---

## Custom Roles

```bash
# Create a custom role from a YAML definition
cat > my-app-api-reader.yaml <<'EOF'
title: "My App API Reader"
description: "Read-only access to My App API resources"
stage: GA
includedPermissions:
  - storage.objects.get
  - storage.objects.list
  - run.routes.invoke
  - secretmanager.versions.access
EOF

gcloud iam roles create myAppApiReader \
    --project=$PROJECT_ID \
    --file=my-app-api-reader.yaml

# Update a custom role (add permissions)
gcloud iam roles update myAppApiReader \
    --project=$PROJECT_ID \
    --add-permissions=cloudtrace.traces.patch

# List custom roles
gcloud iam roles list \
    --project=$PROJECT_ID \
    --filter="name:projects/$PROJECT_ID"
```

---

## Service Accounts

A service account is a special Google account representing a workload (a VM, a Cloud Run service, a pipeline). Never use personal accounts for automated systems.

```bash
# Create a service account
gcloud iam service-accounts create api-backend \
    --display-name="My App API Backend" \
    --description="Service account for the API backend service" \
    --project=$PROJECT_ID

SA_EMAIL="api-backend@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant the service account roles on the project
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudtrace.agent"

# List service accounts
gcloud iam service-accounts list --project=$PROJECT_ID

# Disable a service account (preferred over deletion — reversible)
gcloud iam service-accounts disable $SA_EMAIL --project=$PROJECT_ID

# Delete (irreversible after 30 days)
gcloud iam service-accounts delete $SA_EMAIL --project=$PROJECT_ID
```

### Service Account Keys (Avoid in Production)

Service account key files are long-lived credentials that can be stolen. Use Workload Identity Federation or attach service accounts to compute resources instead.

```bash
# Only use keys if absolutely necessary (e.g., legacy on-premises systems)
gcloud iam service-accounts keys create key.json \
    --iam-account=$SA_EMAIL

# Rotate: create new key, update consumers, then delete old key
gcloud iam service-accounts keys list --iam-account=$SA_EMAIL
gcloud iam service-accounts keys delete KEY_ID --iam-account=$SA_EMAIL

# Recommended: use GOOGLE_APPLICATION_CREDENTIALS only locally
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/key.json"
```

---

## Workload Identity Federation

Workload Identity Federation lets external principals (GitHub Actions, AWS IAM, Azure AD) impersonate GCP service accounts without long-lived keys.

### GitHub Actions → GCP (OIDC, no keys)

```bash
# 1. Create a Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
    --location=global \
    --description="GitHub Actions identity pool" \
    --display-name="GitHub Pool"

# 2. Create an OIDC provider for GitHub
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location=global \
    --workload-identity-pool=github-pool \
    --display-name="GitHub Actions" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor" \
    --attribute-condition="assertion.repository=='your-org/your-repo'"

# 3. Get the pool resource name
POOL_NAME=$(gcloud iam workload-identity-pools describe github-pool \
    --location=global \
    --format="value(name)")

# 4. Allow the pool to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/your-org/your-repo"

# 5. Get the provider resource name (use in GitHub Actions workflow)
gcloud iam workload-identity-pools providers describe github-provider \
    --location=global \
    --workload-identity-pool=github-pool \
    --format="value(name)"
```

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: "projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
          service_account: "api-backend@my-app-production.iam.gserviceaccount.com"
```

---

## Attaching Service Accounts to Compute Resources

```bash
# Attach service account to a Compute Engine VM
gcloud compute instances create vm-my-app-prod-001 \
    --service-account=$SA_EMAIL \
    --scopes=cloud-platform \
    --zone=us-central1-a

# Attach to a Cloud Run service
gcloud run deploy my-app-api \
    --service-account=$SA_EMAIL \
    --region=us-central1

# Attach to a GKE workload — use Workload Identity (see 07-containers/README.md)
```

---

## Organization Policies

Organization policies constrain what can be done across an org, folder, or project — regardless of IAM roles.

```bash
# List available constraints
gcloud org-policies list-available-constraints \
    --organization=123456789 \
    --format="table(name,displayName)"

# Deny public IPs on all Compute Engine instances
cat > no-public-ip-policy.yaml <<'EOF'
name: projects/my-app-production/policies/compute.vmExternalIpAccess
spec:
  rules:
  - enforce: true
EOF

gcloud org-policies set-policy no-public-ip-policy.yaml

# Require OS Login (SSH key management via IAM)
gcloud resource-manager org-policies enable-enforce \
    constraints/compute.requireOsLogin \
    --project=$PROJECT_ID
```

---

## References

- [GCP IAM overview](https://cloud.google.com/iam/docs/overview)
- [Predefined roles reference](https://cloud.google.com/iam/docs/understanding-roles)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [Service account best practices](https://cloud.google.com/iam/docs/best-practices-for-using-and-managing-service-accounts)
---

← [Previous: Billing](../01-account-setup/billing.md) | [Home](../../README.md) | [Next: IAM Basics →](./iam-basics.md)
