← [Previous: Getting Started](./getting-started.md) | [Home](../README.md) | [Next: Modules →](./modules.md)

---

# State Management

Terraform state is a JSON file that maps configuration resources to real infrastructure objects. It is the single source of truth for what Terraform manages.

---

## Why State Matters

- Tracks resource IDs so Terraform can update/delete existing infrastructure
- Stores metadata (dependencies, provider schema versions)
- Enables performance optimization (caching attribute values)
- **Never edit state manually** — use `terraform state` commands or `terraform import`

---

## Local State (Development Only)

```
terraform.tfstate          # current state
terraform.tfstate.backup   # state before last apply
```

Local state has no locking — unsafe for teams. Use remote state in any shared environment.

---

## Remote Backends

### S3 + DynamoDB (AWS)

```hcl
# versions.tf
terraform {
  required_version = ">= 1.7"

  backend "s3" {
    bucket         = "my-app-tf-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:123456789012:key/abc-123"
    dynamodb_table = "terraform-state-lock"  # For state locking
  }
}
```

```bash
# Bootstrap: create the S3 bucket + DynamoDB table
aws s3api create-bucket \
    --bucket my-app-tf-state \
    --region us-east-1

aws s3api put-bucket-versioning \
    --bucket my-app-tf-state \
    --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
    --bucket my-app-tf-state \
    --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws dynamodb create-table \
    --table-name terraform-state-lock \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

### Azure Blob Storage

```hcl
backend "azurerm" {
  resource_group_name  = "rg-terraform-state"
  storage_account_name = "mytfstate"
  container_name       = "tfstate"
  key                  = "production.terraform.tfstate"
}
```

### GCS (GCP)

```hcl
backend "gcs" {
  bucket = "my-app-tf-state"
  prefix = "production"
}
```

### Terraform Cloud / HCP Terraform

```hcl
terraform {
  cloud {
    organization = "my-org"
    workspaces {
      name = "my-app-production"
    }
  }
}
```

---

## State Commands

```bash
# List all resources in state
terraform state list

# Inspect a specific resource
terraform state show aws_s3_bucket.app

# Remove a resource from state without destroying it
# (use when you want Terraform to stop managing it)
terraform state rm aws_s3_bucket.old_bucket

# Move a resource in state (rename or refactor)
terraform state mv aws_s3_bucket.old_name aws_s3_bucket.new_name

# Move resource into a module
terraform state mv aws_s3_bucket.app module.storage.aws_s3_bucket.app

# Pull state to stdout (inspect raw JSON)
terraform state pull | jq '.resources[].type' | sort -u

# Push state from a local file (dangerous — use with care)
terraform state push terraform.tfstate

# Import an existing resource into Terraform management
terraform import aws_s3_bucket.existing my-existing-bucket-name
```

---

## Workspaces

Workspaces isolate state within the same configuration — useful for per-environment deployments from a single root module.

```bash
# List workspaces (default always exists)
terraform workspace list

# Create + switch to a new workspace
terraform workspace new staging
terraform workspace new production

# Switch workspace
terraform workspace select staging

# Show current workspace
terraform workspace show

# Delete a workspace (must not be the active one)
terraform workspace delete old-workspace
```

```hcl
# Use workspace name in resources
locals {
  env = terraform.workspace  # "default", "staging", "production"

  config = {
    default    = { instance_type = "t3.small", min_size = 1 }
    staging    = { instance_type = "t3.medium", min_size = 2 }
    production = { instance_type = "t3.large", min_size = 3 }
  }
}

resource "aws_instance" "web" {
  instance_type = local.config[local.env].instance_type
  # ...
}
```

> **Prefer separate state files over workspaces for production/non-production isolation.** Workspaces share the same provider credentials and configuration — a mistake can affect all workspaces.

---

## State Locking

State locking prevents concurrent applies from corrupting state.

- **S3**: DynamoDB table provides locking
- **GCS**: Native object locking
- **Azure Blob**: Native blob leasing
- **Terraform Cloud**: Built-in

```bash
# If a lock gets stuck (e.g., interrupted apply):
terraform force-unlock LOCK_ID

# Find the lock ID from the error message or:
aws dynamodb scan \
    --table-name terraform-state-lock \
    --query "Items[*].LockID"
```

---

## Sensitive Values in State

State can contain sensitive values (passwords, keys). Protect it:

1. **Encrypt the backend** (S3 SSE, GCS CMEK, Azure SSE)
2. **Restrict access** (IAM/RBAC on the bucket/table)
3. **Never commit `terraform.tfstate` to git** (add to `.gitignore`)
4. Mark outputs as `sensitive = true` to suppress CLI output

```hcl
output "db_password" {
  value     = random_password.db.result
  sensitive = true  # Terraform will not print this value
}
```

---

## Moved Blocks (Refactoring Without Destroy/Recreate)

```hcl
# When you rename a resource or move it into a module, use moved{} so
# Terraform updates state without destroying and recreating.
moved {
  from = aws_s3_bucket.app
  to   = module.storage.aws_s3_bucket.app
}
```

---

## References

- [State documentation](https://developer.hashicorp.com/terraform/language/state)
- [Remote backends](https://developer.hashicorp.com/terraform/language/settings/backends)
- [Workspaces](https://developer.hashicorp.com/terraform/language/state/workspaces)
- [Importing resources](https://developer.hashicorp.com/terraform/language/import)

---

← [Previous: Getting Started](./getting-started.md) | [Home](../README.md) | [Next: Modules →](./modules.md)
