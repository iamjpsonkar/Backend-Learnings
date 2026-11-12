# Troubleshooting — Security

## Vault: Error authenticating: error parsing token

Make sure VAULT_TOKEN is set:
```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-root-token
```

## Vault: sealed

Dev mode Vault restarts unsealed. If it's sealed after a restart:
```bash
vault operator unseal
# Enter any unseal key (dev mode accepts any key)
```

## Vault: path "secret/..." does not exist

Enable the KV engine first:
```bash
vault secrets enable -path=secret kv-v2
```

## Keycloak: 404 on /admin

Wait for Keycloak to fully start (can take 90-120 seconds):
```bash
docker logs cloud-learnings-keycloak --tail=20
# Wait for: "Keycloak X.X.X ... started"
```

## Trivy: Cannot access Docker socket

Trivy needs Docker socket for image scanning. It's mounted as read-only.
If you see permission errors, check the Docker socket is mounted:
```bash
docker exec cloud-learnings-trivy ls -la /var/run/docker.sock
```

## Checkov: No checks found

Make sure you're pointing to a directory with Terraform files:
```bash
docker exec cloud-learnings-checkov ls /workspace/terraform/
```
