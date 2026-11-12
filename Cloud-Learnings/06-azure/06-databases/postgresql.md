← [Previous: Azure Databases](./README.md) | [Home](../../README.md) | [Next: Azure SQL →](./azure-sql.md)

---

# Azure Database for PostgreSQL — Flexible Server

Azure Database for PostgreSQL Flexible Server is a fully managed PostgreSQL service with zone-redundant HA, read replicas, PITR, and private networking support.

---

## Flexible Server vs Single Server

Flexible Server is the recommended deployment option — Single Server is deprecated.

| Feature | Flexible Server |
|---------|----------------|
| Versions | PostgreSQL 11–16 |
| HA | Zone-redundant standby (same-zone or cross-zone) |
| Read replicas | Up to 5, cross-region supported |
| PITR | 7–35 days retention |
| Stop/Start | Yes (save costs in dev/test) |
| Private networking | VNet injection or private endpoint |
| Maintenance window | Custom (user-defined) |
| Burstable SKUs | Yes (B1ms → B16ms) |

---

## Creating a Flexible Server

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
LOCATION="eastus"
SERVER_NAME="psql-my-app-prod-eastus"
ADMIN_USER="pgadmin"
ADMIN_PASS="$(openssl rand -base64 16)Aa1!"  # Must meet complexity requirements

# Create PostgreSQL Flexible Server with VNet injection + HA
az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name $SERVER_NAME \
    --location $LOCATION \
    --version 16 \
    --sku-name Standard_D4s_v3 \
    --tier GeneralPurpose \
    --storage-size 128 \
    --storage-auto-grow Enabled \
    --high-availability ZoneRedundant \
    --standby-zone 2 \
    --vnet vnet-my-app-prod-eastus-001 \
    --subnet snet-data \
    --private-dns-zone psql-my-app-prod-eastus.private.postgres.database.azure.com \
    --admin-user $ADMIN_USER \
    --admin-password $ADMIN_PASS \
    --backup-retention 14 \
    --geo-redundant-backup Enabled \
    --tags Environment=production Service=my-app

echo "Admin password: $ADMIN_PASS"  # Save to Key Vault immediately
```

---

## Database and User Management

```bash
# Create a database
az postgres flexible-server db create \
    --resource-group $RESOURCE_GROUP \
    --server-name $SERVER_NAME \
    --database-name myappdb

# List databases
az postgres flexible-server db list \
    --resource-group $RESOURCE_GROUP \
    --server-name $SERVER_NAME \
    --output table

# Connect via psql (from a VM or Bastion inside the VNet)
psql "host=$SERVER_NAME.postgres.database.azure.com \
     port=5432 \
     dbname=myappdb \
     user=$ADMIN_USER \
     sslmode=require"

# Create application user (least privilege)
# Run inside psql:
# CREATE ROLE appuser WITH LOGIN PASSWORD 'AppPass123!';
# GRANT CONNECT ON DATABASE myappdb TO appuser;
# GRANT USAGE ON SCHEMA public TO appuser;
# GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO appuser;
# ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO appuser;
```

---

## Server Parameters

```bash
# List configurable server parameters
az postgres flexible-server parameter list \
    --resource-group $RESOURCE_GROUP \
    --server-name $SERVER_NAME \
    --query '[*].{Name:name,Value:value,DefaultValue:defaultValue}' \
    --output table

# Tune for production (adjust as needed)
az postgres flexible-server parameter set \
    --resource-group $RESOURCE_GROUP \
    --server-name $SERVER_NAME \
    --name max_connections --value 500

az postgres flexible-server parameter set \
    --resource-group $RESOURCE_GROUP \
    --server-name $SERVER_NAME \
    --name shared_buffers --value 4096000  # 4 GB in kB

az postgres flexible-server parameter set \
    --resource-group $RESOURCE_GROUP \
    --server-name $SERVER_NAME \
    --name work_mem --value 65536  # 64 MB

az postgres flexible-server parameter set \
    --resource-group $RESOURCE_GROUP \
    --server-name $SERVER_NAME \
    --name log_min_duration_statement --value 1000  # Log queries > 1s
```

---

## Read Replicas

```bash
# Create a read replica (cross-region for disaster recovery reads)
az postgres flexible-server replica create \
    --resource-group $RESOURCE_GROUP \
    --replica-name psql-my-app-replica-westus \
    --source-server $SERVER_NAME \
    --location westus

# List replicas
az postgres flexible-server replica list \
    --resource-group $RESOURCE_GROUP \
    --name $SERVER_NAME \
    --output table

# Promote replica to standalone (failover / read scaling)
az postgres flexible-server replica stop-replication \
    --resource-group $RESOURCE_GROUP \
    --name psql-my-app-replica-westus
```

---

## Point-in-Time Restore

```bash
# Restore to a specific point in time (creates a new server)
az postgres flexible-server restore \
    --resource-group $RESOURCE_GROUP \
    --name psql-my-app-restored \
    --source-server $SERVER_NAME \
    --restore-time "2024-06-15T10:00:00Z" \
    --sku-name Standard_D4s_v3 \
    --tier GeneralPurpose
```

---

## Stop / Start (Dev/Test Cost Saving)

```bash
# Stop server (compute billing pauses; storage still billed)
az postgres flexible-server stop \
    --resource-group $RESOURCE_GROUP \
    --name $SERVER_NAME

# Start server
az postgres flexible-server start \
    --resource-group $RESOURCE_GROUP \
    --name $SERVER_NAME

# Show server status
az postgres flexible-server show \
    --resource-group $RESOURCE_GROUP \
    --name $SERVER_NAME \
    --query '{State:state,SKU:sku.name,Version:version,FQDN:fullyQualifiedDomainName}' \
    --output json
```

---

## Python — asyncpg / psycopg2 with Managed Identity

```python
import asyncpg
import os
from azure.identity import DefaultAzureCredential
import logging

logger = logging.getLogger(__name__)

async def get_pg_connection():
    """Get PostgreSQL connection using Azure AD token (no password)."""
    credential = DefaultAzureCredential()
    # Request token for PostgreSQL
    token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")

    host = os.environ["PG_HOST"]  # e.g. psql-my-app-prod-eastus.postgres.database.azure.com
    db = os.environ["PG_DATABASE"]
    user = os.environ["PG_USER"]  # Managed identity client ID or UPN

    logger.info("Connecting to PostgreSQL", extra={"host": host, "database": db})

    conn = await asyncpg.connect(
        host=host,
        port=5432,
        database=db,
        user=user,
        password=token.token,
        ssl="require",
    )
    logger.info("PostgreSQL connection established")
    return conn
```

---

## Monitoring

```bash
# View metrics (connections, CPU, storage)
az monitor metrics list \
    --resource $(az postgres flexible-server show \
        --resource-group $RESOURCE_GROUP \
        --name $SERVER_NAME --query id -o tsv) \
    --metric "active_connections" \
    --interval PT5M \
    --aggregation Average \
    --output table

# Enable diagnostic logs to Log Analytics
az monitor diagnostic-settings create \
    --name psql-diag \
    --resource $(az postgres flexible-server show \
        --resource-group $RESOURCE_GROUP \
        --name $SERVER_NAME --query id -o tsv) \
    --workspace $(az monitor log-analytics workspace show \
        --resource-group rg-platform-monitoring-eastus \
        --workspace-name log-platform-prod-eastus --query id -o tsv) \
    --logs '[{"category":"PostgreSQLLogs","enabled":true},{"category":"QueryStoreRuntimeStatistics","enabled":true}]' \
    --metrics '[{"category":"AllMetrics","enabled":true}]'
```

---

## References

- [Azure Database for PostgreSQL Flexible Server](https://docs.microsoft.com/azure/postgresql/flexible-server/)
- [High availability concepts](https://docs.microsoft.com/azure/postgresql/flexible-server/concepts-high-availability)
- [Azure AD authentication for PostgreSQL](https://docs.microsoft.com/azure/postgresql/flexible-server/concepts-azure-ad-authentication)

---

← [Previous: Azure Databases](./README.md) | [Home](../../README.md) | [Next: Azure SQL →](./azure-sql.md)
