← [Previous: GCP IaC](./README.md) | [Home](../../README.md) | [Next: GCP Projects →](../12-projects/README.md)

---

# Terraform on GCP

Terraform manages GCP infrastructure declaratively. The `google` and `google-beta` providers cover all GCP services. Remote state is stored in Cloud Storage.

---

## Backend Setup

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
TF_STATE_BUCKET="my-app-prod-tf-state"

# Create a GCS bucket for Terraform state
gcloud storage buckets create gs://$TF_STATE_BUCKET \
    --project=$PROJECT \
    --location=$REGION \
    --uniform-bucket-level-access \
    --public-access-prevention

# Enable versioning so you can recover from bad applies
gcloud storage buckets update gs://$TF_STATE_BUCKET \
    --versioning

# Grant CI/CD SA permission to read/write state
gcloud storage buckets add-iam-policy-binding gs://$TF_STATE_BUCKET \
    --member="serviceAccount:sa-terraform@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

---

## versions.tf

```hcl
terraform {
  required_version = ">= 1.7"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "my-app-prod-tf-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region

  default_labels = {
    managed_by  = "terraform"
    environment = var.environment
    team        = "platform"
  }
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}
```

---

## variables.tf

```hcl
variable "project_id" {
  type        = string
  description = "GCP project ID"

  validation {
    condition     = length(var.project_id) > 0
    error_message = "project_id must not be empty."
  }
}

variable "region" {
  type        = string
  description = "Primary GCP region"
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Deployment environment"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "environment must be development, staging, or production."
  }
}

variable "gke_min_nodes" {
  type        = number
  description = "Minimum nodes per zone in GKE cluster"
  default     = 1
}

variable "gke_max_nodes" {
  type        = number
  description = "Maximum nodes per zone in GKE cluster"
  default     = 10
}
```

---

## main.tf

```hcl
locals {
  name_prefix = "my-app-${var.environment}"
}

# --- Enable APIs ---
locals {
  apis = [
    "compute.googleapis.com",
    "container.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudkms.googleapis.com",
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project                    = var.project_id
  service                    = each.value
  disable_on_destroy         = false
  disable_dependent_services = false
}

# --- VPC ---
resource "google_compute_network" "vpc" {
  name                    = "vpc-${local.name_prefix}"
  project                 = var.project_id
  auto_create_subnetworks = false

  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "gke" {
  name          = "subnet-gke-${local.name_prefix}"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = "10.0.0.0/24"

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.1.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.2.0.0/20"
  }

  private_ip_google_access = true
}

resource "google_compute_subnetwork" "private" {
  name          = "subnet-private-${local.name_prefix}"
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = "10.0.1.0/24"

  private_ip_google_access = true
}

# --- Cloud Router + NAT ---
resource "google_compute_router" "router" {
  name    = "router-${local.name_prefix}"
  project = var.project_id
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "nat-${local.name_prefix}"
  project                            = var.project_id
  router                             = google_compute_router.router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# --- Service Accounts ---
resource "google_service_account" "app" {
  account_id   = "sa-my-app"
  project      = var.project_id
  display_name = "My App workload SA"
}

resource "google_service_account" "gke_nodes" {
  account_id   = "sa-gke-nodes"
  project      = var.project_id
  display_name = "GKE node SA (minimal permissions)"
}

resource "google_project_iam_member" "gke_nodes_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_project_iam_member" "gke_nodes_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_project_iam_member" "gke_nodes_ar_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

# --- Artifact Registry ---
resource "google_artifact_registry_repository" "app" {
  repository_id = "my-app"
  project       = var.project_id
  location      = var.region
  format        = "DOCKER"
  description   = "My App container images"

  cleanup_policies {
    id     = "keep-10-tagged"
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
      older_than = "86400s"
    }
  }

  depends_on = [google_project_service.apis]
}

# --- GKE Autopilot ---
resource "google_container_cluster" "app" {
  provider = google-beta

  name     = "gke-${local.name_prefix}"
  project  = var.project_id
  location = var.region

  enable_autopilot = true
  deletion_protection = var.environment == "production"

  network    = google_compute_network.vpc.id
  subnetwork = google_compute_subnetwork.gke.id

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "10.0.0.0/8"
      display_name = "Internal"
    }
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  depends_on = [google_project_service.apis]
}
```

---

## outputs.tf

```hcl
output "vpc_id" {
  value       = google_compute_network.vpc.id
  description = "VPC network ID"
}

output "gke_cluster_name" {
  value       = google_container_cluster.app.name
  description = "GKE cluster name"
}

output "gke_cluster_endpoint" {
  value       = google_container_cluster.app.endpoint
  description = "GKE cluster API endpoint"
  sensitive   = true
}

output "artifact_registry_url" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.app.repository_id}"
  description = "Artifact Registry Docker repository URL"
}

output "app_sa_email" {
  value       = google_service_account.app.email
  description = "App workload service account email"
}
```

---

## GitHub Actions CI/CD

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  push:
    branches: [main]
    paths: ["infra/**"]
  pull_request:
    branches: [main]
    paths: ["infra/**"]

permissions:
  id-token: write
  contents: read
  pull-requests: write

env:
  TF_VERSION: "1.7.5"
  WORKING_DIR: "./infra"

jobs:
  terraform:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ${{ env.WORKING_DIR }}

    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.TF_SA_EMAIL }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: ${{ env.TF_VERSION }}

      - name: Terraform Init
        run: terraform init

      - name: Terraform Format Check
        run: terraform fmt -check -recursive

      - name: Terraform Validate
        run: terraform validate

      - name: Terraform Plan
        id: plan
        run: |
          terraform plan \
            -var="project_id=${{ vars.GCP_PROJECT_ID }}" \
            -var="environment=${{ vars.ENVIRONMENT }}" \
            -out=tfplan \
            -no-color 2>&1 | tee plan-output.txt

      - name: Comment Plan on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const plan = fs.readFileSync('${{ env.WORKING_DIR }}/plan-output.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Terraform Plan\n\`\`\`\n${plan.slice(-65000)}\n\`\`\``
            });

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply -auto-approve tfplan
```

---

## References

- [Google provider documentation](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [GCS backend](https://developer.hashicorp.com/terraform/language/settings/backends/gcs)
- [Workload Identity for Terraform](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions)

---

← [Previous: GCP IaC](./README.md) | [Home](../../README.md) | [Next: GCP Projects →](../12-projects/README.md)
