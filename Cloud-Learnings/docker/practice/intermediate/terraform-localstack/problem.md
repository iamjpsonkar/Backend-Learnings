# Problem: Terraform with LocalStack

## Goal

Provision AWS-like infrastructure using Terraform against LocalStack — without touching real AWS.

## Requirements

1. Write a Terraform configuration that creates:
   - 1 S3 bucket with versioning enabled
   - 1 SQS queue with a dead-letter queue
   - 1 DynamoDB table for Terraform state locking (optional extension)
   - 1 SNS topic subscribed to the SQS queue

2. Use the LocalStack Terraform provider configuration:
   ```hcl
   provider "aws" {
     region                      = "us-east-1"
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
   ```

3. Use a local backend for state:
   ```hcl
   terraform {
     backend "local" {
       path = "terraform.tfstate"
     }
   }
   ```

4. Use variables for:
   - `environment` (default: "lab")
   - `project_name` (default: "cloud-learnings")
   - `aws_region` (default: "us-east-1")

5. Use outputs to print all created resource ARNs/URLs

## Prerequisites

```bash
./run.sh start aws
./run.sh start iac
```

## Constraints

- All resources must have a `project` tag
- Use `terraform.tfvars` for variable values
- Do not hardcode resource names — derive them from variables
- Run `terraform destroy` cleanly at the end

## Validation

```bash
terraform plan   # Should show resources to create
terraform apply  # Should create successfully
terraform output # Should show resource URLs/ARNs

# Verify resources exist in LocalStack
aws --endpoint-url=http://localhost:4566 s3 ls
aws --endpoint-url=http://localhost:4566 sqs list-queues
aws --endpoint-url=http://localhost:4566 sns list-topics

terraform destroy  # Should destroy cleanly
```

## Extension Challenges

1. Store Terraform state in MinIO (S3-compatible backend)
2. Create a Lambda function triggered by SQS
3. Add a CloudWatch log group for the Lambda
4. Module: extract the messaging resources into a reusable module
