← [Previous: Terraform / OpenTofu](./README.md) | [Home](../README.md) | [Next: State Management →](./state.md)

---

# Getting Started with Terraform

---

## Installation

```bash
# macOS (Homebrew)
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# Linux (apt)
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt-get update && sudo apt-get install terraform

# Verify
terraform version

# OpenTofu (alternative)
# macOS
brew install opentofu

# Linux (snap)
snap install --classic opentofu
tofu version
```

---

## HCL Syntax Fundamentals

```hcl
# comments use # or //
/* multi-line comment */

# --- Block types ---
# resource: manages a cloud object
resource "PROVIDER_TYPE" "LOCAL_NAME" {
  argument = value
}

# data: reads existing infrastructure (no create/update/delete)
data "PROVIDER_TYPE" "LOCAL_NAME" {
  argument = value
}

# variable: input parameter
variable "NAME" {
  type    = string
  default = "value"
}

# output: exported value after apply
output "NAME" {
  value = resource.type.name.attribute
}

# locals: computed constants
locals {
  name_prefix = "my-app-${var.environment}"
}

# --- Value types ---
# string
name = "my-bucket"
# number
count = 3
# bool
enabled = true
# list
zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
# map / object
tags = {
  Environment = "production"
  Team        = "platform"
}

# --- References ---
# var.VARIABLE_NAME
# local.LOCAL_NAME
# data.TYPE.NAME.ATTRIBUTE
# resource.TYPE.NAME.ATTRIBUTE (or just TYPE.NAME.ATTRIBUTE within module)
# module.MODULE_NAME.OUTPUT_NAME
```

---

## First Configuration (AWS S3 Bucket)

```hcl
# versions.tf
terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}
```

```hcl
# variables.tf
variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
  default     = "development"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "environment must be development, staging, or production."
  }
}

variable "bucket_name" {
  type        = string
  description = "S3 bucket name (globally unique)"
}
```

```hcl
# main.tf
locals {
  common_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket" "app" {
  bucket = var.bucket_name
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "app" {
  bucket = aws_s3_bucket.app.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app" {
  bucket = aws_s3_bucket.app.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "app" {
  bucket                  = aws_s3_bucket.app.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

```hcl
# outputs.tf
output "bucket_id" {
  value       = aws_s3_bucket.app.id
  description = "S3 bucket name"
}

output "bucket_arn" {
  value       = aws_s3_bucket.app.arn
  description = "S3 bucket ARN"
}
```

---

## Running Terraform

```bash
# 1. Initialize
terraform init
# Output: Downloading provider hashicorp/aws v5.x.y...
#         Terraform has been successfully initialized!

# 2. Format
terraform fmt

# 3. Validate
terraform validate
# Success! The configuration is valid.

# 4. Plan (pass variables at CLI)
terraform plan \
  -var="bucket_name=my-app-prod-data" \
  -var="environment=production"

# Or use a .tfvars file
cat > terraform.tfvars <<EOF
bucket_name = "my-app-prod-data"
environment = "production"
region      = "us-east-1"
EOF
terraform plan -var-file=terraform.tfvars

# 5. Apply
terraform apply -var-file=terraform.tfvars
# Type "yes" to confirm, or use -auto-approve in CI

# 6. Show outputs
terraform output bucket_arn

# 7. Destroy
terraform destroy -var-file=terraform.tfvars
```

---

## Resource Lifecycle

```hcl
resource "aws_instance" "web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.medium"

  lifecycle {
    # Prevent accidental deletion of critical resources
    prevent_destroy = true

    # Create new resource before destroying old one (zero-downtime replace)
    create_before_destroy = true

    # Ignore changes to specific attributes (e.g., managed externally)
    ignore_changes = [
      tags["LastModified"],
      user_data,
    ]
  }
}

# Depends_on — explicit dependency when Terraform can't infer it
resource "aws_iam_role_policy_attachment" "example" {
  role       = aws_iam_role.example.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"

  depends_on = [aws_iam_role.example]
}
```

---

## Data Sources

```hcl
# Fetch the latest Amazon Linux 2023 AMI
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Fetch existing VPC by tag
data "aws_vpc" "existing" {
  tags = {
    Name = "vpc-production"
  }
}

# Fetch current AWS account details
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Use in resources
resource "aws_instance" "web" {
  ami  = data.aws_ami.al2023.id
  # ...
}

output "account_id" {
  value = data.aws_caller_identity.current.account_id
}
```

---

## References

- [Terraform language docs](https://developer.hashicorp.com/terraform/language)
- [AWS provider docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [HCL specification](https://github.com/hashicorp/hcl/blob/main/hclsyntax/spec.md)

---

← [Previous: Terraform / OpenTofu](./README.md) | [Home](../README.md) | [Next: State Management →](./state.md)
