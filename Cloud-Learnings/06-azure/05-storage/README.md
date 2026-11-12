← [Previous: Virtual Machines](../04-compute/virtual-machines.md) | [Home](../../README.md) | [Next: Storage Accounts →](./storage-accounts.md)

---

# Azure Storage

---

## Storage Services Overview

| Service | AWS Equivalent | Use case |
|---------|----------------|---------|
| **Azure Blob Storage** | S3 | Object/unstructured data — any file type at any scale |
| **Azure Files** | EFS / FSx for Windows | Fully managed SMB/NFS file shares |
| **Azure Managed Disks** | EBS | Block storage for VMs |
| **Azure Data Lake Storage Gen2** | S3 + Glue | Hierarchical namespace for analytics (ADLS Gen2 = Blob + HNS) |
| **Azure Queue Storage** | SQS (basic) | Simple message queuing between app components |
| **Azure Table Storage** | DynamoDB (basic) | NoSQL key-value store (consider Cosmos DB for production) |

---

## Storage Account

A Storage Account is the parent resource that contains Blob, Files, Queue, and Table.

```bash
RESOURCE_GROUP="rg-my-app-production"
LOCATION="eastus"

# Create a general-purpose v2 storage account (recommended default)
az storage account create \
    --resource-group $RESOURCE_GROUP \
    --name stmyappprodeastus \
    --location $LOCATION \
    --sku Standard_ZRS \
    --kind StorageV2 \
    --access-tier Hot \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false \
    --https-only true \
    --tags Environment=production Service=my-app

# Get connection string
az storage account show-connection-string \
    --resource-group $RESOURCE_GROUP \
    --name stmyappprodeastus \
    --query connectionString --output tsv

# Get account key
az storage account keys list \
    --resource-group $RESOURCE_GROUP \
    --account-name stmyappprodeastus \
    --query '[0].value' --output tsv
```

### Redundancy Options

| SKU | Redundancy | Availability |
|-----|------------|-------------|
| `LRS` | Local (3 copies, 1 datacenter) | 99.9% |
| `ZRS` | Zone (3 copies, 3 AZs) | 99.99% — **recommended** |
| `GRS` | Geo (LRS + async replica to paired region) | 99.9% + DR |
| `GZRS` | Geo-Zone (ZRS + async replica) | 99.99% + DR |

---

## Azure Blob Storage

### Containers and Objects

```bash
ACCOUNT_NAME="stmyappprodeastus"
ACCOUNT_KEY=$(az storage account keys list \
    --resource-group $RESOURCE_GROUP \
    --account-name $ACCOUNT_NAME \
    --query '[0].value' --output tsv)

# Create a container (private by default)
az storage container create \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --name my-app-data \
    --public-access off

# Upload a file
az storage blob upload \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --container-name my-app-data \
    --file ./report.pdf \
    --name reports/2024/report.pdf \
    --content-type "application/pdf"

# Upload a directory recursively
az storage blob upload-batch \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --destination my-app-data \
    --source ./dist \
    --pattern "**" \
    --content-cache-control "public, max-age=31536000"

# List blobs
az storage blob list \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --container-name my-app-data \
    --prefix "reports/" \
    --query '[*].{Name:name,Size:properties.contentLength,Modified:properties.lastModified}' \
    --output table

# Download
az storage blob download \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --container-name my-app-data \
    --name reports/2024/report.pdf \
    --file /tmp/report.pdf

# Delete a blob
az storage blob delete \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --container-name my-app-data \
    --name reports/2024/report.pdf
```

### Access Tiers

| Tier | Storage Cost | Access Cost | Use |
|------|-------------|------------|-----|
| **Hot** | High | Low | Frequently accessed data |
| **Cool** | Medium | Medium | Infrequently accessed (30+ days) |
| **Cold** | Low | High | Rarely accessed (90+ days) |
| **Archive** | Very low | Very high + hours to rehydrate | Long-term backup (180+ days) |

```bash
# Set tier on upload
az storage blob upload \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --container-name my-app-data \
    --file old-backup.tar.gz \
    --name backups/old-backup.tar.gz \
    --tier Cool

# Move existing blob to Archive
az storage blob set-tier \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --container-name my-app-data \
    --name backups/old-backup.tar.gz \
    --tier Archive
```

### Lifecycle Management

```bash
az storage account management-policy create \
    --account-name $ACCOUNT_NAME \
    --resource-group $RESOURCE_GROUP \
    --policy '{
        "rules": [
            {
                "name": "move-to-cool",
                "enabled": true,
                "type": "Lifecycle",
                "definition": {
                    "filters": {"blobTypes": ["blockBlob"], "prefixMatch": ["data/"]},
                    "actions": {
                        "baseBlob": {
                            "tierToCool": {"daysAfterModificationGreaterThan": 30},
                            "tierToArchive": {"daysAfterModificationGreaterThan": 90},
                            "delete": {"daysAfterModificationGreaterThan": 365}
                        },
                        "snapshot": {
                            "delete": {"daysAfterCreationGreaterThan": 30}
                        }
                    }
                }
            }
        ]
    }'
```

### Shared Access Signatures (SAS)

```bash
# Generate a time-limited SAS token for a blob (read-only, 1 hour)
EXPIRY=$(date -u -v+1H +"%Y-%m-%dT%H:%MZ" 2>/dev/null || date -u -d '+1 hour' +"%Y-%m-%dT%H:%MZ")

SAS_TOKEN=$(az storage blob generate-sas \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --container-name my-app-data \
    --name reports/2024/report.pdf \
    --permissions r \
    --expiry $EXPIRY \
    --output tsv)

echo "https://${ACCOUNT_NAME}.blob.core.windows.net/my-app-data/reports/2024/report.pdf?${SAS_TOKEN}"

# Generate SAS for an entire container (write-only, for upload scenarios)
az storage container generate-sas \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --name uploads \
    --permissions cw \
    --expiry $EXPIRY \
    --output tsv
```

---

## Azure Files

```bash
# Create a file share
az storage share create \
    --account-name $ACCOUNT_NAME \
    --account-key $ACCOUNT_KEY \
    --name my-app-share \
    --quota 100  # GB

# Mount on Linux (requires SMB)
STORAGE_KEY=$(az storage account keys list \
    --resource-group $RESOURCE_GROUP \
    --account-name $ACCOUNT_NAME \
    --query '[0].value' --output tsv)

mkdir -p /mnt/my-app-share
mount -t cifs //${ACCOUNT_NAME}.file.core.windows.net/my-app-share /mnt/my-app-share \
    -o "vers=3.0,username=${ACCOUNT_NAME},password=${STORAGE_KEY},dir_mode=0777,file_mode=0777,serverino"

# Add to /etc/fstab for persistent mount
echo "//${ACCOUNT_NAME}.file.core.windows.net/my-app-share /mnt/my-app-share cifs nofail,credentials=/etc/smbcredentials/${ACCOUNT_NAME}.cred,dir_mode=0777,file_mode=0777,serverino" >> /etc/fstab

# NFS mount (Premium Files with HNS, requires private endpoint)
mount -t nfs ${ACCOUNT_NAME}.file.core.windows.net:/${ACCOUNT_NAME}/my-app-share /mnt/my-app-share \
    -o vers=4,minorversion=1,sec=sys
```

---

## Azure Managed Disks

```bash
# Create a standalone Premium SSD disk
az disk create \
    --resource-group $RESOURCE_GROUP \
    --name disk-my-app-data-001 \
    --size-gb 512 \
    --sku Premium_LRS \
    --zone 1

# Disk SKUs comparison
# Standard_LRS  — HDD, backup/cold data
# Standard_SSD_LRS — SSD, dev/test
# Premium_LRS   — SSD, production workloads (up to 80K IOPS, 750 MB/s)
# UltraSSD_LRS  — SSD, 160K+ IOPS, configurable — databases, I/O intensive

# Resize a disk (can grow, never shrink without stopping VM)
az disk update \
    --resource-group $RESOURCE_GROUP \
    --name disk-my-app-data-001 \
    --size-gb 1024

# Create a snapshot
az snapshot create \
    --resource-group $RESOURCE_GROUP \
    --name snap-disk-my-app-$(date +%Y%m%d) \
    --source disk-my-app-data-001 \
    --incremental

# Enable customer-managed key encryption
az disk update \
    --resource-group $RESOURCE_GROUP \
    --name disk-my-app-data-001 \
    --disk-encryption-set $DES_ID
```

---

## Storage Python SDK Pattern

```python
import logging
import os
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Use DefaultAzureCredential — works with managed identity, CLI login, env vars
credential = DefaultAzureCredential()
account_url = f"https://{os.environ['STORAGE_ACCOUNT']}.blob.core.windows.net"
service_client = BlobServiceClient(account_url=account_url, credential=credential)


def upload_file(container_name: str, blob_name: str, file_path: str) -> str:
    """Upload a file to blob storage and return the blob URL."""
    logger.info("Uploading file: container=%s blob=%s path=%s", container_name, blob_name, file_path)
    blob_client = service_client.get_blob_client(container=container_name, blob=blob_name)
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    logger.info("Upload complete: blob_url=%s", blob_client.url)
    return blob_client.url


def generate_sas_url(container_name: str, blob_name: str, expiry_hours: int = 1) -> str:
    """Generate a time-limited SAS URL for downloading a blob."""
    expiry = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
    sas_token = generate_blob_sas(
        account_name=os.environ["STORAGE_ACCOUNT"],
        container_name=container_name,
        blob_name=blob_name,
        account_key=os.environ["STORAGE_ACCOUNT_KEY"],
        permission=BlobSasPermissions(read=True),
        expiry=expiry,
    )
    url = f"{account_url}/{container_name}/{blob_name}?{sas_token}"
    logger.info("SAS URL generated: blob=%s expiry=%s", blob_name, expiry.isoformat())
    return url
```

---

## References

- [Azure Blob Storage documentation](https://docs.microsoft.com/azure/storage/blobs/)
- [Azure Files documentation](https://docs.microsoft.com/azure/storage/files/)
- [Managed Disks documentation](https://docs.microsoft.com/azure/virtual-machines/managed-disks-overview)
- [Azure Storage pricing](https://azure.microsoft.com/pricing/details/storage/)
---

← [Previous: Virtual Machines](../04-compute/virtual-machines.md) | [Home](../../README.md) | [Next: Storage Accounts →](./storage-accounts.md)
