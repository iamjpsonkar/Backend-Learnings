variable "environment" {
  description = "Deployment environment (lab, dev, staging, prod)"
  type        = string
  default     = "lab"
  validation {
    condition     = contains(["lab", "dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: lab, dev, staging, prod."
  }
}

variable "project_name" {
  description = "Project name for resource naming and tagging"
  type        = string
  default     = "cloud-learnings"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
