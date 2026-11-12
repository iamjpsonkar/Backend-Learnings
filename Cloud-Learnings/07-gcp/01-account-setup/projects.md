← [Previous: gcloud CLI](./gcloud.md) | [Home](../../README.md) | [Next: Billing →](./billing.md)

---

# GCP Projects and Resource Hierarchy

GCP organizes resources in a three-tier hierarchy: Organization → Folders → Projects → Resources. Policies and IAM bindings applied at higher levels cascade down.

---

## Resource Hierarchy

```
Organization (example.com)
  │
  ├── Folder: Production
  │     ├── Project: my-app-prod (ID: my-app-prod-123456)
  │     │     ├── Compute Engine VMs
  │     │     ├── Cloud Storage buckets
  │     │     └── Cloud SQL instances
  │     └── Project: data-prod (ID: data-prod-789012)
  │
  ├── Folder: Development
  │     └── Project: my-app-dev (ID: my-app-dev-345678)
  │
  └── Project: shared-services (networking, CI/CD)
```

**Key rule**: A project is the fundamental unit of isolation — billing, quota, IAM, and API enablement are all per-project.

---

## Creating and Managing Projects

```bash
# Create a project (project ID must be globally unique, 6–30 chars, lowercase)
gcloud projects create my-app-prod-123456 \
    --name="My App Production" \
    --folder=FOLDER_ID \
    --labels=environment=production,team=platform

# Set as the default project
gcloud config set project my-app-prod-123456

# List projects
gcloud projects list \
    --format="table(projectId,name,projectNumber,lifecycleState)" \
    --filter="lifecycleState=ACTIVE"

# Get project details (including project number, needed for some APIs)
gcloud projects describe my-app-prod-123456 \
    --format="json(projectId,name,projectNumber,labels)"

# Move project to a different folder
gcloud projects move my-app-prod-123456 \
    --folder=NEW_FOLDER_ID
```

---

## Enabling APIs

Every GCP service API must be explicitly enabled per project.

```bash
PROJECT="my-app-prod-123456"

# Enable individual APIs
gcloud services enable compute.googleapis.com --project $PROJECT
gcloud services enable container.googleapis.com --project $PROJECT
gcloud services enable sqladmin.googleapis.com --project $PROJECT
gcloud services enable secretmanager.googleapis.com --project $PROJECT

# Enable multiple APIs at once
gcloud services enable \
    compute.googleapis.com \
    container.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudkms.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    cloudtrace.googleapis.com \
    clouderrorreporting.googleapis.com \
    servicenetworking.googleapis.com \
    iam.googleapis.com \
    --project $PROJECT

# List enabled APIs
gcloud services list --enabled --project $PROJECT \
    --format="table(config.name,config.title)"

# Disable an API (stops new usage — existing resources may be affected)
gcloud services disable compute.googleapis.com \
    --project $PROJECT \
    --force  # Disables even if other services depend on it
```

---

## Folders

```bash
# Create a folder hierarchy (requires Organization)
gcloud resource-manager folders create \
    --display-name="Production" \
    --organization=ORG_ID

gcloud resource-manager folders create \
    --display-name="Development" \
    --organization=ORG_ID

# Create a sub-folder
gcloud resource-manager folders create \
    --display-name="Platform Team" \
    --folder=PRODUCTION_FOLDER_ID

# List folders
gcloud resource-manager folders list \
    --organization=ORG_ID \
    --format="table(name,displayName,lifecycleState)"

# Apply an org policy to a folder (inherits to all projects within)
gcloud org-policies set-policy policy.yaml \
    --folder=FOLDER_ID
```

---

## Quotas

GCP enforces per-project quotas on CPU, storage, API calls, etc.

```bash
# View quotas for a service in a region
gcloud compute project-info describe \
    --project $PROJECT \
    --format="json(quotas)"

# View regional quotas
gcloud compute regions describe us-central1 \
    --project $PROJECT \
    --format="table(quotas[].metric,quotas[].limit,quotas[].usage)"

# Check API-level quotas (e.g., Cloud Storage operations)
gcloud alpha services quota list \
    --service=storage.googleapis.com \
    --consumer=project/$PROJECT

# Request quota increase — must be done via Cloud Console:
# console.cloud.google.com/iam-admin/quotas
```

---

## Budget Alerts

```bash
# Create a budget alert (requires billing account access)
# Note: Full budget management via gcloud requires alpha/beta components
# Most users manage budgets via the Console or Terraform

# View billing account linked to project
gcloud billing projects describe $PROJECT \
    --format="table(name,billingAccountName,billingEnabled)"

# Link a billing account
gcloud billing projects link $PROJECT \
    --billing-account=BILLING_ACCOUNT_ID

# List billing accounts accessible to you
gcloud billing accounts list

# Create budget via API (recommended approach — use Terraform)
# See billing.md for Terraform-based budget management
```

---

## Resource Labels

Labels are key-value metadata on GCP resources used for cost attribution, filtering, and policy targeting.

```bash
# Add labels to a project
gcloud projects update my-app-prod-123456 \
    --update-labels=environment=production,team=platform,cost-center=cc-1234

# Label rules:
# - Keys: 1–63 lowercase chars, digits, hyphens, underscores; must start with letter
# - Max 64 labels per resource

# Find resources by label (using Cloud Asset Inventory)
gcloud asset search-all-resources \
    --project $PROJECT \
    --query="labels.environment=production" \
    --asset-types="compute.googleapis.com/Instance" \
    --format="table(name,assetType,labels)"

# Add labels to a VM
gcloud compute instances add-labels my-vm \
    --zone=us-central1-a \
    --labels=environment=production,service=my-app
```

---

## Tags (vs Labels)

Tags (network tags) and Resource Tags serve different purposes:

| Type | Purpose |
|------|---------|
| **Labels** | Cost tracking, organization, filtering |
| **Network tags** | Firewall rule targeting (`--tags=web-server`) |
| **Resource tags** (key-value) | IAM conditions, org policy conditions |

```bash
# Create a resource tag key and value
gcloud resource-manager tags keys create environment \
    --parent=organizations/ORG_ID

gcloud resource-manager tags values create production \
    --parent=organizations/ORG_ID/tagKeys/TAGKEY_ID

# Bind a tag to a resource
gcloud resource-manager tags bindings create \
    --tag-value=organizations/ORG_ID/tagKeys/TAGKEY_ID/tagValues/TAGVALUE_ID \
    --parent=//compute.googleapis.com/projects/PROJECT_NUMBER/zones/us-central1-a/instances/my-vm \
    --location=us-central1-a
```

---

## References

- [GCP resource hierarchy](https://cloud.google.com/resource-manager/docs/cloud-platform-resource-hierarchy)
- [Managing projects](https://cloud.google.com/resource-manager/docs/creating-managing-projects)
- [API enablement](https://cloud.google.com/apis/docs/getting-started)
- [Labels and tags](https://cloud.google.com/resource-manager/docs/creating-managing-labels)

---

← [Previous: gcloud CLI](./gcloud.md) | [Home](../../README.md) | [Next: Billing →](./billing.md)
