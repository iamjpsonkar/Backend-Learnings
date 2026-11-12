# Broken Scenario: Terraform Apply Fails

**Difficulty**: Intermediate
**Profile**: `aws iac`

---

## Scenario

A Terraform config was committed and CI is failing on `terraform apply`. The config "looked fine" in review. Your job: make it apply cleanly.

---

## Setup

```bash
./run.sh start aws iac
```

Copy the broken config:
```bash
cp practice/broken-scenarios/broken-terraform/broken-main.tf \
   /tmp/broken-terraform/main.tf
```

---

## Broken config

Save as `broken-main.tf`:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = var.region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3 = "http://localstack:4566"
  }
}

# Bug 1: references variable that doesn't exist
resource "aws_s3_bucket" "data" {
  bucket = "${var.project}-${var.env}-data"
}

# Bug 2: depends_on creates circular dependency
resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  depends_on = [aws_s3_bucket.backup]  # ← circular

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "backup" {
  bucket = "${var.project}-backup"
  depends_on = [aws_s3_bucket_versioning.data]  # ← circular
}

# Bug 3: wrong attribute name
resource "aws_dynamodb_table" "state" {
  table_name   = "app-state"  # ← wrong, should be "name"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}
```

---

## Tasks

1. Run `terraform init` and `terraform validate` — what errors appear?
2. Fix bug 1: the missing variable
3. Fix bug 2: the circular dependency
4. Fix bug 3: the wrong attribute
5. Run `terraform apply -auto-approve` — it should succeed

---

## Investigation commands

```bash
# In the iac container or with local terraform
terraform init
terraform validate
terraform plan   # reveals attribute errors even if validate passes
```

---

## Solution validation

```bash
terraform apply -auto-approve
# Apply complete! Resources: 4 added, 0 changed, 0 destroyed.

terraform output  # if outputs defined
```
