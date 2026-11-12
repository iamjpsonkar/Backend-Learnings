← [Previous: Azure Storage](./README.md) | [Home](../../README.md) | [Next: Azure Databases →](../06-databases/README.md)

---

# Azure Storage Accounts

An Azure Storage Account is the top-level container for all Azure Storage services: Blob, Files, Queues, and Tables.

---

## Storage Services Summary

| Service | Use case | AWS equivalent |
|---------|---------|----------------|
| **Blob Storage** | Unstructured objects — images, backups, logs, large files | S3 |
| **Azure Files** | Managed SMB/NFS file shares | EFS |
| **Queue Storage** | Simple message queuing | SQS (basic) |
| **Table Storage** | NoSQL key-value store | DynamoDB (basic) |
| **Data Lake Storage Gen2** | Analytics workloads — hierarchical namespace | S3 + Lake Formation |

---

## Creating a Storage Account

```bash
# Create a general-purpose v2 storage account
az storage account create \
    --resource-group rg-my-app-prod-eastus \
    --name stmyappprodeastus \
    --location eastus \
    --sku Standard_ZRS \
    --kind StorageV2 \
    --access-tier Hot \
    --https-only true \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --tags Environment=production Team=platform

# List storage accounts
az storage account list \
    --resource-group rg-my-app-prod-eastus \
    --query '[*].{Name:name,SKU:sku.name,Kind:kind,Location:location}' \
    --output table

# Show details
az storage account show \
    --resource-group rg-my-app-prod-eastus \
    --name stmyappprodeastus
```

### Redundancy Options (SKU)

| SKU | Replication | SLA |
|-----|------------|-----|
| `Standard_LRS` | 3 copies in one datacenter | 99.9% |
| `Standard_ZRS` | 3 copies across 3 AZs in one region | 99.9999999% (zone) |
| `Standard_GRS` | LRS + async copy to secondary region | 99.99999999999999% |
| `Standard_RAGRS` | GRS + read access to secondary | Same as GRS + readable failover |
| `Standard_GZRS` | ZRS + async copy to secondary region | Highest durability |
| `Premium_LRS` | SSD, single datacenter | For performance (blobs, files) |
| `Premium_ZRS` | SSD, zone-redundant | High-perf + zone resilient |

---

## Blob Storage

### Blob Access Tiers

| Tier | Use case | Storage cost | Access cost |
|------|---------|-------------|-------------|
| Hot | Frequently accessed data | Highest | Lowest |
| Cool | Infrequently accessed (≥30 days) | Lower | Higher |
| Cold | Rarely accessed (≥90 days) | Even lower | Even higher |
| Archive | Long-term backup, compliance (≥180 days) | Lowest | Highest + rehydration latency |

```bash
# Get storage account connection string
CONN_STR=$(az storage account show-connection-string \
    --resource-group rg-my-app-prod-eastus \
    --name stmyappprodeastus \
    --query connectionString -o tsv)

# Create a container
az storage container create \
    --name my-app-uploads \
    --connection-string "$CONN_STR" \
    --public-access off

# Upload a blob
az storage blob upload \
    --container-name my-app-uploads \
    --name "2024/01/report.pdf" \
    --file ~/report.pdf \
    --connection-string "$CONN_STR"

# Download a blob
az storage blob download \
    --container-name my-app-uploads \
    --name "2024/01/report.pdf" \
    --file ~/downloaded-report.pdf \
    --connection-string "$CONN_STR"

# List blobs
az storage blob list \
    --container-name my-app-uploads \
    --connection-string "$CONN_STR" \
    --query '[*].{Name:name,Size:properties.contentLength,LastModified:properties.lastModified}' \
    --output table

# Change blob tier
az storage blob set-tier \
    --container-name my-app-uploads \
    --name "2024/01/report.pdf" \
    --tier Cool \
    --connection-string "$CONN_STR"
```

### Lifecycle Management Policy

Automatically transition blobs to cooler tiers or delete them based on age.

```bash
az storage account management-policy create \
    --account-name stmyappprodeastus \
    --resource-group rg-my-app-prod-eastus \
    --policy '{
        "rules": [
            {
                "name": "transition-to-cool",
                "enabled": true,
                "type": "Lifecycle",
                "definition": {
                    "actions": {
                        "baseBlob": {
                            "tierToCool": {"daysAfterModificationGreaterThan": 30},
                            "tierToArchive": {"daysAfterModificationGreaterThan": 90},
                            "delete": {"daysAfterModificationGreaterThan": 365}
                        },
                        "snapshot": {
                            "delete": {"daysAfterCreationGreaterThan": 90}
                        }
                    },
                    "filters": {
                        "blobTypes": ["blockBlob"],
                        "prefixMatch": ["logs/", "backups/"]
                    }
                }
            }
        ]
    }'
```

---

## Access Keys and SAS Tokens

### Access Keys (use with caution — full account access)

```bash
# Get access keys
az storage account keys list \
    --resource-group rg-my-app-prod-eastus \
    --account-name stmyappprodeastus \
    --output table

# Rotate key
az storage account keys renew \
    --resource-group rg-my-app-prod-eastus \
    --account-name stmyappprodeastus \
    --key primary
```

### SAS Tokens (time-limited, scoped access)

```bash
# Generate a SAS token for a container (read-only, 24 hours)
az storage container generate-sas \
    --account-name stmyappprodeastus \
    --name my-app-uploads \
    --permissions rl \
    --expiry $(date -u -d "+24 hours" +%Y-%m-%dT%H:%MZ 2>/dev/null || date -u -v+24H +%Y-%m-%dT%H:%MZ) \
    --https-only \
    --output tsv

# Generate a SAS token for a specific blob (write, 1 hour)
az storage blob generate-sas \
    --account-name stmyappprodeastus \
    --container-name my-app-uploads \
    --name "2024/01/report.pdf" \
    --permissions rw \
    --expiry $(date -u -d "+1 hour" +%Y-%m-%dT%H:%MZ 2>/dev/null || date -u -v+1H +%Y-%m-%dT%H:%MZ) \
    --https-only \
    --output tsv

# Generate account-level SAS (use sparingly)
az storage account generate-sas \
    --account-name stmyappprodeastus \
    --services b \
    --resource-types sco \
    --permissions rlwx \
    --expiry 2024-12-31 \
    --https-only \
    --output tsv
```

---

## Security

```bash
# Disable anonymous (public) blob access
az storage account update \
    --resource-group rg-my-app-prod-eastus \
    --name stmyappprodeastus \
    --allow-blob-public-access false

# Restrict access to specific VNet/subnet
SUBNET_ID=$(az network vnet subnet show \
    --resource-group rg-my-app-prod-eastus \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --name snet-backend-prod \
    --query id -o tsv)

az storage account network-rule add \
    --resource-group rg-my-app-prod-eastus \
    --account-name stmyappprodeastus \
    --subnet $SUBNET_ID

az storage account update \
    --resource-group rg-my-app-prod-eastus \
    --name stmyappprodeastus \
    --default-action Deny   # Deny all traffic not explicitly allowed

# Allow specific IP (e.g., CI/CD runner)
az storage account network-rule add \
    --resource-group rg-my-app-prod-eastus \
    --account-name stmyappprodeastus \
    --ip-address 203.0.113.10

# Enable Private Endpoint (preferred for production — no public exposure)
az network private-endpoint create \
    --resource-group rg-my-app-prod-eastus \
    --name pe-storage-my-app-prod \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-private-ep-prod \
    --private-connection-resource-id \
        $(az storage account show --name stmyappprodeastus --query id -o tsv) \
    --group-id blob \
    --connection-name conn-storage-my-app-prod

# Require Azure AD authentication (disable shared key auth — most secure)
az storage account update \
    --resource-group rg-my-app-prod-eastus \
    --name stmyappprodeastus \
    --allow-shared-key-access false
```

---

## Azure Files

```bash
# Create a file share
az storage share-rm create \
    --resource-group rg-my-app-prod-eastus \
    --storage-account stmyappprodeastus \
    --name my-app-share \
    --quota 100 \
    --enabled-protocols SMB

# Get connection info for mounting
az storage account show-connection-string \
    --resource-group rg-my-app-prod-eastus \
    --name stmyappprodeastus \
    --output tsv

# Mount on Linux (requires storage account key)
STORAGE_KEY=$(az storage account keys list \
    --resource-group rg-my-app-prod-eastus \
    --account-name stmyappprodeastus \
    --query '[0].value' -o tsv)

sudo mount -t cifs //stmyappprodeastus.file.core.windows.net/my-app-share /mnt/my-share \
    -o "vers=3.0,username=stmyappprodeastus,password=$STORAGE_KEY,dir_mode=0777,file_mode=0777,serverino"
```

---

## Python SDK

```python
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

credential = DefaultAzureCredential()
blob_client = BlobServiceClient(
    account_url="https://stmyappprodeastus.blob.core.windows.net",
    credential=credential
)

# Upload
container_client = blob_client.get_container_client("my-app-uploads")
with open("report.pdf", "rb") as f:
    container_client.upload_blob(
        name="2024/01/report.pdf",
        data=f,
        content_settings=ContentSettings(content_type="application/pdf"),
        overwrite=True
    )

# Generate SAS URL (using account key for signing)
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta, timezone

sas_token = generate_blob_sas(
    account_name="stmyappprodeastus",
    container_name="my-app-uploads",
    blob_name="2024/01/report.pdf",
    account_key=STORAGE_KEY,
    permission=BlobSasPermissions(read=True),
    expiry=datetime.now(timezone.utc) + timedelta(hours=1)
)
url = f"https://stmyappprodeastus.blob.core.windows.net/my-app-uploads/2024/01/report.pdf?{sas_token}"
```

---

## References

- [Azure Storage documentation](https://docs.microsoft.com/azure/storage/)
- [Blob storage lifecycle management](https://docs.microsoft.com/azure/storage/blobs/lifecycle-management-overview)
- [Azure Storage security guide](https://docs.microsoft.com/azure/storage/blobs/security-recommendations)
- [Azure Files documentation](https://docs.microsoft.com/azure/storage/files/)

---

← [Previous: Azure Storage](./README.md) | [Home](../../README.md) | [Next: Azure Databases →](../06-databases/README.md)
