← [Previous: Kubernetes Troubleshooting](../10-kubernetes/troubleshooting.md) | [Home](../README.md) | [Next: Getting Started →](./getting-started.md)

---

# Terraform / OpenTofu

Terraform (by HashiCorp) and OpenTofu (the open-source fork) are declarative Infrastructure-as-Code tools that manage cloud and on-premises resources using HCL (HashiCorp Configuration Language).

---

## Why Infrastructure as Code?

| Manual provisioning | IaC |
|---------------------|-----|
| Error-prone, inconsistent | Repeatable, idempotent |
| Hard to review | Version-controlled, diff-able |
| No audit trail | Git history is the audit trail |
| Slow, tribal knowledge | Self-documenting, onboarding-friendly |

---

## Terraform vs OpenTofu

| Feature | Terraform | OpenTofu |
|---------|-----------|----------|
| License | BSL 1.1 (since v1.6) | MPL 2.0 (fully open-source) |
| Maintained by | HashiCorp / IBM | OpenTofu community (Linux Foundation) |
| CLI binary | `terraform` | `tofu` |
| Compatibility | — | Drop-in replacement for Terraform ≤ 1.5 |
| Registry | registry.terraform.io | registry.opentofu.org |
| State format | Same | Same |

---

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Provider** | Plugin that authenticates to and manages a cloud/service API |
| **Resource** | Infrastructure object declared in HCL (VM, bucket, DNS record) |
| **Data source** | Read-only query of existing infrastructure |
| **Module** | Reusable package of resources with inputs and outputs |
| **State** | JSON snapshot of managed resources — stored locally or remotely |
| **Workspace** | Isolated state instance within the same configuration |

---

## File Structure

```
infra/
├── main.tf            # Core resources
├── variables.tf       # Input variables
├── outputs.tf         # Output values
├── versions.tf        # Required providers + backend config
├── locals.tf          # Computed local values
├── data.tf            # Data sources
└── modules/
    └── vpc/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

---

## Core Workflow

```bash
# Initialize (download providers + modules, configure backend)
terraform init

# Preview changes — never modifies infrastructure
terraform plan -out=tfplan

# Apply the saved plan
terraform apply tfplan

# Destroy all managed resources
terraform destroy

# Format all .tf files
terraform fmt -recursive

# Validate syntax and configuration
terraform validate

# Show current state
terraform show

# List managed resources
terraform state list

# Import existing resource into state
terraform import aws_s3_bucket.my_bucket my-bucket-name

# Refresh state from real infrastructure
terraform refresh
```

---

## Topics

| File | Topics |
|------|--------|
| [Getting Started](./getting-started.md) | Install, first config, HCL syntax, providers |
| [State Management](./state.md) | Backends, remote state, locking, workspaces |
| [Modules](./modules.md) | Writing modules, the registry, composition |
| [Variables & Outputs](./variables-outputs.md) | Variables, locals, outputs, sensitive values |
| [Expressions](./expressions.md) | for_each, count, dynamic, conditionals, functions |
| [Providers](./providers.md) | Multi-provider, aliases, version pinning |
| [Testing](./testing.md) | validate, plan checks, terratest, checkov |
| [OpenTofu](./opentofu.md) | OpenTofu specifics, migration from Terraform |

---

## References

- [Terraform documentation](https://developer.hashicorp.com/terraform/docs)
- [OpenTofu documentation](https://opentofu.org/docs/)
- [Terraform Registry](https://registry.terraform.io/)
- [OpenTofu Registry](https://registry.opentofu.org/)

---

← [Previous: Kubernetes Troubleshooting](../10-kubernetes/troubleshooting.md) | [Home](../README.md) | [Next: Getting Started →](./getting-started.md)
