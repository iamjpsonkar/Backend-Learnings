← [Previous: Azure Security](./README.md) | [Home](../../README.md) | [Next: Defender for Cloud →](./defender.md)

---

# Azure Key Vault

Key Vault stores and manages secrets, encryption keys, and certificates. It enforces access control via Azure RBAC and integrates with managed identities for zero-credential access from Azure services.

---

## What Key Vault Stores

| Type | Examples | API |
|------|---------|-----|
| **Secrets** | Passwords, connection strings, API keys | `SecretClient` |
| **Keys** | RSA/EC keys for encryption, signing | `KeyClient` |
| **Certificates** | TLS/SSL certs (auto-renew from DigiCert, Let's Encrypt) | `CertificateClient` |

---

## Access Models

| Model | How it works | Recommendation |
|-------|-------------|----------------|
| **RBAC** (recommended) | Standard Azure roles at vault or secret scope | Use for new vaults |
| **Access Policies** (legacy) | Vault-level allow list per principal | Migrate to RBAC |

Key Vault RBAC roles:

| Role | Permissions |
|------|------------|
| Key Vault Secrets User | Read secret values |
| Key Vault Secrets Officer | CRUD on secrets |
| Key Vault Reader | Read metadata, no values |
| Key Vault Administrator | Full control |

---

## Creating a Key Vault

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
LOCATION="eastus"
KV_NAME="kv-my-app-prod-eastus"

# Create vault with RBAC authorization (not access policies)
az keyvault create \
    --resource-group $RESOURCE_GROUP \
    --name $KV_NAME \
    --location $LOCATION \
    --sku premium \
    --enable-rbac-authorization true \
    --enable-soft-delete true \
    --soft-delete-retention-days 90 \
    --enable-purge-protection true \
    --public-network-access Disabled \
    --tags Environment=production Service=my-app

# Grant yourself admin access
MY_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
KV_ID=$(az keyvault show --resource-group $RESOURCE_GROUP --name $KV_NAME --query id -o tsv)

az role assignment create \
    --assignee $MY_OBJECT_ID \
    --role "Key Vault Administrator" \
    --scope $KV_ID
```

---

## Managing Secrets

```bash
# Set a secret
az keyvault secret set \
    --vault-name $KV_NAME \
    --name db-password \
    --value "SuperSecretPassword123!" \
    --expires "2025-12-31T00:00:00Z" \
    --tags ManagedBy=Terraform Rotation=quarterly

# Get a secret value
az keyvault secret show \
    --vault-name $KV_NAME \
    --name db-password \
    --query value -o tsv

# List secrets (names only, not values)
az keyvault secret list \
    --vault-name $KV_NAME \
    --query '[*].{Name:name,Enabled:attributes.enabled,Expires:attributes.expires}' \
    --output table

# Create a new version (old versions remain accessible by version ID)
az keyvault secret set \
    --vault-name $KV_NAME \
    --name db-password \
    --value "NewSecretPassword456!"

# List versions
az keyvault secret list-versions \
    --vault-name $KV_NAME \
    --name db-password \
    --output table

# Disable a secret version
az keyvault secret set-attributes \
    --vault-name $KV_NAME \
    --name db-password \
    --version "abc123..." \
    --enabled false

# Delete and purge (irreversible — only after soft-delete retention)
az keyvault secret delete --vault-name $KV_NAME --name db-password
az keyvault secret purge --vault-name $KV_NAME --name db-password  # Permanent
```

---

## Managing Keys

```bash
# Create an RSA key (for encryption)
az keyvault key create \
    --vault-name $KV_NAME \
    --name data-encryption-key \
    --kty RSA \
    --size 4096 \
    --ops encrypt decrypt wrapKey unwrapKey \
    --protection hsm  # Hardware-backed (Premium SKU)

# Create an EC key (for signing)
az keyvault key create \
    --vault-name $KV_NAME \
    --name signing-key \
    --kty EC \
    --curve P-384 \
    --ops sign verify

# Enable auto-rotation
az keyvault key rotation-policy update \
    --vault-name $KV_NAME \
    --name data-encryption-key \
    --value @rotation-policy.json
# rotation-policy.json: { "lifetimeActions": [{"trigger": {"timeBeforeExpiry": "P30D"}, "action": {"type": "Rotate"}}], "attributes": {"expiryTime": "P1Y"} }
```

---

## TLS Certificates

```bash
# Create a self-signed certificate
az keyvault certificate create \
    --vault-name $KV_NAME \
    --name my-app-tls \
    --policy "$(az keyvault certificate get-default-policy)"

# Import an existing PFX certificate
az keyvault certificate import \
    --vault-name $KV_NAME \
    --name my-app-tls \
    --file cert.pfx \
    --password "$CERT_PASSWORD"

# Auto-renew certificate from DigiCert
ISSUER_POLICY='{
  "issuerParameters": {"name": "DigiCert"},
  "keyProperties": {"keyType": "RSA", "keySize": 4096, "reuseKey": false},
  "x509CertificateProperties": {
    "subject": "CN=my-app.example.com",
    "subjectAlternativeNames": {"dnsNames": ["my-app.example.com", "www.my-app.example.com"]},
    "validityInMonths": 12
  },
  "lifetimeActions": [{"trigger": {"daysBeforeExpiry": 30}, "action": {"actionType": "AutoRenew"}}]
}'
az keyvault certificate create \
    --vault-name $KV_NAME \
    --name my-app-tls-auto \
    --policy "$ISSUER_POLICY"
```

---

## Python SDK — Zero-Credential Pattern

```python
import os
import logging
import functools
from azure.keyvault.secrets import SecretClient
from azure.keyvault.keys import KeyClient
from azure.keyvault.keys.crypto import CryptographyClient, EncryptionAlgorithm
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

KV_URL = os.environ["KEY_VAULT_URL"]  # https://kv-my-app-prod-eastus.vault.azure.net
_credential = None


def _get_credential() -> DefaultAzureCredential:
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


@functools.lru_cache(maxsize=None)
def get_secret(secret_name: str) -> str:
    """Retrieve a secret value from Key Vault. Cached after first call."""
    client = SecretClient(vault_url=KV_URL, credential=_get_credential())
    logger.info("Fetching secret from Key Vault", extra={"secret_name": secret_name})
    secret = client.get_secret(secret_name)
    logger.info("Secret fetched", extra={"secret_name": secret_name, "version": secret.properties.version})
    return secret.value


def rotate_secret_cache(secret_name: str) -> None:
    """Invalidate cache entry for a rotated secret."""
    get_secret.cache_clear()
    logger.info("Secret cache cleared", extra={"secret_name": secret_name})


def encrypt_data(key_name: str, plaintext: bytes) -> bytes:
    """Encrypt data using a Key Vault key."""
    key_client = KeyClient(vault_url=KV_URL, credential=_get_credential())
    key = key_client.get_key(key_name)
    crypto_client = CryptographyClient(key, credential=_get_credential())

    logger.info("Encrypting data", extra={"key_name": key_name, "bytes": len(plaintext)})
    result = crypto_client.encrypt(EncryptionAlgorithm.rsa_oaep_256, plaintext)
    logger.info("Data encrypted", extra={"key_name": key_name, "ciphertext_bytes": len(result.ciphertext)})
    return result.ciphertext


def decrypt_data(key_name: str, ciphertext: bytes) -> bytes:
    """Decrypt data using a Key Vault key."""
    key_client = KeyClient(vault_url=KV_URL, credential=_get_credential())
    key = key_client.get_key(key_name)
    crypto_client = CryptographyClient(key, credential=_get_credential())

    logger.info("Decrypting data", extra={"key_name": key_name, "ciphertext_bytes": len(ciphertext)})
    result = crypto_client.decrypt(EncryptionAlgorithm.rsa_oaep_256, ciphertext)
    logger.info("Data decrypted", extra={"key_name": key_name})
    return result.plaintext
```

---

## Private Endpoint

```bash
# Create private endpoint for Key Vault
az network private-endpoint create \
    --resource-group $RESOURCE_GROUP \
    --name pe-keyvault \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-private-endpoints \
    --private-connection-resource-id $KV_ID \
    --group-id vault \
    --connection-name pe-conn-keyvault

# Private DNS zone
az network private-dns zone create \
    --resource-group $RESOURCE_GROUP \
    --name "privatelink.vaultcore.azure.net"

az network private-dns link vnet create \
    --resource-group $RESOURCE_GROUP \
    --zone-name "privatelink.vaultcore.azure.net" \
    --name dns-link-kv \
    --virtual-network vnet-my-app-prod-eastus-001 \
    --registration-enabled false

az network private-endpoint dns-zone-group create \
    --resource-group $RESOURCE_GROUP \
    --endpoint-name pe-keyvault \
    --name kv-zone-group \
    --private-dns-zone "privatelink.vaultcore.azure.net" \
    --zone-name vault
```

---

## References

- [Azure Key Vault documentation](https://docs.microsoft.com/azure/key-vault/)
- [Key Vault RBAC](https://docs.microsoft.com/azure/key-vault/general/rbac-guide)
- [Python SDK](https://docs.microsoft.com/azure/key-vault/secrets/quick-create-python)
- [Certificate auto-renewal](https://docs.microsoft.com/azure/key-vault/certificates/how-to-integrate-certificate-authority)

---

← [Previous: Azure Security](./README.md) | [Home](../../README.md) | [Next: Defender for Cloud →](./defender.md)
