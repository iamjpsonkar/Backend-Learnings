# Validation — Security

## Check Vault is running

```bash
curl -s http://localhost:8200/v1/sys/health | jq '{initialized, sealed}'
# Expected: {"initialized": true, "sealed": false}
```

## Check a secret exists

```bash
VAULT_TOKEN=dev-root-token \
  curl -s -H "X-Vault-Token: dev-root-token" \
  http://localhost:8200/v1/secret/data/myapp/config | jq '.data.data'
# Expected: your key-value pairs
```

## Check Keycloak realm

```bash
curl -s http://localhost:8180/realms/my-realm/.well-known/openid-configuration | jq '.issuer'
# Expected: "http://localhost:8180/realms/my-realm"
```

## Verify Trivy scan output

```bash
ls -la reports/security-scans/
# Expected: scan file(s) if you used --output flag
```
