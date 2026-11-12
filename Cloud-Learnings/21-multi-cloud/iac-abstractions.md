← [Previous: Data Replication](./data-replication.md) | [Home](../README.md) | [Next: Projects →](../22-projects/README.md)

---

# IaC Abstractions for Multi-Cloud

Managing infrastructure across multiple cloud providers requires tooling that can express all three in a single workflow. Terraform and Pulumi both support multi-provider configurations. The goal is to use providers natively (no false abstraction layer) while sharing common patterns.

---

## Terraform Multi-Provider

### Provider Configuration

```hcl
# versions.tf
terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "multi-cloud/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      managed_by  = "terraform"
      environment = var.environment
      project     = var.project
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "azurerm" {
  features {}
  subscription_id = var.azure_subscription_id
}
```

### Cross-Provider Resource Example

```hcl
# main.tf — Deploy app on AWS, analytics on GCP, identity on Azure

# ─── AWS: Application Layer ───────────────────────────────────────────────────

resource "aws_ecs_cluster" "app" {
  name = "${var.project}-${var.environment}"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = { role = "compute" }
}

resource "aws_ecs_service" "order_api" {
  name            = "order-api"
  cluster         = aws_ecs_cluster.app.id
  task_definition = aws_ecs_task_definition.order_api.arn
  desired_count   = var.order_api_task_count

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.order_api.id]
    assign_public_ip = false
  }
}

# ─── GCP: Analytics Layer ─────────────────────────────────────────────────────

resource "google_bigquery_dataset" "analytics" {
  dataset_id  = "${replace(var.project, "-", "_")}_analytics"
  location    = var.gcp_region
  description = "Analytics replica from AWS production data"

  labels = {
    managed_by  = "terraform"
    environment = var.environment
  }

  access {
    role          = "WRITER"
    special_group = "projectWriters"
  }
}

resource "google_bigquery_table" "orders_replica" {
  dataset_id = google_bigquery_dataset.analytics.dataset_id
  table_id   = "orders_replica"

  time_partitioning {
    type  = "DAY"
    field = "source_timestamp"
  }

  clustering = ["customer_id", "status"]

  schema = jsonencode([
    { name = "ingested_at",       type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "source_timestamp",  type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "operation",         type = "STRING",    mode = "REQUIRED" },
    { name = "order_id",          type = "STRING",    mode = "REQUIRED" },
    { name = "customer_id",       type = "STRING",    mode = "NULLABLE" },
    { name = "status",            type = "STRING",    mode = "NULLABLE" },
    { name = "total_amount",      type = "NUMERIC",   mode = "NULLABLE" },
    { name = "is_deleted",        type = "BOOL",      mode = "NULLABLE" },
  ])

  labels = {
    managed_by  = "terraform"
    environment = var.environment
  }
}

# ─── Azure: Identity Layer ────────────────────────────────────────────────────

resource "azurerm_user_assigned_identity" "app_identity" {
  name                = "${var.project}-${var.environment}-identity"
  resource_group_name = var.azure_resource_group
  location            = var.azure_region
  tags = {
    managed_by  = "terraform"
    environment = var.environment
  }
}

# ─── Cross-Cloud: GCP Workload Identity for AWS ───────────────────────────────

resource "google_iam_workload_identity_pool" "aws_pool" {
  workload_identity_pool_id = "aws-${var.environment}-pool"
  display_name              = "AWS ${var.environment} workloads"
}

resource "google_iam_workload_identity_pool_provider" "aws_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.aws_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "aws-provider"

  aws {
    account_id = var.aws_account_id
  }

  attribute_mapping = {
    "google.subject" = "assertion.arn"
    "attribute.aws_role" = "assertion.arn.extract('assumed-role/{role}/')"
  }
}
```

### Variables and Outputs

```hcl
# variables.tf
variable "aws_region" {
  default = "us-east-1"
}

variable "gcp_project_id" {
  description = "GCP project ID"
}

variable "gcp_region" {
  default = "us-central1"
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
}

variable "azure_region" {
  default = "eastus"
}

variable "azure_resource_group" {
  description = "Azure resource group name"
}

variable "aws_account_id" {
  description = "AWS account ID (12 digits)"
}

variable "environment" {
  description = "prod | staging | dev"
}

variable "project" {
  description = "Project name (kebab-case)"
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "order_api_task_count" {
  default = 3
}

# outputs.tf
output "aws_ecs_cluster_name" {
  value = aws_ecs_cluster.app.name
}

output "gcp_bq_dataset" {
  value = google_bigquery_dataset.analytics.dataset_id
}

output "gcp_workload_identity_pool" {
  value = google_iam_workload_identity_pool.aws_pool.name
}

output "azure_managed_identity_id" {
  value = azurerm_user_assigned_identity.app_identity.id
}
```

---

## Pulumi Multi-Cloud (Python)

```python
"""
Pulumi program: multi-cloud infrastructure.
Deploy to: pulumi up --stack prod
"""
import pulumi
import pulumi_aws as aws
import pulumi_gcp as gcp
import pulumi_azure_native as azure

config = pulumi.Config()
environment = config.require("environment")
project_name = config.require("projectName")

# ─── AWS ──────────────────────────────────────────────────────────────────────

aws_cluster = aws.ecs.Cluster(
    f"{project_name}-cluster",
    settings=[aws.ecs.ClusterSettingArgs(name="containerInsights", value="enabled")],
    tags={"environment": environment, "managed_by": "pulumi"},
)

# ─── GCP ──────────────────────────────────────────────────────────────────────

gcp_dataset = gcp.bigquery.Dataset(
    f"{project_name}-analytics",
    dataset_id=f"{project_name.replace('-', '_')}_analytics",
    location="US",
    labels={"environment": environment, "managed_by": "pulumi"},
)

gcp_table = gcp.bigquery.Table(
    "orders-replica",
    dataset_id=gcp_dataset.dataset_id,
    table_id="orders_replica",
    time_partitioning=gcp.bigquery.TableTimePartitioningArgs(
        type="DAY",
        field="source_timestamp",
    ),
    schema=pulumi.Output.from_input([
        {"name": "ingested_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
        {"name": "order_id", "type": "STRING", "mode": "REQUIRED"},
        {"name": "status", "type": "STRING", "mode": "NULLABLE"},
        {"name": "total_amount", "type": "NUMERIC", "mode": "NULLABLE"},
    ]).apply(lambda s: str(s).replace("'", '"')),
)

# ─── Cross-cloud: pass GCP dataset ID to AWS as SSM parameter ─────────────────

aws_ssm_gcp_dataset = aws.ssm.Parameter(
    "gcp-dataset-id",
    name=f"/{environment}/{project_name}/gcp-bq-dataset",
    type="String",
    value=gcp_dataset.dataset_id,
    tags={"environment": environment},
)

# ─── Exports ──────────────────────────────────────────────────────────────────

pulumi.export("aws_cluster_arn", aws_cluster.arn)
pulumi.export("gcp_bq_dataset", gcp_dataset.dataset_id)
pulumi.export("gcp_bq_table", gcp_table.table_id)
```

---

## Shared Modules Pattern

Structure Terraform for multi-cloud by keeping provider-specific modules separate and a top-level root that composes them.

```
infrastructure/
├── modules/
│   ├── aws/
│   │   ├── compute/          # ECS, EC2
│   │   ├── database/         # RDS, DynamoDB
│   │   └── networking/       # VPC, subnets, SGs
│   ├── gcp/
│   │   ├── analytics/        # BigQuery, Dataflow
│   │   ├── compute/          # GKE, Cloud Run
│   │   └── networking/       # VPC, firewall
│   └── azure/
│       ├── identity/         # Entra ID, managed identities
│       └── networking/       # VNet, NSG
├── environments/
│   ├── prod/
│   │   ├── main.tf           # calls modules from all three
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   └── dev/
└── shared/
    ├── dns/                  # cross-cloud DNS (Route 53 + Cloud DNS)
    └── monitoring/           # unified alerting (Datadog / Grafana)
```

```hcl
# environments/prod/main.tf — root module that composes everything

module "aws_compute" {
  source         = "../../modules/aws/compute"
  environment    = var.environment
  vpc_id         = module.aws_networking.vpc_id
  subnet_ids     = module.aws_networking.private_subnet_ids
  task_count     = 5
}

module "gcp_analytics" {
  source         = "../../modules/gcp/analytics"
  environment    = var.environment
  project_id     = var.gcp_project_id
  region         = var.gcp_region
  source_aws_account_id = var.aws_account_id
}

module "azure_identity" {
  source         = "../../modules/azure/identity"
  environment    = var.environment
  resource_group = var.azure_resource_group
}
```

---

## CI/CD for Multi-Cloud IaC

```yaml
# .github/workflows/terraform-multi-cloud.yml
name: Terraform Multi-Cloud

on:
  push:
    branches: [main]
    paths: ["infrastructure/**"]
  pull_request:
    paths: ["infrastructure/**"]

jobs:
  plan:
    name: Terraform Plan
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # OIDC for all three providers
      contents: read

    steps:
      - uses: actions/checkout@v4

      # AWS OIDC
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/terraform-ci-role
          aws-region: us-east-1

      # GCP OIDC
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/123/locations/global/workloadIdentityPools/github-pool/providers/github-provider
          service_account: terraform@my-project.iam.gserviceaccount.com

      # Azure OIDC
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "~1.6"

      - name: Terraform Init
        run: terraform -chdir=infrastructure/environments/prod init

      - name: Terraform Validate
        run: terraform -chdir=infrastructure/environments/prod validate

      - name: Terraform Plan
        run: terraform -chdir=infrastructure/environments/prod plan -out=tfplan

      - name: Upload plan artifact
        uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: infrastructure/environments/prod/tfplan

  apply:
    name: Terraform Apply
    runs-on: ubuntu-latest
    needs: plan
    if: github.ref == 'refs/heads/main'
    environment: production    # requires manual approval in GitHub Environments
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4
      # (same auth steps as above)
      - name: Download plan
        uses: actions/download-artifact@v4
        with:
          name: tfplan
          path: infrastructure/environments/prod/
      - name: Terraform Apply
        run: terraform -chdir=infrastructure/environments/prod apply tfplan
```

---

## References

- [Terraform AWS provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
- [Terraform GCP provider](https://registry.terraform.io/providers/hashicorp/google/latest)
- [Terraform Azure provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest)
- [Pulumi multi-cloud examples](https://github.com/pulumi/examples)

---

← [Previous: Data Replication](./data-replication.md) | [Home](../README.md) | [Next: Projects →](../22-projects/README.md)
