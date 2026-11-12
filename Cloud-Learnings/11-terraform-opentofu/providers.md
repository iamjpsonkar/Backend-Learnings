← [Previous: Expressions](./expressions.md) | [Home](../README.md) | [Next: Testing →](./testing.md)

---

# Providers

Providers are plugins that allow Terraform to interact with APIs. Each provider exposes resources and data sources for a specific platform or service.

---

## Provider Configuration

```hcl
# versions.tf — declare and pin providers
terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"   # Allow 5.x, not 6.x
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.90, < 4.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}
```

---

## AWS Provider

```hcl
# Default provider (uses default credentials chain)
provider "aws" {
  region = var.region

  default_tags {
    tags = {
      ManagedBy   = "terraform"
      Environment = var.environment
      Project     = var.project
    }
  }
}

# Assume a role (cross-account deployments)
provider "aws" {
  region = var.region

  assume_role {
    role_arn     = "arn:aws:iam::123456789012:role/TerraformRole"
    session_name = "terraform-${var.environment}"
    external_id  = var.external_id
  }
}
```

---

## Provider Aliases (Multi-Region, Multi-Account)

```hcl
# Default AWS provider (primary region)
provider "aws" {
  region = "us-east-1"
}

# Aliased provider for secondary region
provider "aws" {
  alias  = "us_west"
  region = "us-west-2"
}

# Aliased provider for another account
provider "aws" {
  alias  = "prod_account"
  region = "us-east-1"

  assume_role {
    role_arn = "arn:aws:iam::PROD_ACCOUNT:role/TerraformRole"
  }
}

# Use aliased provider in a resource
resource "aws_s3_bucket" "replica" {
  provider = aws.us_west
  bucket   = "my-app-replica"
}

resource "aws_vpc" "prod" {
  provider   = aws.prod_account
  cidr_block = "10.0.0.0/16"
}
```

---

## Azure Provider

```hcl
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }

  # Authentication via environment variables:
  # ARM_TENANT_ID, ARM_SUBSCRIPTION_ID
  # ARM_CLIENT_ID + ARM_CLIENT_SECRET  (service principal)
  # ARM_USE_OIDC=true (GitHub Actions / Workload Identity)
}

# Multi-subscription
provider "azurerm" {
  alias           = "hub"
  subscription_id = var.hub_subscription_id
  features {}
}
```

---

## GCP Provider

```hcl
provider "google" {
  project = var.project_id
  region  = var.region

  default_labels = {
    managed_by  = "terraform"
    environment = var.environment
  }
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# GCP authentication:
# Application Default Credentials (gcloud auth application-default login)
# Service account JSON key: GOOGLE_CREDENTIALS env var
# Workload Identity on GKE/Cloud Run: automatic
```

---

## Kubernetes Provider

```hcl
# Fetch cluster credentials from data source
data "aws_eks_cluster" "app" {
  name = aws_eks_cluster.app.name
}

data "aws_eks_cluster_auth" "app" {
  name = aws_eks_cluster.app.name
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.app.endpoint
  cluster_ca_certificate = base64decode(data.aws_eks_cluster.app.certificate_authority[0].data)
  token                  = data.aws_eks_cluster_auth.app.token
}

provider "helm" {
  kubernetes {
    host                   = data.aws_eks_cluster.app.endpoint
    cluster_ca_certificate = base64decode(data.aws_eks_cluster.app.certificate_authority[0].data)
    token                  = data.aws_eks_cluster_auth.app.token
  }
}
```

---

## Random Provider (Utility)

```hcl
resource "random_password" "db" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "app" {
  bucket = "my-app-${random_id.suffix.hex}"  # Globally unique name
}

output "db_password" {
  value     = random_password.db.result
  sensitive = true
}
```

---

## Provider Version Constraints

```
~> 5.0     Allows 5.x (patch + minor), not 6.0+
~> 5.3.1   Allows 5.3.x (patch only), not 5.4.0+
>= 3.0     Any version ≥ 3.0
>= 3.0, < 4.0  Range (same as ~> 3.0)
= 3.5.2    Exact version (pin tightly)
!= 3.5.0   Exclude a bad release
```

---

## .terraform.lock.hcl

```hcl
# Auto-generated lock file — always commit to git
# Records exact provider versions and checksums for reproducible builds
provider "registry.terraform.io/hashicorp/aws" {
  version     = "5.31.0"
  constraints = "~> 5.0"
  hashes = [
    "h1:abc123...",
    "zh:def456...",
  ]
}
```

```bash
# Upgrade providers (update lock file)
terraform init -upgrade

# Validate all providers against lock file hashes
terraform providers lock \
  -platform=linux_amd64 \
  -platform=darwin_amd64 \
  -platform=darwin_arm64
```

---

## References

- [Provider configuration](https://developer.hashicorp.com/terraform/language/providers/configuration)
- [AWS provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Azure provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [GCP provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

---

← [Previous: Expressions](./expressions.md) | [Home](../README.md) | [Next: Testing →](./testing.md)
