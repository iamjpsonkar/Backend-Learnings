#!/usr/bin/env bash
# Validate lab: vault-basics
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-root-token}"

check_vault() {
    local desc="$1"
    local url="$2"
    local grep_pattern="${3:-}"
    local result
    result=$(curl -sf -H "X-Vault-Token: $VAULT_TOKEN" "$url" 2>/dev/null || echo "")
    if [ -z "$grep_pattern" ] || echo "$result" | grep -q "$grep_pattern"; then
        echo "PASS: $desc"
    else
        echo "FAIL: $desc (pattern '$grep_pattern' not found)"
    fi
}

# Check Vault is running and unsealed
HEALTH=$(curl -sf "$VAULT_ADDR/v1/sys/health" 2>/dev/null || echo "")
if echo "$HEALTH" | grep -q '"sealed":false'; then
    echo "PASS: Vault is running and unsealed"
else
    echo "FAIL: Vault not running or sealed — run: make start-security"
fi

# Check secret was written
check_vault "Secret lab/myapp is readable" "$VAULT_ADDR/v1/secret/data/lab/myapp" "username"

# Check api_key was added (update task)
SECRET_DATA=$(curl -sf -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/lab/myapp" 2>/dev/null || echo "{}")
if echo "$SECRET_DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'api_key' in d.get('data',{}).get('data',{}) else 1)" 2>/dev/null; then
    echo "PASS: api_key field found in secret"
else
    echo "FAIL: api_key not found in secret/lab/myapp — complete the update task"
fi

# Check policy was created
check_vault "Policy myapp-readonly exists" "$VAULT_ADDR/v1/sys/policies/acl/myapp-readonly" "myapp-readonly"

# Check Vault UI is accessible
if curl -sf "$VAULT_ADDR/ui/" | grep -qi vault; then
    echo "PASS: Vault UI accessible at $VAULT_ADDR/ui/"
else
    echo "FAIL: Vault UI not accessible"
fi
