← [Previous: Providers](./providers.md) | [Home](../README.md) | [Next: OpenTofu →](./opentofu.md)

---

# Testing Terraform

Testing infrastructure code prevents regressions and catches misconfigurations before they reach production.

---

## Built-in Validation

```bash
# Syntax check and schema validation (fast — no API calls)
terraform validate

# Format check
terraform fmt -check -recursive

# Speculative plan — requires valid credentials
terraform plan -detailed-exitcode
# Exit codes: 0=no changes, 1=error, 2=changes present
```

---

## Terraform Test Framework (v1.6+)

The native `terraform test` command runs `.tftest.hcl` files in the `tests/` directory.

```
.
├── main.tf
├── variables.tf
└── tests/
    ├── defaults.tftest.hcl
    └── production.tftest.hcl
```

```hcl
# tests/defaults.tftest.hcl
variables {
  bucket_name = "test-bucket-${random_id.suffix.hex}"
  environment = "development"
  region      = "us-east-1"
}

run "bucket_is_created" {
  command = plan  # Use "apply" to actually create resources

  assert {
    condition     = aws_s3_bucket.app.bucket == var.bucket_name
    error_message = "Bucket name does not match the variable."
  }
}

run "versioning_is_enabled" {
  command = plan

  assert {
    condition     = aws_s3_bucket_versioning.app.versioning_configuration[0].status == "Enabled"
    error_message = "Versioning must be enabled."
  }
}

run "public_access_is_blocked" {
  command = plan

  assert {
    condition     = aws_s3_bucket_public_access_block.app.block_public_acls == true
    error_message = "Public ACLs must be blocked."
  }

  assert {
    condition     = aws_s3_bucket_public_access_block.app.block_public_policy == true
    error_message = "Public bucket policy must be blocked."
  }
}
```

```bash
# Run tests
terraform test

# Run tests in a specific file
terraform test -filter=tests/defaults.tftest.hcl

# Run tests that apply (create real resources — costs money, clean up after)
terraform test -filter=tests/integration.tftest.hcl
```

---

## Mock Providers (Terraform 1.7+)

Mock providers allow tests to run without real cloud credentials.

```hcl
# tests/unit.tftest.hcl
mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
      arn        = "arn:aws:iam::123456789012:user/test"
    }
  }
}

run "naming_convention" {
  command = plan

  assert {
    condition     = startswith(aws_s3_bucket.app.bucket, "my-app-")
    error_message = "Bucket name must start with 'my-app-'."
  }
}
```

---

## Terratest (Go-based Integration Testing)

Terratest deploys real infrastructure and runs assertions against it.

```go
// tests/vpc_test.go
package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
    "github.com/aws/aws-sdk-go/aws/session"
    "github.com/aws/aws-sdk-go/service/ec2"
)

func TestVPCModule(t *testing.T) {
    t.Parallel()

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../modules/vpc",
        Vars: map[string]interface{}{
            "name":                 "test-vpc",
            "availability_zones":  []string{"us-east-1a", "us-east-1b"},
            "public_subnet_cidrs": []string{"10.0.0.0/24", "10.0.1.0/24"},
            "private_subnet_cidrs": []string{"10.0.10.0/24", "10.0.11.0/24"},
        },
    })

    // Always destroy at the end
    defer terraform.Destroy(t, terraformOptions)

    // Create the VPC
    terraform.InitAndApply(t, terraformOptions)

    // Get outputs
    vpcID := terraform.Output(t, terraformOptions, "vpc_id")
    privateSubnetIDs := terraform.OutputList(t, terraformOptions, "private_subnet_ids")

    // Assert
    assert.NotEmpty(t, vpcID)
    assert.Equal(t, 2, len(privateSubnetIDs))

    // Validate via AWS SDK
    sess := session.Must(session.NewSession())
    ec2Client := ec2.New(sess)
    result, _ := ec2Client.DescribeVpcs(&ec2.DescribeVpcsInput{
        VpcIds: []*string{&vpcID},
    })
    assert.Equal(t, "available", *result.Vpcs[0].State)
}
```

```bash
# Run terratest
cd tests
go test -v -run TestVPCModule -timeout 15m
```

---

## Static Analysis

### checkov (Security & Compliance)

```bash
# Install
pip install checkov

# Scan Terraform files
checkov -d . --framework terraform

# Scan and output as JUnit XML (for CI)
checkov -d . --framework terraform --output junitxml > checkov-report.xml

# Suppress a specific check with a comment
resource "aws_s3_bucket" "logs" {
  bucket = "my-app-logs"
  #checkov:skip=CKV_AWS_144:Cross-region replication not required for log bucket
}
```

### tfsec

```bash
# Install
brew install tfsec  # macOS

# Scan
tfsec .

# Ignore a check
resource "aws_security_group_rule" "allow_all_egress" {
  #tfsec:ignore:aws-ec2-no-public-egress-sgr
  type        = "egress"
  cidr_blocks = ["0.0.0.0/0"]
}
```

### tflint

```bash
# Install
brew install tflint

# Initialize (download ruleset plugins)
tflint --init

# Run
tflint --recursive
```

---

## CI Pipeline Example

```yaml
# .github/workflows/terraform-ci.yml
name: Terraform CI

on:
  pull_request:
    paths: ["infra/**"]

jobs:
  validate:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infra

    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.7.5"

      - name: Init
        run: terraform init -backend=false

      - name: Format check
        run: terraform fmt -check -recursive

      - name: Validate
        run: terraform validate

      - name: tflint
        uses: terraform-linters/setup-tflint@v4
        with:
          tflint_version: v0.50.0
      - run: tflint --init && tflint --recursive

      - name: checkov
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: infra
          framework: terraform
          output_format: sarif
          output_file_path: reports/checkov.sarif

      - name: Terraform test (mocked)
        run: terraform test
```

---

## References

- [terraform test command](https://developer.hashicorp.com/terraform/cli/commands/test)
- [Terratest](https://terratest.gruntwork.io/)
- [checkov](https://www.checkov.io/)
- [tfsec](https://aquasecurity.github.io/tfsec/)
- [tflint](https://github.com/terraform-linters/tflint)

---

← [Previous: Providers](./providers.md) | [Home](../README.md) | [Next: OpenTofu →](./opentofu.md)
