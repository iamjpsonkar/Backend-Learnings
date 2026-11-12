← [Previous: APIM](../08-serverless/apim.md) | [Home](../../README.md) | [Next: Key Vault →](./key-vault.md)

---

# Azure Security

---

## Service Overview

| Service | AWS Equivalent | Purpose |
|---------|----------------|---------|
| **Azure Key Vault** | KMS + Secrets Manager | Keys, secrets, certificates — managed HSM option |
| **Microsoft Defender for Cloud** | GuardDuty + Security Hub | Threat detection + security posture management |
| **Microsoft Sentinel** | — (no direct equivalent) | Cloud-native SIEM and SOAR |
| **Azure DDoS Protection** | Shield Advanced | DDoS mitigation |
| **Azure Firewall** | Network Firewall | Managed stateful L4/L7 firewall |
| **Microsoft Entra PIM** | — | Just-in-time privileged access |

---

## Azure Key Vault

Key Vault stores three types of secrets:

| Type | Examples | Use |
|------|---------|-----|
| **Secrets** | Database passwords, API keys, connection strings | Application credentials |
| **Keys** | RSA/EC cryptographic keys | Encryption, signing (wraps Azure services) |
| **Certificates** | TLS/SSL certificates | HTTPS, mTLS |

```bash
RESOURCE_GROUP="rg-my-app-production"
LOCATION="eastus"

# Create a Key Vault (RBAC authorization model — recommended)
az keyvault create \
    --resource-group $RESOURCE_GROUP \
    --name kv-my-app-prod-eastus \
    --location $LOCATION \
    --sku standard \
    --enable-rbac-authorization true \
    --enable-soft-delete true \
    --soft-delete-retention-days 90 \
    --enable-purge-protection true \
    --public-network-access Disabled \
    --tags Environment=production

# Grant yourself Key Vault Administrator role
MY_ID=$(az ad signed-in-user show --query id --output tsv)
az role assignment create \
    --assignee $MY_ID \
    --role "Key Vault Administrator" \
    --scope $(az keyvault show --name kv-my-app-prod-eastus --query id --output tsv)

# Store secrets
az keyvault secret set \
    --vault-name kv-my-app-prod-eastus \
    --name database-password \
    --value "Str0ngP@ssw0rd!" \
    --content-type "text/plain" \
    --tags Service=my-app Environment=production

az keyvault secret set \
    --vault-name kv-my-app-prod-eastus \
    --name api-key \
    --value "sk-live-abc123def456"

# Retrieve secrets
az keyvault secret show \
    --vault-name kv-my-app-prod-eastus \
    --name database-password \
    --query value --output tsv

# List secrets
az keyvault secret list \
    --vault-name kv-my-app-prod-eastus \
    --query '[*].{Name:name,Created:attributes.created,Enabled:attributes.enabled}' \
    --output table

# Create a managed encryption key
az keyvault key create \
    --vault-name kv-my-app-prod-eastus \
    --name my-app-encryption-key \
    --kty RSA \
    --size 2048 \
    --ops encrypt decrypt wrapKey unwrapKey \
    --tags Service=my-app

# Import a TLS certificate
az keyvault certificate import \
    --vault-name kv-my-app-prod-eastus \
    --name my-app-tls \
    --file /path/to/cert.pfx \
    --password "certpassword"

# Generate a Key Vault-managed certificate (auto-renewal)
az keyvault certificate create \
    --vault-name kv-my-app-prod-eastus \
    --name my-app-tls-managed \
    --policy '{
        "x509CertificateProperties": {
            "subject": "CN=my-app.example.com",
            "subjectAlternativeNames": {"dnsNames": ["my-app.example.com", "www.example.com"]},
            "validityInMonths": 12
        },
        "issuerParameters": {
            "name": "DigiCert",
            "certificateType": "OV-SSL"
        },
        "keyProperties": {
            "keyType": "RSA",
            "keySize": 2048,
            "exportable": true
        },
        "lifetimeActions": [{
            "trigger": {"daysBeforeExpiry": 30},
            "action": {"actionType": "AutoRenew"}
        }]
    }'
```

### Python SDK — Accessing Key Vault Secrets

```python
import os
import logging
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from functools import lru_cache

logger = logging.getLogger(__name__)

_credential = DefaultAzureCredential()
_vault_url = f"https://{os.environ['KEY_VAULT_NAME']}.vault.azure.net"
_secret_client = SecretClient(vault_url=_vault_url, credential=_credential)


@lru_cache(maxsize=None)
def get_secret(secret_name: str) -> str:
    """Retrieve a secret from Key Vault with process-lifetime caching."""
    logger.info("Fetching secret from Key Vault: name=%s", secret_name)
    try:
        secret = _secret_client.get_secret(secret_name)
        logger.debug("Secret retrieved: name=%s version=%s", secret_name, secret.properties.version)
        return secret.value
    except Exception as e:
        logger.error("Failed to retrieve secret: name=%s error=%s", secret_name, str(e))
        raise
```

---

## Microsoft Defender for Cloud

Defender for Cloud provides continuous security assessment (secure score) and threat detection.

```bash
# Enable Defender plans (charged per resource)
az security pricing create --name VirtualMachines     --tier Standard  # $0.02/VM/hr
az security pricing create --name StorageAccounts     --tier Standard
az security pricing create --name SqlServers          --tier Standard
az security pricing create --name AppServices         --tier Standard
az security pricing create --name ContainerRegistry   --tier Standard
az security pricing create --name KeyVaults           --tier Standard
az security pricing create --name KubernetesService   --tier Standard

# View security recommendations
az security assessment list \
    --query '[?status.code==`Unhealthy`].{Name:displayName,Severity:metadata.severity,Resource:resourceDetails.id}' \
    --output table

# View security alerts (threat detections)
az security alert list \
    --query '[*].{Name:alertDisplayName,Severity:severity,State:state,Time:timeGeneratedUtc}' \
    --output table

# Get overall secure score
az security secure-score list \
    --query '[*].{Name:displayName,Score:score.current,Max:score.max,Percentage:score.percentage}' \
    --output table

# Enable just-in-time VM access (blocks management ports until explicitly allowed)
az security jit-policy create \
    --resource-group $RESOURCE_GROUP \
    --name default \
    --virtual-machines '[{
        "id": "/subscriptions/'"$SUBSCRIPTION_ID"'/resourceGroups/'"$RESOURCE_GROUP"'/providers/Microsoft.Compute/virtualMachines/vm-my-app-prod-eastus-001",
        "ports": [
            {"number": 22, "protocol": "TCP", "maxRequestAccessDuration": "PT3H"},
            {"number": 3389, "protocol": "TCP", "maxRequestAccessDuration": "PT1H"}
        ]
    }]'

# Request JIT access to SSH into a VM
az security jit-policy initiate \
    --resource-group $RESOURCE_GROUP \
    --name default \
    --vm-id /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Compute/virtualMachines/vm-my-app-prod-eastus-001 \
    --ports '[{"number": 22, "duration": "PT2H", "allowedSourceAddressPrefix": "MY_IP"}]'
```

---

## Microsoft Sentinel (SIEM)

Sentinel collects security data from Azure and non-Azure sources, detects threats with analytics rules, and enables automated response with playbooks.

```bash
# Create a Log Analytics workspace (Sentinel runs on top of it)
WORKSPACE_ID=$(az monitor log-analytics workspace create \
    --resource-group $RESOURCE_GROUP \
    --workspace-name law-sentinel-prod-eastus \
    --location $LOCATION \
    --sku PerGB2018 \
    --retention-time 90 \
    --query id --output tsv)

# Enable Sentinel on the workspace
az sentinel workspace create \
    --resource-group $RESOURCE_GROUP \
    --workspace-name law-sentinel-prod-eastus

# Connect Azure Active Directory data connector
az sentinel data-connector create \
    --resource-group $RESOURCE_GROUP \
    --workspace-name law-sentinel-prod-eastus \
    --data-connector-id AzureActiveDirectory \
    --kind AzureActiveDirectory \
    --properties tenantId=$TENANT_ID

# List active analytics rules (threat detection rules)
az sentinel alert-rule list \
    --resource-group $RESOURCE_GROUP \
    --workspace-name law-sentinel-prod-eastus \
    --query '[*].{Name:displayName,Severity:properties.severity,Status:properties.enabled}' \
    --output table

# List incidents
az sentinel incident list \
    --resource-group $RESOURCE_GROUP \
    --workspace-name law-sentinel-prod-eastus \
    --query '[?properties.severity==`High`].{Title:properties.title,Severity:properties.severity,Status:properties.status}' \
    --output table
```

---

## Azure DDoS Protection

```bash
# Create a DDoS Protection Plan (~$2,944/month, covers unlimited VNets in the plan)
az network ddos-protection create \
    --resource-group $RESOURCE_GROUP \
    --name ddos-prod-eastus \
    --location $LOCATION

# Associate with VNet (enables Standard protection)
az network vnet update \
    --resource-group $RESOURCE_GROUP \
    --name vnet-my-app-prod-eastus-001 \
    --ddos-protection true \
    --ddos-protection-plan ddos-prod-eastus
```

---

## Security Best Practices Checklist

- [ ] Enable Defender for Cloud for all subscription services
- [ ] Require MFA via Conditional Access for all users
- [ ] Use Managed Identities instead of service principal credentials wherever possible
- [ ] Enable Key Vault soft-delete and purge protection
- [ ] Use Private Endpoints for Key Vault — disable public access
- [ ] Apply JIT VM access to block SSH/RDP by default
- [ ] Enable Microsoft Sentinel and connect at minimum the Azure Activity Log and Entra ID data connectors
- [ ] Scope RBAC assignments to the minimum necessary scope (resource > resource group > subscription)
- [ ] Use PIM for privileged roles — no always-on Owner assignments

---

## References

- [Azure Key Vault documentation](https://docs.microsoft.com/azure/key-vault/)
- [Microsoft Defender for Cloud](https://docs.microsoft.com/azure/defender-for-cloud/)
- [Microsoft Sentinel](https://docs.microsoft.com/azure/sentinel/)
- [Azure security baseline](https://docs.microsoft.com/security/benchmark/azure/)
---

← [Previous: APIM](../08-serverless/apim.md) | [Home](../../README.md) | [Next: Key Vault →](./key-vault.md)
