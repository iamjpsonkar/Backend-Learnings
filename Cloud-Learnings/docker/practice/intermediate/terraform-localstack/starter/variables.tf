variable "environment" {
  description = "Environment name"
  type        = string
  default     = "lab"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "cloud-learnings"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}
