# Secure Platform — Advanced

**Difficulty**: Advanced
**Profile**: `core apps security`
**Time estimate**: 3–4 hours

---

## Scenario

The platform is running but has multiple security gaps. Your job: audit it, fix the issues, and document the security posture.

---

## Setup

```bash
./run.sh start core apps security
./run.sh status
```

---

## Tasks

### Task 1 — Docker image scanning

Scan all platform images with Trivy:

```bash
# Scan a single image
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image \
  --severity HIGH,CRITICAL \
  --format table \
  cloud-learnings-lab-sample-api:latest

# Scan all images in the compose project
docker images --filter "reference=cloud-learnings*" --format "{{.Repository}}:{{.Tag}}" | \
  while read img; do
    echo "=== Scanning $img ==="
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
      aquasec/trivy image --severity HIGH,CRITICAL "$img"
  done
```

Document findings: How many HIGH/CRITICAL CVEs per image?

### Task 2 — IaC scanning with Checkov

Scan the Terraform configs:

```bash
docker run --rm \
  -v "$(pwd)/infrastructure/terraform:/tf" \
  bridgecrew/checkov \
  -d /tf \
  --framework terraform \
  --compact
```

Scan the Kubernetes manifests:

```bash
docker run --rm \
  -v "$(pwd)/infrastructure/kubernetes:/k8s" \
  bridgecrew/checkov \
  -d /k8s \
  --framework kubernetes \
  --compact
```

Fix at least 3 findings in each.

### Task 3 — Dockerfile linting

```bash
# Lint a Dockerfile
docker run --rm -i hadolint/hadolint < apps/sample-api/Dockerfile

# Lint all Dockerfiles
find . -name "Dockerfile" -exec \
  docker run --rm -i hadolint/hadolint hadolint {} \;
```

Fix all CRITICAL and HIGH findings.

### Task 4 — Vault secret management

Replace hardcoded credentials in the platform with Vault:

```bash
# Open Vault at http://localhost:8200 (token: root)

# 1. Create a secret for database credentials
vault kv put secret/appdb \
  username=appuser \
  password=apppassword \
  host=postgres \
  port=5432 \
  database=appdb

# 2. Create an AppRole for sample-api to use
vault auth enable approle
vault write auth/approle/role/sample-api \
  token_policies=sample-api-policy \
  token_ttl=1h

# 3. Write the policy
vault policy write sample-api-policy - <<EOF
path "secret/data/appdb" {
  capabilities = ["read"]
}
EOF

# 4. Get role_id and secret_id
vault read auth/approle/role/sample-api/role-id
vault write -f auth/approle/role/sample-api/secret-id
```

Verify a Python script can read the secret via AppRole auth.

### Task 5 — Network security audit

Review the docker-compose.yml networks. Answer:
- Which services are on the `public_net`? Should they be?
- Which services expose ports to the host? Are all necessary?
- Which services run as root? (check `docker inspect`)

For each service running as root, check if a non-root user could be used.

### Task 6 — Keycloak OIDC integration

Configure Keycloak to protect sample-api endpoints:

```bash
# Keycloak admin: http://localhost:8180 (admin/admin)
# Import lab-realm.json (already configured)

# Get an access token
TOKEN=$(curl -s -X POST \
  http://localhost:8180/realms/lab-realm/protocol/openid-connect/token \
  -d "client_id=sample-app" \
  -d "username=labuser" \
  -d "password=labpassword" \
  -d "grant_type=password" | jq -r '.access_token')

# Use the token
curl -H "Authorization: Bearer $TOKEN" http://localhost/api/items
```

### Task 7 — Security hardening checklist

Write a `SECURITY-AUDIT.md` documenting:
- All CVEs found (by severity)
- All IaC issues found and fixed
- All Dockerfile issues found and fixed
- Network exposure assessment
- Secrets management status
- Recommendations for production

---

## Success criteria

- [ ] Trivy scans completed for all images, findings documented
- [ ] 3+ Checkov findings fixed in Terraform and Kubernetes
- [ ] All Dockerfile CRITICAL/HIGH Hadolint findings fixed
- [ ] Vault AppRole working and Python reads secret
- [ ] Network audit completed with recommendations
- [ ] Keycloak token obtained and used
- [ ] SECURITY-AUDIT.md written
