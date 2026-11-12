terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "local" {
    path = "terraform.tfstate"
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
    s3       = "http://localhost:4566"
    sqs      = "http://localhost:4566"
    sns      = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
  }
}

# TODO: Create an S3 bucket with versioning enabled

# TODO: Create an SQS dead-letter queue

# TODO: Create a main SQS queue with the DLQ configured

# TODO: Create an SNS topic

# TODO: Subscribe the SQS queue to the SNS topic
