#!/usr/bin/env bash
# Validate lab: vault-secrets-injection
set -euo pipefail

VAULT_ADDR="http://localhost:8200"
VAULT_TOKEN="dev-root-token"

echo "=== Vault Dynamic Secrets Lab Validation ==="

# Check vault CLI
if command -v vault &>/dev/null; then
    VAULT_VER=$(vault version 2>/dev/null | head -1)
    echo "PASS: Vault CLI installed — $VAULT_VER"
else
    echo "WARN: vault CLI not installed — install with: brew install vault"
fi

# Check Vault server is running
if curl -sf "$VAULT_ADDR/v1/sys/health" 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
init = d.get('initialized', False)
sealed = d.get('sealed', True)
print(f'initialized={init} sealed={sealed}')
exit(0 if init and not sealed else 1)
" 2>/dev/null; then
    echo "PASS: Vault is initialized and unsealed"
else
    echo "FAIL: Vault not reachable or sealed at $VAULT_ADDR"
    echo "      Run: make start-security"
    exit 1
fi

export VAULT_ADDR VAULT_TOKEN

# Check if database secrets engine is enabled
if command -v vault &>/dev/null; then
    if vault secrets list 2>/dev/null | grep -q "^database/"; then
        echo "PASS: Database secrets engine is enabled"
    else
        echo "WARN: Database secrets engine not enabled"
        echo "      Enable: vault secrets enable database"
    fi

    # Check if lab-postgres connection is configured
    if vault read database/config/lab-postgres 2>/dev/null | grep -q "lab-postgres"; then
        echo "PASS: lab-postgres database connection configured"
    else
        echo "WARN: lab-postgres database connection not found in Vault"
    fi

    # Check if lab-role exists
    if vault read database/roles/lab-role 2>/dev/null | grep -q "lab-role\|creation_statements"; then
        echo "PASS: lab-role database role exists"

        # Try generating credentials
        CREDS=$(vault read -format=json database/creds/lab-role 2>/dev/null || true)
        if [ -n "$CREDS" ] && echo "$CREDS" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('data',{}).get('username') else 1)" 2>/dev/null; then
            DYNA_USER=$(echo "$CREDS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['username'])")
            echo "PASS: Dynamic credential generated — username: $DYNA_USER"
        else
            echo "WARN: Could not generate dynamic credentials (PostgreSQL may not be running)"
        fi
    else
        echo "WARN: lab-role not found"
        echo "      Configure the database role first"
    fi

    # Check AppRole auth
    if vault auth list 2>/dev/null | grep -q "^approle/"; then
        echo "PASS: AppRole authentication is enabled"
    else
        echo "INFO: AppRole auth not enabled (optional for this validation)"
    fi
fi

echo ""
echo "=== Validation complete ==="
