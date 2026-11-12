#!/usr/bin/env bash
# scripts/vault-init.sh — Initialize Vault with lab secrets and policies
# Run: make vault-init   (after make start-security)

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/common.sh"
load_env

VAULT_ADDR="${VAULT_ADDR:-http://localhost:${VAULT_PORT:-8200}}"
VAULT_TOKEN="${VAULT_DEV_ROOT_TOKEN_ID:-dev-root-token}"

export VAULT_ADDR VAULT_TOKEN

log_step "Vault Initialization for Lab Platform"
log_info "Vault address: $VAULT_ADDR"

# Check Vault is running
wait_for_service "Vault" "$VAULT_ADDR/v1/sys/health?standbyok=true" 15

require_command vault "brew install vault  OR  https://developer.hashicorp.com/vault/downloads"

log_info "Vault status:"
vault status || true

# ─────────────────────────────────────────────
# Enable secret engines used in labs
# ─────────────────────────────────────────────
log_step "Enabling secret engines"

# KV v2 for general secrets
vault secrets enable -path=secret kv-v2 2>/dev/null || log_info "  kv-v2 at secret/ already enabled"

# KV v1 for simple labs
vault secrets enable -path=kv kv 2>/dev/null || log_info "  kv at kv/ already enabled"

# PKI for TLS certificate labs
vault secrets enable pki 2>/dev/null || log_info "  pki already enabled"
vault secrets tune -max-lease-ttl=87600h pki 2>/dev/null || true

# Database secrets engine
vault secrets enable database 2>/dev/null || log_info "  database already enabled"

log_ok "Secret engines enabled"

# ─────────────────────────────────────────────
# Seed demo secrets
# ─────────────────────────────────────────────
log_step "Seeding lab secrets"

vault kv put secret/lab/database \
    host="postgres" \
    port="5432" \
    name="labdb" \
    username="labuser" \
    password="labpassword123" \
    2>/dev/null

vault kv put secret/lab/redis \
    host="redis" \
    port="6379" \
    password="labpassword123" \
    2>/dev/null

vault kv put secret/lab/api-keys \
    internal_api_key="dev-api-key-do-not-use-in-prod" \
    webhook_secret="dev-webhook-secret-12345" \
    2>/dev/null

log_ok "Lab secrets seeded"

# ─────────────────────────────────────────────
# Create lab policies
# ─────────────────────────────────────────────
log_step "Creating policies"

vault policy write lab-readonly - << 'POLICY'
# Read-only access to lab secrets
path "secret/data/lab/*" {
  capabilities = ["read", "list"]
}
path "kv/lab/*" {
  capabilities = ["read", "list"]
}
POLICY

vault policy write lab-readwrite - << 'POLICY'
# Read-write access to lab secrets
path "secret/data/lab/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/metadata/lab/*" {
  capabilities = ["list", "read", "delete"]
}
path "kv/lab/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
POLICY

log_ok "Policies created: lab-readonly, lab-readwrite"

# ─────────────────────────────────────────────
# Create lab tokens
# ─────────────────────────────────────────────
log_step "Creating lab tokens"

READONLY_TOKEN=$(vault token create \
    -policy=lab-readonly \
    -ttl=24h \
    -display-name=lab-readonly \
    -format=json | python3 -c "import sys,json; print(json.load(sys.stdin)['auth']['client_token'])")

log_ok "Read-only token (valid 24h): $READONLY_TOKEN"

echo ""
echo "Vault is ready for labs."
echo "  VAULT_ADDR=$VAULT_ADDR"
echo "  VAULT_TOKEN=$VAULT_TOKEN (root, dev mode only)"
echo ""
echo "Test with:"
echo "  export VAULT_ADDR=$VAULT_ADDR"
echo "  export VAULT_TOKEN=$VAULT_TOKEN"
echo "  vault kv get secret/lab/database"
