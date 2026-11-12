← [Previous: Modules](./modules.md) | [Home](../README.md) | [Next: Expressions →](./expressions.md)

---

# Variables and Outputs

---

## Input Variables

```hcl
# Simple types
variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "instance_count" {
  type        = number
  description = "Number of instances to create"
  default     = 2
}

variable "enable_monitoring" {
  type        = bool
  description = "Enable detailed CloudWatch monitoring"
  default     = true
}

# List
variable "availability_zones" {
  type        = list(string)
  description = "AZs to deploy into"
  default     = ["us-east-1a", "us-east-1b"]
}

# Map
variable "instance_types" {
  type = map(string)
  description = "Instance type per environment"
  default = {
    development = "t3.small"
    staging     = "t3.medium"
    production  = "t3.large"
  }
}

# Object (structured type)
variable "database_config" {
  type = object({
    engine         = string
    engine_version = string
    instance_class = string
    storage_gb     = number
    multi_az       = bool
  })
  description = "RDS database configuration"
  default = {
    engine         = "postgres"
    engine_version = "16.2"
    instance_class = "db.t3.medium"
    storage_gb     = 100
    multi_az       = false
  }
}

# List of objects
variable "allowed_cidrs" {
  type = list(object({
    cidr        = string
    description = string
  }))
  description = "CIDRs allowed to access the load balancer"
  default     = []
}
```

---

## Variable Validation

```hcl
variable "environment" {
  type        = string
  description = "Deployment environment"

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "environment must be one of: development, staging, production."
  }
}

variable "bucket_name" {
  type        = string
  description = "S3 bucket name"

  validation {
    condition     = length(var.bucket_name) >= 3 && length(var.bucket_name) <= 63
    error_message = "bucket_name must be between 3 and 63 characters."
  }

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9\\-]*[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "instance_count" {
  type        = number
  description = "Number of instances"

  validation {
    condition     = var.instance_count >= 1 && var.instance_count <= 100
    error_message = "instance_count must be between 1 and 100."
  }
}
```

---

## Sensitive Variables

```hcl
variable "db_password" {
  type        = string
  description = "Database master password"
  sensitive   = true  # Never printed in plan/apply output or logs
}

variable "api_key" {
  type      = string
  sensitive = true
}
```

```bash
# Pass sensitive values via environment variables (not CLI flags — those appear in history)
export TF_VAR_db_password="super-secret-password"
export TF_VAR_api_key="sk-abc123"
terraform apply
```

---

## Locals

```hcl
locals {
  # Simple computation
  name_prefix = "${var.project}-${var.environment}"

  # Conditional value
  instance_type = var.environment == "production" ? "t3.large" : "t3.small"

  # Derived map
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
    CreatedAt   = timestamp()
  }

  # Select from map
  vpc_cidr = {
    development = "10.0.0.0/16"
    staging     = "10.1.0.0/16"
    production  = "10.2.0.0/16"
  }[var.environment]

  # Flatten nested structures
  all_subnets = flatten([
    for vpc in var.vpcs : vpc.subnet_cidrs
  ])

  # Build a map from a list
  az_index = {
    for i, az in var.availability_zones : az => i
  }
}
```

---

## Outputs

```hcl
# outputs.tf

# Simple output
output "vpc_id" {
  value       = aws_vpc.main.id
  description = "VPC ID"
}

# Sensitive output (value hidden in CLI output, but stored in state)
output "db_connection_string" {
  value       = "postgresql://${var.db_user}:${var.db_password}@${aws_db_instance.main.endpoint}/${var.db_name}"
  description = "PostgreSQL connection string"
  sensitive   = true
}

# Complex output
output "subnet_info" {
  value = {
    public_ids  = aws_subnet.public[*].id
    private_ids = aws_subnet.private[*].id
    public_cidrs = aws_subnet.public[*].cidr_block
  }
  description = "Subnet IDs and CIDRs by tier"
}

# Conditional output
output "nat_gateway_ip" {
  value       = var.enable_nat_gateway ? aws_eip.nat[0].public_ip : null
  description = "NAT Gateway public IP (null if NAT disabled)"
}
```

```bash
# Print all outputs
terraform output

# Print a specific output (raw value, no quotes — useful for scripting)
terraform output -raw vpc_id

# Print as JSON
terraform output -json

# Access outputs from another root module (via terraform_remote_state)
```

---

## terraform_remote_state (Cross-Module Outputs)

```hcl
# Read outputs from another Terraform configuration's state
data "terraform_remote_state" "network" {
  backend = "s3"

  config = {
    bucket = "my-app-tf-state"
    key    = "network/terraform.tfstate"
    region = "us-east-1"
  }
}

# Use the outputs
resource "aws_eks_cluster" "app" {
  name = "my-app"

  vpc_config {
    subnet_ids = data.terraform_remote_state.network.outputs.private_subnet_ids
  }
}
```

---

## Variable Precedence (highest → lowest)

1. `-var="key=value"` or `-var-file=file.tfvars` on CLI
2. `*.auto.tfvars` or `*.auto.tfvars.json` files in config dir
3. `terraform.tfvars` or `terraform.tfvars.json` in config dir
4. `TF_VAR_variable_name` environment variables
5. `default` value in `variable` block

---

## References

- [Input variables](https://developer.hashicorp.com/terraform/language/values/variables)
- [Local values](https://developer.hashicorp.com/terraform/language/values/locals)
- [Output values](https://developer.hashicorp.com/terraform/language/values/outputs)

---

← [Previous: Modules](./modules.md) | [Home](../README.md) | [Next: Expressions →](./expressions.md)
