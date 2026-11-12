# OpenTofu — LocalStack Practice
# Functionally identical to Terraform but uses OpenTofu CLI
# Run via: ./run.sh lab start terraform-opentofu

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state for practice (no backend config needed)
  backend "local" {
    path = "/workspace/opentofu.tfstate"
  }
}

provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3       = var.localstack_endpoint
    sqs      = var.localstack_endpoint
    sns      = var.localstack_endpoint
    dynamodb = var.localstack_endpoint
    iam      = var.localstack_endpoint
    sts      = var.localstack_endpoint
  }
}

# ── S3 Buckets ───────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "app_data" {
  bucket = "${var.project_name}-app-data"

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-app-data"
    Purpose = "application-data"
  })
}

resource "aws_s3_bucket_versioning" "app_data" {
  bucket = aws_s3_bucket.app_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "backups" {
  bucket = "${var.project_name}-backups"

  tags = merge(var.common_tags, {
    Name    = "${var.project_name}-backups"
    Purpose = "backups"
  })
}

# ── SQS Queues ───────────────────────────────────────────────────────────────

resource "aws_sqs_queue" "dead_letter" {
  name                      = "${var.project_name}-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = var.common_tags
}

resource "aws_sqs_queue" "orders" {
  name                       = "${var.project_name}-orders"
  visibility_timeout_seconds = 30
  message_retention_seconds  = 345600 # 4 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = 3
  })

  tags = var.common_tags
}

# ── SNS Topics ───────────────────────────────────────────────────────────────

resource "aws_sns_topic" "events" {
  name = "${var.project_name}-events"
  tags = var.common_tags
}

resource "aws_sns_topic_subscription" "events_to_orders_queue" {
  topic_arn = aws_sns_topic.events.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.orders.arn
}

# ── DynamoDB Tables ──────────────────────────────────────────────────────────

resource "aws_dynamodb_table" "sessions" {
  name           = "${var.project_name}-sessions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = var.common_tags
}

resource "aws_dynamodb_table" "inventory" {
  name         = "${var.project_name}-inventory"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "product_id"
  range_key    = "warehouse_id"

  attribute {
    name = "product_id"
    type = "S"
  }

  attribute {
    name = "warehouse_id"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  global_secondary_index {
    name            = "category-index"
    hash_key        = "category"
    range_key       = "product_id"
    projection_type = "ALL"
  }

  tags = var.common_tags
}
