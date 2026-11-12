← [Previous: PostgreSQL](./postgresql.md) | [Home](../../README.md) | [Next: Cosmos DB →](./cosmos-db.md)

---

# Azure SQL Database

Azure SQL Database is a fully managed relational database service built on SQL Server. It offers serverless compute, elastic pools, built-in HA, geo-replication, and automatic backups.

---

## Deployment Options

| Option | Use Case |
|--------|----------|
| **Single Database** | Isolated database with dedicated resources |
| **Elastic Pool** | Multiple databases sharing a pool of resources (cost-efficient for variable workloads) |
| **SQL Managed Instance** | Near-complete SQL Server compatibility (lift-and-shift) |
| **SQL Server on VM** | Full SQL Server control, OS-level access |

---

## Service Tiers

| Tier | Model | Best For |
|------|-------|----------|
| **General Purpose** | vCore (2–80 vCores) | Most production workloads |
| **Business Critical** | vCore + local SSD, 3 replicas | Low-latency, read scale |
| **Hyperscale** | vCore, up to 100 TB, read scale-out | Large databases |
| **Serverless** | Auto-pause, per-second billing | Dev/test, intermittent workloads |
| **Basic / Standard / Premium** | DTU model (legacy) | Simple workloads |

---

## Creating an Azure SQL Database

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
LOCATION="eastus"
SERVER_NAME="sql-my-app-prod-eastus"
ADMIN_USER="sqladmin"
ADMIN_PASS="$(openssl rand -base64 16)Aa1!"

# Create a logical SQL Server
az sql server create \
    --resource-group $RESOURCE_GROUP \
    --name $SERVER_NAME \
    --location $LOCATION \
    --admin-user $ADMIN_USER \
    --admin-password $ADMIN_PASS

# Disable public network access (use private endpoint)
az sql server update \
    --resource-group $RESOURCE_GROUP \
    --name $SERVER_NAME \
    --set publicNetworkAccess=Disabled

# Enable Azure AD admin (recommended — disable SQL auth for production)
az sql server ad-admin create \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --display-name "DBA-Group" \
    --object-id $(az ad group show --group "dba-team" --query id -o tsv)

# Create a General Purpose database
az sql db create \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name myappdb \
    --service-objective GP_Gen5_4 \
    --zone-redundant true \
    --backup-storage-redundancy Geo \
    --tags Environment=production Service=my-app
```

---

## Serverless Database

```bash
# Create a serverless database (auto-pause after 60 minutes of inactivity)
az sql db create \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name myappdb-dev \
    --edition GeneralPurpose \
    --compute-model Serverless \
    --family Gen5 \
    --min-capacity 0.5 \
    --capacity 4 \
    --auto-pause-delay 60

# Disable auto-pause for a period (e.g., during load testing)
az sql db update \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name myappdb-dev \
    --auto-pause-delay -1  # -1 = disabled
```

---

## Elastic Pool

```bash
# Create an elastic pool (up to 500 databases sharing 100 eDTUs)
az sql elastic-pool create \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name ep-my-app-prod \
    --edition Standard \
    --capacity 100 \
    --db-max-capacity 20 \
    --db-min-capacity 0

# Add a database to the elastic pool
az sql db update \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name myappdb \
    --elastic-pool ep-my-app-prod
```

---

## Geo-Replication and Failover Groups

```bash
# Create active geo-replication replica in West US
az sql db replica create \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name myappdb \
    --partner-server sql-my-app-dr-westus \
    --partner-resource-group rg-my-app-dr-westus

# Create a failover group (managed failover endpoint)
az sql failover-group create \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name fg-my-app-prod \
    --partner-server sql-my-app-dr-westus \
    --failover-policy Automatic \
    --grace-period 1  # Hours before automatic failover

# Manual failover (planned — no data loss)
az sql failover-group set-primary \
    --resource-group rg-my-app-dr-westus \
    --server sql-my-app-dr-westus \
    --name fg-my-app-prod

# Applications connect to the failover group endpoint — transparent failover
# Read-write:  fg-my-app-prod.database.windows.net
# Read-only:   fg-my-app-prod.secondary.database.windows.net
```

---

## Backup and Restore

```bash
# List available restore points
az sql db list-deleted \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --output table

# Restore to a point in time
az sql db restore \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name myappdb-restored \
    --source-database myappdb \
    --time "2024-06-15T10:00:00Z" \
    --service-objective GP_Gen5_4

# Long-term retention backup (weekly, monthly, yearly)
az sql db ltr-policy set \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --database myappdb \
    --weekly-retention P1W \
    --monthly-retention P1M \
    --yearly-retention P1Y \
    --week-of-year 1
```

---

## Firewall and Private Endpoint

```bash
# Allow Azure services through firewall (for PaaS-to-PaaS, not recommended for production)
az sql server firewall-rule create \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0

# Create private endpoint for SQL (preferred for production)
az network private-endpoint create \
    --resource-group $RESOURCE_GROUP \
    --name pe-sql \
    --vnet-name vnet-my-app-prod-eastus-001 \
    --subnet snet-private-endpoints \
    --private-connection-resource-id $(az sql server show \
        --resource-group $RESOURCE_GROUP \
        --name $SERVER_NAME --query id -o tsv) \
    --group-id sqlServer \
    --connection-name pe-conn-sql
```

---

## Python — pyodbc with Azure AD Token

```python
import os
import struct
import pyodbc
import logging
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

def get_sql_connection():
    """Connect to Azure SQL using Azure AD token (managed identity)."""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://database.windows.net/.default")

    # Convert token to bytes for pyodbc
    token_bytes = token.token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

    server = os.environ["SQL_SERVER"]  # sql-my-app-prod-eastus.database.windows.net
    database = os.environ["SQL_DATABASE"]

    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};DATABASE={database};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )

    logger.info("Connecting to Azure SQL", extra={"server": server, "database": database})
    conn = pyodbc.connect(conn_str, attrs_before={1256: token_struct})
    logger.info("Azure SQL connection established")
    return conn
```

---

## Useful Commands

```bash
# Show database details
az sql db show \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name myappdb \
    --query '{Name:name,Status:status,SKU:currentServiceObjectiveName,Size:maxSizeBytes,ZoneRedundant:zoneRedundant}' \
    --output json

# Scale up
az sql db update \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --name myappdb \
    --service-objective GP_Gen5_8

# List all databases on a server
az sql db list \
    --resource-group $RESOURCE_GROUP \
    --server $SERVER_NAME \
    --output table
```

---

## References

- [Azure SQL Database documentation](https://docs.microsoft.com/azure/azure-sql/database/)
- [Serverless tier](https://docs.microsoft.com/azure/azure-sql/database/serverless-tier-overview)
- [Failover groups](https://docs.microsoft.com/azure/azure-sql/database/auto-failover-group-overview)
- [Azure AD authentication](https://docs.microsoft.com/azure/azure-sql/database/authentication-aad-overview)

---

← [Previous: PostgreSQL](./postgresql.md) | [Home](../../README.md) | [Next: Cosmos DB →](./cosmos-db.md)
