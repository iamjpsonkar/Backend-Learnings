variable "project_name" {
  description = "Prefix for all resource names"
  type        = string
  default     = "cloudlab"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.project_name))
    error_message = "project_name must be 3-20 lowercase alphanumeric characters or hyphens, starting with a letter."
  }
}

variable "aws_region" {
  description = "AWS region (cosmetic for LocalStack)"
  type        = string
  default     = "us-east-1"
}

variable "localstack_endpoint" {
  description = "LocalStack endpoint URL"
  type        = string
  default     = "http://localstack:4566"
}

variable "common_tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default = {
    project     = "cloud-learnings-lab"
    managed_by  = "opentofu"
    environment = "local"
  }
}
