# Commands — Security

## Vault

```bash
# Environment setup
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-root-token

# Or use vault CLI container
docker exec -it cloud-learnings-vault sh
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-root-token

# Status
vault status

# KV operations
vault kv put secret/myapp/config key=value
vault kv get secret/myapp/config
vault kv get -field=key secret/myapp/config
vault kv list secret/myapp/
vault kv delete secret/myapp/config
vault kv undelete -versions=1 secret/myapp/config

# Auth methods
vault auth enable approle
vault auth list

# Policies
vault policy write mypolicy - << 'EOF'
path "secret/data/*" { capabilities = ["read"] }
EOF
vault policy list
vault policy read mypolicy

# Token operations
vault token create -policy=mypolicy -ttl=1h
vault token lookup
vault token revoke <token>
```

## Trivy

```bash
# Scan image
docker exec -it cloud-learnings-trivy trivy image nginx:alpine

# Scan with severity filter
docker exec -it cloud-learnings-trivy trivy image \
  --severity HIGH,CRITICAL \
  --no-progress \
  nginx:alpine

# Scan filesystem
docker exec -it cloud-learnings-trivy trivy fs /workspace

# Scan IaC (terraform, dockerfile, kubernetes manifests)
docker exec -it cloud-learnings-trivy trivy config /workspace

# JSON output
docker exec -it cloud-learnings-trivy trivy image \
  --format json \
  --output /reports/scan.json \
  nginx:alpine
```

## Checkov

```bash
# Scan directory
docker exec -it cloud-learnings-checkov checkov -d /workspace

# Specific framework
docker exec -it cloud-learnings-checkov checkov -d /workspace --framework terraform

# Skip checks
docker exec -it cloud-learnings-checkov checkov -d /workspace --skip-check CKV_AWS_123

# List all checks
docker exec -it cloud-learnings-checkov checkov --list
```

## Hadolint

```bash
# Lint Dockerfile
docker exec -it cloud-learnings-hadolint hadolint /workspace/sample-api/Dockerfile

# Ignore specific rules
docker exec -it cloud-learnings-hadolint hadolint \
  --ignore DL3008 \
  /workspace/sample-api/Dockerfile

# JSON output
docker exec -it cloud-learnings-hadolint hadolint \
  --format json \
  /workspace/sample-api/Dockerfile
```
