← [Previous: State Management](./state.md) | [Home](../README.md) | [Next: Variables & Outputs →](./variables-outputs.md)

---

# Modules

Modules are reusable packages of Terraform resources. They allow you to abstract infrastructure patterns, enforce standards, and share configurations across teams and projects.

---

## Module Structure

```
modules/
└── vpc/
    ├── main.tf        # Resources
    ├── variables.tf   # Input variables
    ├── outputs.tf     # Output values
    ├── versions.tf    # Required providers (no backend block)
    └── README.md      # Usage docs
```

---

## Writing a Module

```hcl
# modules/vpc/variables.tf
variable "name" {
  type        = string
  description = "VPC name — used as prefix for all resources"
}

variable "cidr_block" {
  type        = string
  description = "Primary IPv4 CIDR block"
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.cidr_block, 0))
    error_message = "cidr_block must be a valid CIDR notation."
  }
}

variable "availability_zones" {
  type        = list(string)
  description = "List of AZs to create subnets in"
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "CIDRs for private subnets (one per AZ)"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "CIDRs for public subnets (one per AZ)"
}

variable "enable_nat_gateway" {
  type        = bool
  description = "Create NAT Gateways for private subnets"
  default     = true
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default     = {}
}
```

```hcl
# modules/vpc/main.tf
locals {
  common_tags = merge(var.tags, { Module = "vpc", Name = var.name })
}

resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = merge(local.common_tags, { Name = var.name })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${var.name}-igw" })
}

resource "aws_subnet" "public" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  map_public_ip_on_launch = true
  tags = merge(local.common_tags, {
    Name = "${var.name}-public-${var.availability_zones[count.index]}"
    Tier = "public"
  })
}

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(local.common_tags, {
    Name = "${var.name}-private-${var.availability_zones[count.index]}"
    Tier = "private"
  })
}

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? length(var.availability_zones) : 0
  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "${var.name}-nat-eip-${count.index}" })
}

resource "aws_nat_gateway" "this" {
  count         = var.enable_nat_gateway ? length(var.availability_zones) : 0
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = merge(local.common_tags, { Name = "${var.name}-nat-${count.index}" })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${var.name}-rt-public" })

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
}

resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.this.id
  tags   = merge(local.common_tags, { Name = "${var.name}-rt-private-${count.index}" })

  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.this[count.index].id
    }
  }
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}
```

```hcl
# modules/vpc/outputs.tf
output "vpc_id" {
  value       = aws_vpc.this.id
  description = "VPC ID"
}

output "public_subnet_ids" {
  value       = aws_subnet.public[*].id
  description = "List of public subnet IDs"
}

output "private_subnet_ids" {
  value       = aws_subnet.private[*].id
  description = "List of private subnet IDs"
}

output "nat_gateway_ids" {
  value       = aws_nat_gateway.this[*].id
  description = "List of NAT Gateway IDs"
}
```

---

## Calling a Module

```hcl
# root/main.tf
module "vpc" {
  source = "./modules/vpc"   # local path
  # source = "git::https://github.com/my-org/tf-modules.git//modules/vpc?ref=v1.2.0"
  # source = "app.terraform.io/my-org/vpc/aws"   # Terraform Cloud registry

  name                 = "my-app-production"
  cidr_block           = "10.0.0.0/16"
  availability_zones   = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnet_cidrs  = ["10.0.0.0/24", "10.0.1.0/24", "10.0.2.0/24"]
  private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]
  enable_nat_gateway   = true

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Use module outputs in other resources
resource "aws_eks_cluster" "app" {
  name = "my-app-production"
  vpc_config {
    subnet_ids = module.vpc.private_subnet_ids
  }
}
```

---

## Registry Modules

```hcl
# Public registry module — pinned to a version
module "s3_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> 4.0"

  bucket        = "my-app-prod-data"
  force_destroy = false

  versioning = {
    enabled = true
  }

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }
}

# Popular community modules:
# - terraform-aws-modules/vpc/aws
# - terraform-aws-modules/eks/aws
# - terraform-aws-modules/rds/aws
# - Azure/aks/azurerm
# - GoogleCloudPlatform/kubernetes-engine/google
```

---

## Module Versioning and Source Types

```hcl
# Local path (development)
source = "./modules/vpc"

# Git — tag
source = "git::https://github.com/my-org/tf-modules.git//modules/vpc?ref=v2.1.0"

# Git — branch (avoid in production — not immutable)
source = "git::https://github.com/my-org/tf-modules.git//modules/vpc?ref=main"

# Terraform Registry (public or private)
source  = "hashicorp/consul/aws"
version = "~> 0.5"

# S3 bucket
source = "s3::https://s3.amazonaws.com/my-tf-modules/vpc.zip"
```

---

## Best Practices

- Pin module versions (`version = "~> 4.0"`) — never use floating references in production
- Keep modules focused — a module should do one thing well
- All variables must have `type` and `description`
- Sensitive outputs must be marked `sensitive = true`
- Don't put backend configuration in modules
- Test modules independently before composing

---

## References

- [Module documentation](https://developer.hashicorp.com/terraform/language/modules)
- [Module composition](https://developer.hashicorp.com/terraform/language/modules/develop/composition)
- [Terraform Registry](https://registry.terraform.io/browse/modules)

---

← [Previous: State Management](./state.md) | [Home](../README.md) | [Next: Variables & Outputs →](./variables-outputs.md)
