← [Previous: Application Gateway](./application-gateway.md) | [Home](../../README.md) | [Next: Azure Compute →](../04-compute/README.md)

---

# Azure Private Endpoints

Private Endpoints give Azure PaaS services (Storage, SQL, Key Vault, Cosmos DB, AKS API server, etc.) a private IP address within your VNet. Traffic stays on the Microsoft backbone — it never traverses the public internet.

---

## How Private Link Works

```
Your VNet (10.0.0.0/16)
  └── snet-private-endpoints (10.0.30.0/24)
        └── NIC: pe-storage-blob  ─── private IP 10.0.30.4
                                         │
                             Azure Private Link Service
                                         │
                             stmyappprodeastus.blob.core.windows.net
                             (resolves to 10.0.30.4 via private DNS)
```

Key points:
- The PaaS resource retains its public FQDN — private DNS overrides resolution inside the VNet
- You can (and should) disable public network access on the PaaS resource after the endpoint is created
- Requires `--disable-private-endpoint-network-policies true` on the subnet

---

## Supported Services and Group IDs

| Service | Group ID(s) |
|---------|-------------|
| Azure Blob Storage | `blob` |
| Azure File Storage | `file` |
| Azure Queue Storage | `queue` |
| Azure Table Storage | `table` |
| Azure SQL Database | `sqlServer` |
| Azure PostgreSQL Flexible Server | `postgresqlServer` |
| Azure Cosmos DB (SQL) | `Sql` |
| Azure Key Vault | `vault` |
| Azure Monitor / Log Analytics | `azuremonitor` |
| Azure Container Registry | `registry` |
| AKS API server | `management` |
| Azure Service Bus | `namespace` |
| Azure Event Hubs | `namespace` |
| Azure App Service | `sites` |

---

## Creating a Private Endpoint

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
VNET="vnet-my-app-prod-eastus-001"
PE_SUBNET="snet-private-endpoints"

# Ensure the subnet has private endpoint policies disabled
az network vnet subnet update \
    --resource-group $RESOURCE_GROUP \
    --vnet-name $VNET \
    --name $PE_SUBNET \
    --disable-private-endpoint-network-policies true

# --- Storage Account ---
STORAGE_ID=$(az storage account show \
    --resource-group $RESOURCE_GROUP \
    --name stmyappprodeastus \
    --query id --output tsv)

az network private-endpoint create \
    --resource-group $RESOURCE_GROUP \
    --name pe-storage-blob \
    --vnet-name $VNET \
    --subnet $PE_SUBNET \
    --private-connection-resource-id $STORAGE_ID \
    --group-id blob \
    --connection-name pe-conn-storage-blob

# Disable public access on the storage account
az storage account update \
    --resource-group $RESOURCE_GROUP \
    --name stmyappprodeastus \
    --public-network-access Disabled

# --- Key Vault ---
KV_ID=$(az keyvault show \
    --resource-group $RESOURCE_GROUP \
    --name kv-my-app-prod-eastus \
    --query id --output tsv)

az network private-endpoint create \
    --resource-group $RESOURCE_GROUP \
    --name pe-keyvault \
    --vnet-name $VNET \
    --subnet $PE_SUBNET \
    --private-connection-resource-id $KV_ID \
    --group-id vault \
    --connection-name pe-conn-keyvault

# Disable public access on Key Vault
az keyvault update \
    --resource-group $RESOURCE_GROUP \
    --name kv-my-app-prod-eastus \
    --public-network-access Disabled

# --- Azure SQL ---
SQL_ID=$(az sql server show \
    --resource-group $RESOURCE_GROUP \
    --name sql-my-app-prod-eastus \
    --query id --output tsv)

az network private-endpoint create \
    --resource-group $RESOURCE_GROUP \
    --name pe-sql \
    --vnet-name $VNET \
    --subnet $PE_SUBNET \
    --private-connection-resource-id $SQL_ID \
    --group-id sqlServer \
    --connection-name pe-conn-sql
```

---

## Private DNS Zones

Without private DNS, the storage FQDN resolves to its public IP even inside the VNet. You must create a private DNS zone and link it to the VNet.

```bash
# DNS zone names per service
# Blob:     privatelink.blob.core.windows.net
# File:     privatelink.file.core.windows.net
# SQL:      privatelink.database.windows.net
# Key Vault: privatelink.vaultcore.azure.net
# ACR:      privatelink.azurecr.io
# Service Bus: privatelink.servicebus.windows.net

ZONE="privatelink.blob.core.windows.net"

# Create private DNS zone
az network private-dns zone create \
    --resource-group $RESOURCE_GROUP \
    --name "$ZONE"

# Link DNS zone to the VNet (auto-registration off — PE manages DNS records)
az network private-dns link vnet create \
    --resource-group $RESOURCE_GROUP \
    --zone-name "$ZONE" \
    --name dns-link-prod-vnet \
    --virtual-network $VNET \
    --registration-enabled false

# Auto-register DNS A record from the private endpoint
az network private-endpoint dns-zone-group create \
    --resource-group $RESOURCE_GROUP \
    --endpoint-name pe-storage-blob \
    --name blob-zone-group \
    --private-dns-zone "$ZONE" \
    --zone-name blob

# Verify DNS record was created
az network private-dns record-set a list \
    --resource-group $RESOURCE_GROUP \
    --zone-name "$ZONE" \
    --output table
```

### Bulk DNS Setup Script

```bash
#!/bin/bash
# Setup private DNS zones for common services
RESOURCE_GROUP="rg-my-app-prod-eastus"
VNET="vnet-my-app-prod-eastus-001"

declare -A ZONES=(
    [blob]="privatelink.blob.core.windows.net"
    [file]="privatelink.file.core.windows.net"
    [sql]="privatelink.database.windows.net"
    [vault]="privatelink.vaultcore.azure.net"
    [acr]="privatelink.azurecr.io"
    [servicebus]="privatelink.servicebus.windows.net"
    [postgres]="privatelink.postgres.database.azure.com"
)

for svc in "${!ZONES[@]}"; do
    ZONE="${ZONES[$svc]}"
    echo "Creating DNS zone: $ZONE"
    az network private-dns zone create \
        --resource-group $RESOURCE_GROUP \
        --name "$ZONE" --output none

    az network private-dns link vnet create \
        --resource-group $RESOURCE_GROUP \
        --zone-name "$ZONE" \
        --name "dns-link-$svc" \
        --virtual-network $VNET \
        --registration-enabled false \
        --output none
    echo "  Linked to VNet: $VNET"
done
```

---

## Verifying Connectivity

```bash
# Check private endpoint provisioning state
az network private-endpoint show \
    --resource-group $RESOURCE_GROUP \
    --name pe-storage-blob \
    --query '{State:provisioningState,IP:customDnsConfigs[0].ipAddresses[0]}' \
    --output json

# From inside a VM in the VNet — verify DNS resolves to private IP
# nslookup stmyappprodeastus.blob.core.windows.net
# Expected: 10.0.30.4 (private IP, not a public IP)

# List all private endpoints in a resource group
az network private-endpoint list \
    --resource-group $RESOURCE_GROUP \
    --query '[*].{Name:name,State:provisioningState,Resource:privateLinkServiceConnections[0].privateLinkServiceId}' \
    --output table
```

---

## Private Link Service (Expose Your Own Service)

Private Link Service lets you expose your own internal load-balanced service to other VNets or tenants — without VNet peering.

```bash
# Create a standard internal load balancer (required by Private Link Service)
az network lb create \
    --resource-group $RESOURCE_GROUP \
    --name lb-internal-prod \
    --sku Standard \
    --vnet-name $VNET \
    --subnet snet-app \
    --frontend-ip-name fe-internal \
    --backend-pool-name be-pool

# Create a Private Link Service on the LB frontend
az network private-link-service create \
    --resource-group $RESOURCE_GROUP \
    --name pls-my-service \
    --vnet-name $VNET \
    --subnet snet-app \
    --lb-name lb-internal-prod \
    --lb-frontend-ip-configs fe-internal \
    --location eastus

# Get the alias — share with consumers to create their private endpoints
az network private-link-service show \
    --resource-group $RESOURCE_GROUP \
    --name pls-my-service \
    --query 'alias' --output tsv
```

---

## References

- [Azure Private Link documentation](https://docs.microsoft.com/azure/private-link/)
- [Private endpoint DNS configuration](https://docs.microsoft.com/azure/private-link/private-endpoint-dns)
- [Private Link service](https://docs.microsoft.com/azure/private-link/private-link-service-overview)

---

← [Previous: Application Gateway](./application-gateway.md) | [Home](../../README.md) | [Next: Azure Compute →](../04-compute/README.md)
