← [Previous: CDK](./cdk.md) | [Home](../../README.md) | [Next: AWS Projects →](../14-projects/README.md)

---

# Terraform on AWS

Terraform (and its open-source fork OpenTofu) provisions AWS infrastructure using the AWS provider. Unlike CDK/CloudFormation, Terraform state is stored separately and the tool is cloud-agnostic.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **Provider** | Plugin that talks to an API (e.g., `hashicorp/aws`) |
| **Resource** | An infrastructure object (`aws_vpc`, `aws_ecs_service`) |
| **Data source** | Read-only lookup of existing infrastructure (`data.aws_ami`) |
| **Module** | A reusable collection of resources with inputs and outputs |
| **State** | Terraform's record of what it has deployed (must be stored remotely in teams) |
| **Workspace** | Isolated state within a single backend (useful for staging/production with the same code) |
| **Plan** | Dry run showing what `apply` will do — always review before applying |
| **Backend** | Where state is stored: local (default) or remote (S3 + DynamoDB lock) |

---

## Project Structure

```
infra/
├── main.tf             # Root module: providers, backend, top-level resources
├── variables.tf        # Input variable definitions
├── outputs.tf          # Output values
├── locals.tf           # Local values (computed from variables)
├── versions.tf         # Required provider versions
├── modules/
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── ecs-service/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    ├── staging/
    │   ├── main.tf     # Calls root modules with staging values
    │   └── terraform.tfvars
    └── production/
        ├── main.tf
        └── terraform.tfvars
```

---

## versions.tf — Pin Provider Versions

```hcl
terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "my-terraform-state-123456789012"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "alias/terraform-state-key"
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Team        = var.team
    }
  }
}
```

---

## Remote State Backend Setup

```bash
# Create state bucket (one-time)
aws s3api create-bucket \
    --bucket my-terraform-state-$(aws sts get-caller-identity --query Account --output text) \
    --region us-east-1

aws s3api put-bucket-versioning \
    --bucket my-terraform-state-123456789012 \
    --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
    --bucket my-terraform-state-123456789012 \
    --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms"}}]}'

aws s3api put-public-access-block \
    --bucket my-terraform-state-123456789012 \
    --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Create DynamoDB table for state locking
aws dynamodb create-table \
    --table-name terraform-state-lock \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --tags Key=ManagedBy,Value=Terraform
```

---

## variables.tf

```hcl
variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "team" {
  description = "Team that owns these resources"
  type        = string
  default     = "platform"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}
```

---

## main.tf — VPC + ECS Example

```hcl
locals {
  name_prefix = "${var.environment}-my-app"
  common_tags = {
    Environment = var.environment
    Project     = "my-app"
  }
}

# Data: fetch the latest Amazon Linux 2023 AMI
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-vpc" })
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-public-${count.index + 1}" })
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-private-${count.index + 1}" })
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = merge(local.common_tags, { Name = "${local.name_prefix}-igw" })
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "${local.name_prefix}-nat-eip" })
}

resource "aws_nat_gateway" "ngw" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.igw]
  tags          = merge(local.common_tags, { Name = "${local.name_prefix}-ngw" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-public-rt" })
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.ngw.id
  }

  tags = merge(local.common_tags, { Name = "${local.name_prefix}-private-rt" })
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
    base              = 1
  }

  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 4
  }
}
```

---

## outputs.tf

```hcl
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}
```

---

## Terraform Workflow

```bash
cd infra/environments/production

# Initialize — downloads providers and sets up backend
terraform init

# Plan — shows what will be created/changed/destroyed
terraform plan -var-file=terraform.tfvars -out=tfplan

# Apply — executes the plan
terraform apply tfplan

# Destroy — removes all managed resources (irreversible!)
terraform destroy -var-file=terraform.tfvars

# Show current state
terraform show

# List resources in state
terraform state list

# Import existing resource into state
terraform import aws_vpc.main vpc-0123456789abcdef0

# Remove resource from state without destroying it
terraform state rm aws_vpc.main

# Format code
terraform fmt -recursive

# Validate configuration
terraform validate
```

---

## Workspaces (Staging vs Production)

```bash
# Create workspaces
terraform workspace new staging
terraform workspace new production

# Switch
terraform workspace select production

# In configuration, use workspace to vary resource names
# locals.tf:
# locals {
#   env = terraform.workspace  # "staging" or "production"
# }

# List workspaces
terraform workspace list
```

---

## Module — Reusable VPC Pattern

```hcl
# modules/vpc/main.tf
resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = var.name })
}
# ... subnets, route tables, etc.

# modules/vpc/variables.tf
variable "name"       { type = string }
variable "cidr_block" { type = string }
variable "tags"       { type = map(string); default = {} }

# modules/vpc/outputs.tf
output "vpc_id"             { value = aws_vpc.this.id }
output "private_subnet_ids" { value = aws_subnet.private[*].id }

# Using the module in environments/production/main.tf
module "vpc" {
  source     = "../../modules/vpc"
  name       = "production-vpc"
  cidr_block = "10.0.0.0/16"
  tags       = { Environment = "production", Team = "platform" }
}

resource "aws_ecs_cluster" "main" {
  name = "production-cluster"
  # Use module outputs
}
```

---

## Terraform AWS Authentication

```bash
# Option 1: Environment variables (CI/CD)
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"

# Option 2: AWS profile (~/.aws/credentials)
# In versions.tf:
# provider "aws" {
#   profile = "production"
#   region  = "us-east-1"
# }

# Option 3: IAM role (EC2, ECS, Lambda — no credentials needed)
# Terraform automatically uses the instance/task role

# Option 4: Assume a role (best practice for CI/CD)
# provider "aws" {
#   assume_role {
#     role_arn = "arn:aws:iam::123456789012:role/TerraformDeployRole"
#   }
# }
```

---

## References

- [Terraform AWS provider documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform language reference](https://developer.hashicorp.com/terraform/language)
- [Remote state with S3](https://developer.hashicorp.com/terraform/language/settings/backends/s3)
- [Terraform best practices](https://developer.hashicorp.com/terraform/cloud-docs/recommended-practices)
- [OpenTofu](https://opentofu.org/)
---

← [Previous: CDK](./cdk.md) | [Home](../../README.md) | [Next: AWS Projects →](../14-projects/README.md)
