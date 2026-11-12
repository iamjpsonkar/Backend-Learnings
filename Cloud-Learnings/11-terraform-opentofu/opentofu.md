← [Previous: Testing](./testing.md) | [Home](../README.md) | [Next: Ansible →](../12-ansible/README.md)

---

# OpenTofu

OpenTofu is the open-source fork of Terraform, created in response to HashiCorp's BSL license change in August 2023. It is maintained by the Linux Foundation and governed by the OpenTofu Steering Committee.

---

## Why OpenTofu?

| Concern | HashiCorp Terraform | OpenTofu |
|---------|--------------------|----|
| License | BSL 1.1 (restricts competing products) | MPL 2.0 (permissive open-source) |
| Governance | HashiCorp / IBM | Community-driven (Linux Foundation) |
| Registry | registry.terraform.io | registry.opentofu.org + compatible with TF registry |
| State format | Proprietary binary | Identical to Terraform |
| CLI | `terraform` | `tofu` |

OpenTofu is a drop-in replacement for Terraform ≤ 1.5. Configurations, providers, modules, and state files are compatible.

---

## Installation

```bash
# macOS (Homebrew)
brew install opentofu

# Linux (official installer)
curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh | sh

# Linux (apt)
curl -fsSL https://get.opentofu.org/opentofu.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/opentofu.gpg
echo "deb [signed-by=/etc/apt/keyrings/opentofu.gpg] https://packages.opentofu.org/opentofu/tofu/any/ any main" \
    | sudo tee /etc/apt/sources.list.d/opentofu.list
sudo apt-get update && sudo apt-get install tofu

# Verify
tofu version
```

---

## CLI: tofu vs terraform

```bash
# All terraform subcommands work with tofu
tofu init
tofu plan
tofu apply
tofu destroy
tofu fmt
tofu validate
tofu state list
tofu output
tofu workspace list
tofu test         # OpenTofu also supports the test framework
```

---

## Migrating from Terraform to OpenTofu

```bash
# 1. Install tofu
brew install opentofu

# 2. Run tofu init in your existing Terraform directory
#    OpenTofu reads terraform.lock.hcl and existing state
cd my-infra/
tofu init

# 3. Verify plan produces no unexpected changes
tofu plan

# 4. Update CI/CD: replace `terraform` with `tofu`

# 5. Update lock file (optional — tofu generates its own)
tofu providers lock \
    -platform=linux_amd64 \
    -platform=darwin_arm64

# Note: terraform.lock.hcl and .terraform.lock.hcl are both supported
```

---

## OpenTofu-Specific Features

### Provider-Defined Functions (1.7+)

Providers can expose custom functions callable in HCL.

```hcl
# Example: AWS provider function (hypothetical)
output "arn_parsed" {
  value = provider::aws::arn_parse("arn:aws:s3:::my-bucket")
}
```

### State Encryption (1.7+)

OpenTofu added native state encryption — encrypt state at rest without relying on backend-side encryption.

```hcl
terraform {
  encryption {
    key_provider "pbkdf2" "passphrase" {
      passphrase = var.state_passphrase
    }

    method "aes_gcm" "primary" {
      keys = key_provider.pbkdf2.passphrase
    }

    state {
      method = method.aes_gcm.primary
    }

    plan {
      method = method.aes_gcm.primary
    }
  }
}
```

### `removed` Block (1.7+, backported from TF 1.7)

```hcl
# Remove a resource from state without destroying it
removed {
  from = aws_s3_bucket.legacy

  lifecycle {
    destroy = false  # false = just remove from state, don't destroy
  }
}
```

---

## OpenTofu in CI/CD

### GitHub Actions

```yaml
# .github/workflows/opentofu.yml
name: OpenTofu

on:
  push:
    branches: [main]
    paths: ["infra/**"]
  pull_request:
    branches: [main]
    paths: ["infra/**"]

permissions:
  id-token: write
  contents: read

jobs:
  opentofu:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: infra

    steps:
      - uses: actions/checkout@v4

      - uses: opentofu/setup-opentofu@v1
        with:
          tofu_version: "1.7.x"

      - id: auth
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Init
        run: tofu init

      - name: Format check
        run: tofu fmt -check -recursive

      - name: Validate
        run: tofu validate

      - name: Plan
        id: plan
        run: tofu plan -out=tfplan -no-color 2>&1 | tee plan.txt

      - name: Apply (main branch only)
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: tofu apply -auto-approve tfplan
```

---

## OpenTofu vs Terraform Feature Matrix

| Feature | Terraform | OpenTofu |
|---------|-----------|----------|
| `terraform test` | 1.6+ | 1.6+ |
| Mock providers | 1.7+ | 1.7+ |
| `removed` block | 1.7+ | 1.7+ |
| Provider functions | 1.8+ | 1.7+ |
| State encryption | No native | 1.7+ |
| `tofu test` | N/A | 1.6+ |
| HCP Terraform | Yes | Partial (TACOS compatible) |

---

## Resources

- [OpenTofu documentation](https://opentofu.org/docs/)
- [OpenTofu GitHub](https://github.com/opentofu/opentofu)
- [Migration guide](https://opentofu.org/docs/intro/migration/)
- [OpenTofu Registry](https://registry.opentofu.org/)

---

← [Previous: Testing](./testing.md) | [Home](../README.md) | [Next: Ansible →](../12-ansible/README.md)
