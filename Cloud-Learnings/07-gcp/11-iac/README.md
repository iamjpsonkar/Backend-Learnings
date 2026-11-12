← [Previous: Cloud Trace](../10-observability/cloud-trace.md) | [Home](../../README.md) | [Next: Terraform on GCP →](./terraform-gcp.md)

---

# GCP Infrastructure as Code

---

## Tool Selection

| Tool | GCP-native? | Use Case |
|------|------------|---------|
| **Terraform** | No (HashiCorp) | Multi-cloud IaC — most widely used for GCP |
| **Pulumi** | No | IaC with real programming languages (Python, Go, TS) |
| **Config Connector** | Yes | Manage GCP resources as Kubernetes CRDs |
| **Deployment Manager** | Yes (deprecated) | GCP-native YAML/Python IaC — avoid for new projects |
| **gcloud** scripts | Yes | One-off provisioning or bootstrapping |

Terraform is the recommended choice for GCP IaC. Config Connector is useful when GKE is already the control plane.

---

## Terraform on GCP

### Remote State Setup (GCS Backend)

```bash
PROJECT_ID="my-app-production"
REGION="us-central1"
STATE_BUCKET="${PROJECT_ID}-terraform-state"

# Create the GCS bucket for Terraform state
gcloud storage buckets create gs://$STATE_BUCKET \
    --project=$PROJECT_ID \
    --location=$REGION \
    --uniform-bucket-level-access \
    --public-access-prevention

# Enable versioning (protects against accidental state deletion)
gcloud storage buckets update gs://$STATE_BUCKET \
    --versioning

# Enable object-level logging
gcloud storage buckets update gs://$STATE_BUCKET \
    --log-bucket=gs://${PROJECT_ID}-access-logs \
    --log-object-prefix=terraform-state/
```

### versions.tf

```hcl
terraform {
  required_version = ">= 1.7"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.30"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "gcs" {
    bucket = "my-app-production-terraform-state"
    prefix = "my-app/production"  # folder path within bucket
  }
}

provider "google" {
  project = var.project_id
  region  = var.region

  # Authentication:
  # - Local: GOOGLE_APPLICATION_CREDENTIALS or `gcloud auth application-default login`
  # - CI/CD: Workload Identity Federation (no key files)
  # - GCE/Cloud Run/GKE: Attached service account (automatic)

  default_labels = {
    managed_by  = "terraform"
    environment = var.environment
    application = var.app_name
  }
}

provider "google-beta" {
  project = var.project_id
  region  = var.region

  default_labels = {
    managed_by  = "terraform"
    environment = var.environment
    application = var.app_name
  }
}
```

### variables.tf

```hcl
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for primary deployment"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be one of: dev, staging, production"
  }
}

variable "app_name" {
  description = "Short application name (lowercase, alphanumeric, hyphens)"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.app_name))
    error_message = "app_name must be 3-20 lowercase alphanumeric characters or hyphens"
  }
}

variable "vpc_cidr" {
  description = "VPC address range (not used for routing in GCP, informational only)"
  type        = string
  default     = "10.0.0.0/16"
}
```

### main.tf

```hcl
locals {
  prefix = "${var.app_name}-${var.environment}"
}

# ─── Enable Required APIs ──────────────────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudkms.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "iamcredentials.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

# ─── VPC ──────────────────────────────────────────────────────────────────────
resource "google_compute_network" "main" {
  project                 = var.project_id
  name                    = "vpc-${local.prefix}"
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"

  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "app" {
  project                  = var.project_id
  name                     = "snet-app-${var.region}"
  network                  = google_compute_network.main.self_link
  region                   = var.region
  ip_cidr_range            = "10.0.11.0/24"
  private_ip_google_access = true
}

resource "google_compute_subnetwork" "gke" {
  project                  = var.project_id
  name                     = "snet-gke-${var.region}"
  network                  = google_compute_network.main.self_link
  region                   = var.region
  ip_cidr_range            = "10.0.31.0/24"
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/20"
  }
}

# ─── Cloud NAT ────────────────────────────────────────────────────────────────
resource "google_compute_router" "main" {
  project = var.project_id
  name    = "router-${var.region}"
  network = google_compute_network.main.self_link
  region  = var.region
}

resource "google_compute_router_nat" "main" {
  project                            = var.project_id
  name                               = "nat-${var.region}"
  router                             = google_compute_router.main.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# ─── Service Account ───────────────────────────────────────────────────────────
resource "google_service_account" "workload" {
  project      = var.project_id
  account_id   = "${var.app_name}-workload"
  display_name = "${title(var.app_name)} Workload Service Account"
  description  = "Service account for ${var.app_name} application workloads"
}

resource "google_project_iam_member" "workload_trace" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.workload.email}"
}

resource "google_project_iam_member" "workload_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.workload.email}"
}

# ─── Artifact Registry ────────────────────────────────────────────────────────
resource "google_artifact_registry_repository" "app" {
  project       = var.project_id
  location      = var.region
  repository_id = var.app_name
  format        = "DOCKER"
  description   = "${var.app_name} container images"

  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "keep-tagged"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }
  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s"  # 7 days
    }
  }
}

# ─── GKE Autopilot Cluster ────────────────────────────────────────────────────
resource "google_container_cluster" "main" {
  provider = google-beta

  project  = var.project_id
  name     = "gke-${local.prefix}-${var.region}"
  location = var.region

  enable_autopilot = true
  network          = google_compute_network.main.self_link
  subnetwork       = google_compute_subnetwork.gke.self_link

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  depends_on = [google_project_service.apis]
}
```

### outputs.tf

```hcl
output "vpc_id" {
  description = "VPC self-link"
  value       = google_compute_network.main.self_link
}

output "gke_cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.main.name
}

output "workload_sa_email" {
  description = "Workload service account email"
  value       = google_service_account.workload.email
}

output "artifact_registry_url" {
  description = "Artifact Registry Docker repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}"
}
```

### Terraform Workflow

```bash
# Authenticate for Terraform
gcloud auth application-default login

# Init — downloads providers, configures GCS backend
terraform init

# Validate
terraform validate && terraform fmt -check -recursive

# Plan (always save output for reproducible apply)
terraform plan \
    -var="project_id=my-app-production" \
    -var="environment=production" \
    -var="app_name=my-app" \
    -out=tfplan

# Apply
terraform apply tfplan

# Workspaces — separate state for each environment
terraform workspace new staging
terraform workspace select production
terraform workspace list

# Destroy with confirmation prompt
terraform destroy \
    -var="project_id=my-app-production" \
    -var="environment=production" \
    -var="app_name=my-app"
```

### GitHub Actions — Terraform + Workload Identity

```yaml
# .github/workflows/terraform.yml
name: Terraform Plan & Apply

on:
  pull_request:
    paths: ["infra/**"]
  push:
    branches: [main]
    paths: ["infra/**"]

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infra

    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: "projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
          service_account: "terraform@my-app-production.iam.gserviceaccount.com"

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "~1.7"

      - run: terraform init
      - run: terraform validate
      - run: terraform fmt -check

      - name: Terraform Plan
        id: plan
        run: |
          terraform plan \
            -var="project_id=my-app-production" \
            -var="environment=production" \
            -var="app_name=my-app" \
            -out=tfplan \
            -no-color 2>&1 | tee plan.txt

      - name: Post Plan to PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const plan = fs.readFileSync('infra/plan.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `\`\`\`hcl\n${plan.slice(0, 65000)}\n\`\`\``
            });

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply tfplan
```

---

## References

- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GCS Terraform backend](https://developer.hashicorp.com/terraform/language/settings/backends/gcs)
- [Config Connector](https://cloud.google.com/config-connector/docs)
- [Workload Identity Federation for GitHub Actions](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions)
---

← [Previous: Cloud Trace](../10-observability/cloud-trace.md) | [Home](../../README.md) | [Next: Terraform on GCP →](./terraform-gcp.md)
