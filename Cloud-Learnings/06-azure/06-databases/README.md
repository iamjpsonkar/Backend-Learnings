← [Previous: Storage Accounts](../05-storage/storage-accounts.md) | [Home](../../README.md) | [Next: PostgreSQL →](./postgresql.md)

---

# Azure Databases

---

## Service Selection

| Service | AWS Equivalent | Use case |
|---------|----------------|---------|
| **Azure SQL Database** | RDS SQL Server | Managed SQL Server — PaaS, serverless option |
| **Azure Database for PostgreSQL Flexible Server** | RDS PostgreSQL / Aurora PostgreSQL | Managed PostgreSQL — best for new workloads |
| **Azure Database for MySQL Flexible Server** | RDS MySQL / Aurora MySQL | Managed MySQL |
| **Azure Cosmos DB** | DynamoDB | Multi-model NoSQL — global distribution, multiple APIs |
| **Azure Cache for Redis** | ElastiCache for Redis | Managed Redis — cache, sessions, rate limiting |
| **Azure SQL Managed Instance** | RDS Custom / EC2 SQL Server | Near 100% SQL Server compatibility, lift-and-shift |
| **Azure Synapse Analytics** | Redshift + Glue | Data warehouse + ETL |

---

## Azure Database for PostgreSQL Flexible Server

```bash
RESOURCE_GROUP="rg-my-app-production"
LOCATION="eastus"
PG_ADMIN="pgadmin"

# Create Flexible Server (recommended over Single Server — deprecated)
az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name pg-my-app-prod-eastus \
    --location $LOCATION \
    --sku-name Standard_D4s_v3 \
    --tier GeneralPurpose \
    --storage-size 128 \
    --version 16 \
    --admin-user $PG_ADMIN \
    --admin-password "Str0ngP@ssw0rd!" \
    --high-availability ZoneRedundant \
    --zone 1 \
    --standby-zone 2 \
    --vnet vnet-my-app-prod-eastus-001 \
    --subnet snet-data \
    --private-dns-zone pg-my-app-prod-eastus.private.postgres.database.azure.com \
    --tags Environment=production Service=my-app

# Create a database
az postgres flexible-server db create \
    --resource-group $RESOURCE_GROUP \
    --server-name pg-my-app-prod-eastus \
    --database-name myapp

# Show connection string
az postgres flexible-server show-connection-string \
    --server-name pg-my-app-prod-eastus \
    --admin-user $PG_ADMIN \
    --admin-password "Str0ngP@ssw0rd!" \
    --database-name myapp \
    --query connectionStrings.psql_cmd --output tsv

# Configure parameters (e.g., max_connections, shared_buffers)
az postgres flexible-server parameter set \
    --resource-group $RESOURCE_GROUP \
    --server-name pg-my-app-prod-eastus \
    --name max_connections \
    --value 200

# Create a read replica in another region
az postgres flexible-server replica create \
    --resource-group $RESOURCE_GROUP \
    --replica-name pg-my-app-prod-westus-replica \
    --source-server pg-my-app-prod-eastus \
    --location westus

# Point-in-time restore
az postgres flexible-server restore \
    --resource-group $RESOURCE_GROUP \
    --name pg-my-app-restored \
    --source-server pg-my-app-prod-eastus \
    --restore-time "2024-06-01T12:00:00Z"

# View server metrics
az monitor metrics list \
    --resource $(az postgres flexible-server show \
        --resource-group $RESOURCE_GROUP \
        --name pg-my-app-prod-eastus \
        --query id --output tsv) \
    --metric cpu_percent storage_percent active_connections \
    --interval PT1M \
    --output table
```

---

## Azure SQL Database

```bash
# Create SQL Server (logical server — container for databases)
az sql server create \
    --resource-group $RESOURCE_GROUP \
    --name sql-my-app-prod-eastus \
    --location $LOCATION \
    --admin-user sqladmin \
    --admin-password "Str0ngP@ssw0rd!" \
    --enable-public-network false

# Create a database (Serverless — scales to zero when idle)
az sql db create \
    --resource-group $RESOURCE_GROUP \
    --server sql-my-app-prod-eastus \
    --name myapp \
    --compute-model Serverless \
    --edition GeneralPurpose \
    --family Gen5 \
    --min-capacity 0.5 \
    --capacity 4 \
    --auto-pause-delay 60 \
    --zone-redundant true \
    --backup-storage-redundancy Zone

# General Purpose (provisioned) — for consistent latency
az sql db create \
    --resource-group $RESOURCE_GROUP \
    --server sql-my-app-prod-eastus \
    --name myapp-prod \
    --service-objective GP_Gen5_4 \
    --zone-redundant true \
    --backup-storage-redundancy Zone

# Enable Azure Defender for SQL (advanced threat protection)
az sql server threat-policy update \
    --resource-group $RESOURCE_GROUP \
    --server sql-my-app-prod-eastus \
    --state Enabled \
    --email-addresses "security@example.com" \
    --email-account-admins true

# Show connection strings
az sql db show-connection-string \
    --server sql-my-app-prod-eastus \
    --name myapp \
    --client ado.net
```

---

## Azure Cosmos DB

Cosmos DB is a globally distributed, multi-model NoSQL database. Choose the API that matches your workload.

| API | AWS Equivalent | Data Model |
|-----|----------------|-----------|
| **NoSQL** | DynamoDB | JSON documents — native Cosmos API |
| **MongoDB** | DocumentDB | BSON documents — MongoDB wire protocol |
| **Apache Cassandra** | Keyspaces | Wide-column |
| **Apache Gremlin** | Neptune | Graph database |
| **Table** | DynamoDB | Key-value (Azure Table Storage compatible) |
| **PostgreSQL** | Aurora PostgreSQL | Distributed PostgreSQL (via Citus) |

```bash
# Create a Cosmos DB account (NoSQL API, multi-region)
az cosmosdb create \
    --resource-group $RESOURCE_GROUP \
    --name cosmos-my-app-prod-eastus \
    --kind GlobalDocumentDB \
    --locations regionName=eastus failoverPriority=0 isZoneRedundant=true \
    --locations regionName=westus failoverPriority=1 isZoneRedundant=false \
    --default-consistency-level Session \
    --enable-automatic-failover true \
    --ip-range-filter "" \
    --enable-virtual-network true \
    --virtual-network-rules vnet-my-app-prod-eastus-001 \
    --tags Environment=production

# Create a database
az cosmosdb sql database create \
    --resource-group $RESOURCE_GROUP \
    --account-name cosmos-my-app-prod-eastus \
    --name myapp \
    --throughput 400

# Create a container with partition key
az cosmosdb sql container create \
    --resource-group $RESOURCE_GROUP \
    --account-name cosmos-my-app-prod-eastus \
    --database-name myapp \
    --name orders \
    --partition-key-path "/customerId" \
    --throughput 1000 \
    --idx '{
        "indexingMode": "consistent",
        "automatic": true,
        "includedPaths": [{"path": "/*"}],
        "excludedPaths": [{"path": "/payload/*"}]
    }'

# Enable autoscale (scales 100–10,000 RU/s automatically)
az cosmosdb sql container throughput update \
    --resource-group $RESOURCE_GROUP \
    --account-name cosmos-my-app-prod-eastus \
    --database-name myapp \
    --name orders \
    --max-throughput 10000

# Get primary key
az cosmosdb keys list \
    --resource-group $RESOURCE_GROUP \
    --name cosmos-my-app-prod-eastus \
    --type keys \
    --query primaryMasterKey --output tsv
```

### Consistency Levels

| Level | Reads | Latency | Use |
|-------|-------|---------|-----|
| **Strong** | Always latest | Highest | Financial transactions |
| **Bounded Staleness** | Latest within lag | Medium | Global apps needing bounded freshness |
| **Session** | Latest for same session | Low | **Default — recommended for most apps** |
| **Consistent Prefix** | Ordered but potentially stale | Low | Social media feeds |
| **Eventual** | No ordering guarantee | Lowest | Non-critical reads (counters, popularity) |

---

## Azure Cache for Redis

```bash
# Create Redis cache (Standard C2 — 6 GB, with replication)
az redis create \
    --resource-group $RESOURCE_GROUP \
    --name redis-my-app-prod-eastus \
    --location $LOCATION \
    --sku Standard \
    --vm-size C2 \
    --enable-non-ssl-port false \
    --minimum-tls-version 1.2 \
    --tags Environment=production

# Get connection details
az redis show \
    --resource-group $RESOURCE_GROUP \
    --name redis-my-app-prod-eastus \
    --query '{Host:hostName,Port:sslPort,Status:provisioningState}'

# Get access key
az redis list-keys \
    --resource-group $RESOURCE_GROUP \
    --name redis-my-app-prod-eastus \
    --query primaryKey --output tsv

# Redis SKUs
# Basic C0–C6: single node, no SLA — dev/test only
# Standard C0–C6: replicated, SLA — production
# Premium P1–P5: clustering, persistence, VNet, geo-replication
```

### Python Redis Pattern

```python
import redis
import json
import logging
import os
from functools import wraps

logger = logging.getLogger(__name__)

_redis_client = redis.StrictRedis(
    host=os.environ["REDIS_HOST"],
    port=6380,
    password=os.environ["REDIS_KEY"],
    ssl=True,
    decode_responses=True,
    socket_timeout=2,
    socket_connect_timeout=2,
)


def cache_aside(key_prefix: str, ttl_seconds: int = 300):
    """Cache-aside decorator — returns cached value or calls function and caches result."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"
            try:
                cached = _redis_client.get(cache_key)
                if cached:
                    logger.debug("Cache hit: key=%s", cache_key)
                    return json.loads(cached)
                logger.debug("Cache miss: key=%s", cache_key)
            except redis.RedisError as e:
                logger.warning("Redis read failed, bypassing cache: key=%s error=%s", cache_key, str(e))

            result = func(*args, **kwargs)

            try:
                _redis_client.setex(cache_key, ttl_seconds, json.dumps(result))
                logger.debug("Cached result: key=%s ttl=%d", cache_key, ttl_seconds)
            except redis.RedisError as e:
                logger.warning("Redis write failed: key=%s error=%s", cache_key, str(e))

            return result
        return wrapper
    return decorator


@cache_aside("user", ttl_seconds=600)
def get_user(user_id: str) -> dict:
    logger.info("Fetching user from database: user_id=%s", user_id)
    # ... database query ...
    return {"id": user_id, "name": "Alice"}
```

---

## References

- [Azure Database for PostgreSQL](https://docs.microsoft.com/azure/postgresql/)
- [Azure SQL Database](https://docs.microsoft.com/azure/azure-sql/database/)
- [Azure Cosmos DB](https://docs.microsoft.com/azure/cosmos-db/)
- [Azure Cache for Redis](https://docs.microsoft.com/azure/azure-cache-for-redis/)
---

← [Previous: Storage Accounts](../05-storage/storage-accounts.md) | [Home](../../README.md) | [Next: PostgreSQL →](./postgresql.md)
