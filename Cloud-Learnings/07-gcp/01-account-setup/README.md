← [Previous: GCP](../README.md) | [Home](../../README.md) | [Next: gcloud CLI →](./gcloud.md)

---

# GCP Account Setup

---

## gcloud CLI

```bash
# Install gcloud (macOS via Homebrew)
brew install --cask google-cloud-sdk

# Initialize — authenticates and selects a project
gcloud init

# Authenticate as yourself (browser-based)
gcloud auth login

# Application Default Credentials — for local development / SDKs
gcloud auth application-default login

# List accounts and active account
gcloud auth list

# Set active account
gcloud config set account your-email@example.com

# Show active configuration
gcloud config list
```

---

## Projects

A **project** is the primary isolation boundary in GCP. Every resource belongs to a project, and billing, quotas, and IAM are all scoped to projects.

```bash
# List all accessible projects
gcloud projects list

# Create a new project
gcloud projects create my-app-production \
    --name="My App Production" \
    --organization=123456789  # optional — org ID from `gcloud organizations list`

# Set the active project for all subsequent commands
gcloud config set project my-app-production

# Describe a project
gcloud projects describe my-app-production

# Get project number (needed for some APIs and IAM)
gcloud projects describe my-app-production \
    --format="value(projectNumber)"
```

### Enable Required APIs

GCP APIs are disabled by default per project. Always enable the APIs your workloads need.

```bash
PROJECT_ID="my-app-production"

gcloud services enable \
    compute.googleapis.com \
    container.googleapis.com \
    run.googleapis.com \
    cloudfunctions.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudkms.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    cloudtrace.googleapis.com \
    errorreporting.googleapis.com \
    iam.googleapis.com \
    iamcredentials.googleapis.com \
    --project=$PROJECT_ID

# List enabled APIs
gcloud services list --enabled --project=$PROJECT_ID
```

---

## Billing

```bash
# List billing accounts
gcloud billing accounts list

# Link a billing account to a project
gcloud billing projects link my-app-production \
    --billing-account=012345-ABCDEF-123456

# Verify billing is enabled
gcloud billing projects describe my-app-production
```

### Budget Alerts

Set budgets in the Cloud Console (Billing → Budgets & Alerts) or via the Billing API. Budgets can trigger Pub/Sub notifications for automated cost control.

---

## Multiple Configurations (Named Profiles)

```bash
# Create a named configuration for a project + account
gcloud config configurations create my-app-prod
gcloud config set account prod-engineer@example.com
gcloud config set project my-app-production
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a

# Switch between configurations
gcloud config configurations activate my-app-prod
gcloud config configurations activate default

# List all configurations
gcloud config configurations list
```

---

## Regions and Zones

```bash
# List all regions
gcloud compute regions list

# List zones in a region
gcloud compute zones list --filter="region:us-central1"

# Recommended default regions
# us-central1 (Iowa) — low cost, broad service availability
# us-east1 (South Carolina)
# europe-west1 (Belgium)
# asia-southeast1 (Singapore)
```

---

## Resource Hierarchy Setup

```bash
# List organizations (requires Cloud Identity or Workspace)
gcloud organizations list

# Create folders for environment separation
gcloud resource-manager folders create \
    --display-name="Production" \
    --organization=123456789

gcloud resource-manager folders create \
    --display-name="Non-Production" \
    --organization=123456789

# Create a project inside a folder
gcloud projects create my-app-staging \
    --name="My App Staging" \
    --folder=FOLDER_ID
```

---

## Naming Conventions

| Resource | Pattern | Example |
|----------|---------|---------|
| Project | `{app}-{env}` | `my-app-production` |
| VPC | `vpc-{app}-{env}` | `vpc-my-app-prod` |
| Subnet | `snet-{tier}-{region}` | `snet-app-us-central1` |
| GKE Cluster | `gke-{app}-{env}-{region}` | `gke-my-app-prod-us-central1` |
| Cloud Run | `{app}-{service}-{env}` | `my-app-api-prod` |
| Service Account | `{role}@{project}.iam.gserviceaccount.com` | `api-backend@my-app-prod.iam.gserviceaccount.com` |
| Secret | `{service}-{key}` | `api-database-password` |
| Bucket | `{project-id}-{purpose}` | `my-app-production-assets` |

---

## Account Safety Checklist

- [ ] Enable 2-step verification on all Google accounts that access GCP
- [ ] Assign the Organization Admin role to a group, not an individual
- [ ] Enable organization policy constraints (e.g., restrict public IPs, enforce uniform bucket access)
- [ ] Configure a billing budget alert at 80% and 100% of expected spend
- [ ] Enable the Security Command Center (Standard tier is free)
- [ ] Never use the default Compute Engine service account for production workloads
- [ ] Enable VPC Service Controls for sensitive projects
- [ ] Rotate service account keys regularly — prefer Workload Identity Federation (no keys at all)

---

## References

- [gcloud CLI reference](https://cloud.google.com/sdk/gcloud/reference)
- [GCP resource hierarchy](https://cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy)
- [GCP regions and zones](https://cloud.google.com/compute/docs/regions-zones)
---

← [Previous: GCP](../README.md) | [Home](../../README.md) | [Next: gcloud CLI →](./gcloud.md)
