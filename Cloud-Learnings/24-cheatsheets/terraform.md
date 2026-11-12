← [Previous: kubectl](./kubectl.md) | [Home](../README.md) | [Next: Docker →](./docker.md)

---

# Terraform Cheatsheet

```hcl
# ── INIT / PLAN / APPLY ────────────────────────────────────────────────────────
terraform init                          # initialize: download providers, configure backend
terraform init -upgrade                 # upgrade provider versions
terraform init -reconfigure             # re-initialize (e.g., backend changed)
terraform init -migrate-state           # migrate state to new backend

terraform validate                      # check syntax and configuration
terraform fmt                           # format code (in-place)
terraform fmt -check                    # check formatting (CI)
terraform fmt -recursive                # format all .tf files recursively

terraform plan                          # show what will change
terraform plan -out=tfplan              # save plan to file (use in CI)
terraform plan -var="env=prod"          # pass variable
terraform plan -var-file=prod.tfvars    # use variable file
terraform plan -target=aws_ecs_service.api  # plan only specific resource

terraform apply                         # apply (with confirmation prompt)
terraform apply tfplan                  # apply saved plan (no prompt)
terraform apply -auto-approve           # skip confirmation (CI/automation)
terraform apply -target=aws_ecs_service.api  # apply only specific resource

terraform destroy                       # destroy all resources
terraform destroy -target=aws_instance.web  # destroy specific resource
terraform destroy -auto-approve         # no prompt

# ── STATE ──────────────────────────────────────────────────────────────────────
terraform show                          # show current state
terraform show tfplan                   # show a saved plan
terraform state list                    # list all resources in state
terraform state show aws_instance.web   # show specific resource details

# Move resource (rename without destroy/recreate)
terraform state mv aws_instance.web aws_instance.web_server

# Remove resource from state (without destroying)
terraform state rm aws_s3_bucket.temp

# Import existing resource into state
terraform import aws_s3_bucket.existing my-existing-bucket

# Pull/push state (for manual operations)
terraform state pull > backup.tfstate
terraform state push backup.tfstate

# ── WORKSPACES ─────────────────────────────────────────────────────────────────
terraform workspace list                # list workspaces
terraform workspace show                # current workspace
terraform workspace new staging         # create workspace
terraform workspace select prod         # switch workspace
terraform workspace delete staging      # delete workspace

# In code: reference workspace name
resource "aws_s3_bucket" "data" {
  bucket = "myapp-${terraform.workspace}-data"
}

# ── OUTPUTS ────────────────────────────────────────────────────────────────────
terraform output                        # show all outputs
terraform output alb_dns_name           # show specific output
terraform output -json                  # JSON format (useful in scripts)
ALB_DNS=$(terraform output -raw alb_dns_name)  # use in shell

# ── DEBUGGING ──────────────────────────────────────────────────────────────────
TF_LOG=DEBUG terraform plan             # verbose logging
TF_LOG=DEBUG terraform plan 2>debug.log # save logs to file
TF_LOG_PATH=./debug.log terraform plan  # alternative

# Refresh state to sync with real infrastructure
terraform refresh

# Graph dependencies
terraform graph | dot -Tsvg > graph.svg

# ── LOCKING ────────────────────────────────────────────────────────────────────
terraform force-unlock LOCK_ID          # release stuck state lock
# Get LOCK_ID from error message or DynamoDB:
# aws dynamodb scan --table-name terraform-locks

# ── COMMON PATTERNS ────────────────────────────────────────────────────────────

# ── variables.tf
variable "environment" {
  description = "Deployment environment"
  type        = string
  validation {
    condition     = contains(["prod", "staging", "dev"], var.environment)
    error_message = "environment must be prod, staging, or dev"
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}

# ── locals.tf
locals {
  common_tags = merge(var.tags, {
    environment = var.environment
    managed_by  = "terraform"
    project     = var.project
  })
  is_prod = var.environment == "prod"
}

# ── Dynamic blocks
resource "aws_security_group" "web" {
  name   = "web-sg"
  vpc_id = var.vpc_id

  dynamic "ingress" {
    for_each = var.allowed_ports
    content {
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }
}

# ── Count and for_each
resource "aws_subnet" "private" {
  count             = length(var.private_cidr_blocks)
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_cidr_blocks[count.index]
  availability_zone = var.availability_zones[count.index]
}

resource "aws_iam_user" "team" {
  for_each = toset(["alice", "bob", "carol"])
  name     = each.key
}

# ── Data sources
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

data "aws_caller_identity" "current" {}
# Use: data.aws_caller_identity.current.account_id

# ── Conditional resources
resource "aws_db_instance" "replica" {
  count               = var.environment == "prod" ? 1 : 0
  # ... only creates in prod
}

# ── depends_on (explicit dependency)
resource "aws_ecs_service" "api" {
  depends_on = [aws_lb_listener.https]  # ensure listener exists before service
}

# ── lifecycle
resource "aws_s3_bucket" "data" {
  lifecycle {
    prevent_destroy = true             # prevent accidental delete
    ignore_changes  = [tags]           # ignore tag drift
    create_before_destroy = true       # rolling replace
  }
}

# ── Provider aliases (multi-region / multi-account)
provider "aws" {
  alias  = "dr"
  region = "us-west-2"
}

resource "aws_s3_bucket" "dr_backup" {
  provider = aws.dr
  bucket   = "myapp-dr-backup"
}
```

---

← [Previous: kubectl](./kubectl.md) | [Home](../README.md) | [Next: Docker →](./docker.md)
