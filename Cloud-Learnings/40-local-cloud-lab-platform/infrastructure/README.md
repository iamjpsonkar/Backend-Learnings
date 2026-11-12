# Infrastructure

Terraform and Ansible configurations for the lab platform's own infrastructure.

## Purpose

This directory contains IaC for managing the platform itself — not lab exercises.
Lab exercises are in `labs/`.

## Structure

```
infrastructure/
├── terraform/
│   └── minio-backend/     # Terraform config to use local MinIO as state backend
└── ansible/
    └── platform-setup/    # Ansible playbook for setting up the host environment
```

## Terraform Backend (MinIO)

Use local MinIO as a Terraform state backend for IaC labs:

```hcl
terraform {
  backend "s3" {
    bucket                      = "terraform-state"
    key                         = "my-lab/terraform.tfstate"
    region                      = "us-east-1"
    endpoint                    = "http://localhost:9000"
    access_key                  = "labadmin"
    secret_key                  = "labpassword123"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    force_path_style            = true
  }
}
```
