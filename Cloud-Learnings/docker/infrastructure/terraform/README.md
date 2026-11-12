# Terraform Infrastructure

This directory contains Terraform configurations targeting LocalStack.

## Quick Start

```bash
# Start required services
./run.sh start aws

# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply -auto-approve

# View outputs
terraform output

# Destroy
terraform destroy -auto-approve
```

## Using MinIO as S3-compatible Terraform Backend

Instead of local state, use MinIO for a realistic remote backend experience:

```hcl
terraform {
  backend "s3" {
    bucket                      = "lab-terraform-state"
    key                         = "cloud-learnings/terraform.tfstate"
    region                      = "us-east-1"
    endpoint                    = "http://localhost:9001"
    access_key                  = "minioadmin"
    secret_key                  = "minioadmin123"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    force_path_style            = true
  }
}
```

First create the bucket in MinIO:
```bash
docker exec cloud-learnings-minio \
  mc mb local/lab-terraform-state
```

## Resources Created

- S3 bucket: `{project}-{env}-data` (with versioning)
- S3 bucket: `{project}-{env}-logs`
- SQS queue: `{project}-{env}-queue` (with DLQ)
- SNS topic: `{project}-{env}-events` (subscribed to SQS)
- DynamoDB table: `{project}-{env}-items`
