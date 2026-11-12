# Lab: Security Toolkit

Practice secrets management, identity, and security scanning.

## Objectives

1. Vault: write/read secrets, AppRole auth
2. Keycloak: create realm, configure OIDC client
3. Trivy: scan container images for vulnerabilities
4. Checkov: scan Terraform/IaC for misconfigurations
5. Hadolint: lint Dockerfiles
6. Detect and fix hardcoded secrets

## Prerequisites

```bash
./run.sh start security
```

## Service URLs

| Service | URL | Credentials |
|---|---|---|
| Vault UI | http://localhost:8200 | Token: dev-root-token |
| Keycloak Admin | http://localhost:8180/admin | admin/adminpassword123 |

## Vault CLI Setup

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-root-token
vault status
```

## Continue

See [tasks.md](tasks.md).
