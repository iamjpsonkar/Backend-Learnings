# Tasks — Security

## Task 1 — Vault: KV Secret Engine

- [ ] Check Vault status: `vault status`
- [ ] Enable KV v2 secret engine:
  ```bash
  vault secrets enable -path=secret kv-v2
  ```
- [ ] Write a secret:
  ```bash
  vault kv put secret/myapp/config db_password="mysecretpassword" api_key="abc123"
  ```
- [ ] Read the secret:
  ```bash
  vault kv get secret/myapp/config
  ```
- [ ] Get only the db_password:
  ```bash
  vault kv get -field=db_password secret/myapp/config
  ```
- [ ] Update the secret (creates new version):
  ```bash
  vault kv put secret/myapp/config db_password="newpassword" api_key="abc123"
  ```
- [ ] List versions:
  ```bash
  vault kv metadata get secret/myapp/config
  ```
- [ ] Get previous version:
  ```bash
  vault kv get -version=1 secret/myapp/config
  ```

## Task 2 — Vault: AppRole Authentication

- [ ] Enable AppRole auth method:
  ```bash
  vault auth enable approle
  ```
- [ ] Create a policy:
  ```bash
  vault policy write myapp-policy - << EOF
  path "secret/data/myapp/*" { capabilities = ["read"] }
  EOF
  ```
- [ ] Create an AppRole:
  ```bash
  vault write auth/approle/role/myapp policies="myapp-policy"
  ```
- [ ] Get Role ID and Secret ID:
  ```bash
  vault read auth/approle/role/myapp/role-id
  vault write -f auth/approle/role/myapp/secret-id
  ```
- [ ] Login with AppRole:
  ```bash
  vault write auth/approle/login role_id="ROLE_ID" secret_id="SECRET_ID"
  ```

## Task 3 — Keycloak: Create a Realm

- [ ] Open http://localhost:8180/admin
- [ ] Log in: admin/adminpassword123
- [ ] Create a new realm "my-realm"
- [ ] Create a client "my-app" (OpenID Connect)
- [ ] Set redirect URIs to `http://localhost:8000/*`
- [ ] Create a user "testuser" with password "testpass123"

## Task 4 — Trivy: Scan Images

```bash
# Scan a public image
docker exec -it cloud-learnings-trivy trivy image nginx:alpine

# Scan with JSON output
docker exec -it cloud-learnings-trivy trivy image --format json --output /reports/nginx-scan.json nginx:alpine

# Filter by severity
docker exec -it cloud-learnings-trivy trivy image --severity HIGH,CRITICAL nginx:alpine

# Scan a local image (if apps built)
docker exec -it cloud-learnings-trivy trivy image cloud-learnings-sample-api:local
```

- [ ] Identify HIGH and CRITICAL vulnerabilities
- [ ] Note which packages have fixes available

## Task 5 — Checkov: Scan IaC

```bash
# Scan Terraform configs
docker exec -it cloud-learnings-checkov checkov -d /workspace/terraform

# Scan with specific check
docker exec -it cloud-learnings-checkov checkov -d /workspace --check CKV_AWS_18

# Generate JSON report
docker exec -it cloud-learnings-checkov checkov -d /workspace -o json > /reports/checkov-report.json
```

- [ ] Review the list of failed checks
- [ ] Fix one finding in the Terraform code

## Task 6 — Hadolint: Lint Dockerfiles

```bash
docker exec -it cloud-learnings-hadolint hadolint /workspace/sample-api/Dockerfile
docker exec -it cloud-learnings-hadolint hadolint /workspace/broken-apps/broken-api/Dockerfile
```

- [ ] Note which rules are violated
- [ ] Fix at least one issue in the Dockerfile

## Task 7 — Find and fix a hardcoded secret

Look in `apps/` for any hardcoded credentials. Practice:
- Using environment variables instead
- Using Vault to retrieve secrets at runtime
- Using `.env` file (never committed)
