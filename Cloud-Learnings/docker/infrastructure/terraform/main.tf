terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state backend for lab use
  # For MinIO S3-compatible backend, see README.md
  backend "local" {
    path = "terraform.tfstate"
  }
}

# Configure AWS provider to use LocalStack
provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3         = "http://localhost:4566"
    sqs        = "http://localhost:4566"
    sns        = "http://localhost:4566"
    dynamodb   = "http://localhost:4566"
    iam        = "http://localhost:4566"
    lambda     = "http://localhost:4566"
    kms        = "http://localhost:4566"
    cloudwatch = "http://localhost:4566"
    logs       = "http://localhost:4566"
  }
}

# =============================================================================
# S3 Buckets
# =============================================================================
resource "aws_s3_bucket" "app_data" {
  bucket = "${var.project_name}-${var.environment}-data"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "app_data" {
  bucket = aws_s3_bucket.app_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "app_logs" {
  bucket = "${var.project_name}-${var.environment}-logs"
  tags   = local.common_tags
}

# =============================================================================
# SQS Queues
# =============================================================================
resource "aws_sqs_queue" "dlq" {
  name                       = "${var.project_name}-${var.environment}-dlq"
  message_retention_seconds  = 1209600  # 14 days
  tags                       = local.common_tags
}

resource "aws_sqs_queue" "main" {
  name                       = "${var.project_name}-${var.environment}-queue"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 86400
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
  tags = local.common_tags
}

# =============================================================================
# SNS Topics
# =============================================================================
resource "aws_sns_topic" "events" {
  name = "${var.project_name}-${var.environment}-events"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "events_to_sqs" {
  topic_arn = aws_sns_topic.events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.main.arn
}

# =============================================================================
# DynamoDB
# =============================================================================
resource "aws_dynamodb_table" "items" {
  name         = "${var.project_name}-${var.environment}-items"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  tags = local.common_tags
}

# =============================================================================
# Locals
# =============================================================================
locals {
  common_tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}
