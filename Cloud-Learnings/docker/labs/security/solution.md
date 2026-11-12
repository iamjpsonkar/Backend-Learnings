# Solution — Security

## Task 1 — Vault KV Full Workflow

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-root-token

# Enable engine
vault secrets enable -path=secret kv-v2

# Write
vault kv put secret/myapp/config \
  db_password="mysecretpassword" \
  api_key="abc123" \
  db_host="postgres" \
  db_port="5432"

# Read
vault kv get secret/myapp/config

# Get single field (for scripting)
DB_PASS=$(vault kv get -field=db_password secret/myapp/config)
echo "DB password: $DB_PASS"

# Update (creates version 2)
vault kv patch secret/myapp/config db_password="newpassword"

# View history
vault kv metadata get secret/myapp/config

# Rollback to version 1
vault kv get -version=1 secret/myapp/config
```

## Task 2 — AppRole Full Workflow

```bash
# Enable
vault auth enable approle

# Policy
vault policy write myapp-policy - << 'EOF'
path "secret/data/myapp/*" {
  capabilities = ["read", "list"]
}
EOF

# Role
vault write auth/approle/role/myapp \
  policies="myapp-policy" \
  token_ttl=1h \
  token_max_ttl=4h

# Get credentials
ROLE_ID=$(vault read -field=role_id auth/approle/role/myapp/role-id)
SECRET_ID=$(vault write -force -field=secret_id auth/approle/role/myapp/secret-id)

echo "Role ID: $ROLE_ID"
echo "Secret ID: $SECRET_ID"

# Login (as application would)
TOKEN=$(vault write -field=token auth/approle/login \
  role_id="$ROLE_ID" \
  secret_id="$SECRET_ID")

# Use app token
VAULT_TOKEN="$TOKEN" vault kv get secret/myapp/config
```

## Task 7 — Replace Hardcoded Secret

**Before (insecure):**
```python
DATABASE_URL = "postgresql://labuser:hardcoded-password@localhost:5432/labdb"
```

**After (using environment variable):**
```python
import os
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required")
```

**After (using Vault):**
```python
import hvac
import os

vault_client = hvac.Client(
    url=os.getenv("VAULT_ADDR", "http://localhost:8200"),
    token=os.getenv("VAULT_TOKEN")
)
secret = vault_client.secrets.kv.v2.read_secret_version(
    path="myapp/config",
    mount_point="secret"
)
db_password = secret["data"]["data"]["db_password"]
```
