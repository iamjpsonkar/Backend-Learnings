← [Previous: Azure SQL](./azure-sql.md) | [Home](../../README.md) | [Next: Redis Cache →](./redis.md)

---

# Azure Cosmos DB

Cosmos DB is a globally distributed, multi-model NoSQL database. It offers single-digit millisecond latency, 99.999% availability SLAs, and automatic multi-region replication.

---

## APIs Supported

| API | Data Model | AWS Equivalent |
|-----|-----------|----------------|
| **NoSQL (Core)** | JSON documents | DynamoDB |
| **MongoDB** | BSON documents | DocumentDB |
| **Cassandra** | Wide-column | Keyspaces |
| **Gremlin** | Graph | Neptune |
| **Table** | Key-value | DynamoDB (simple) |
| **PostgreSQL** | Relational (Citus) | Aurora |

The **NoSQL API** is the native and recommended API for new workloads.

---

## Consistency Levels

Cosmos DB offers 5 tunable consistency levels (strongest to weakest):

| Level | Guarantee | Latency | Use Case |
|-------|-----------|---------|----------|
| **Strong** | Linearizability | Highest | Financial transactions |
| **Bounded Staleness** | Reads lag writes by K ops or T time | High | Leader-follower with bounded lag |
| **Session** (default) | Consistent within a client session | Medium | User-specific data (cart, profile) |
| **Consistent Prefix** | Reads never see out-of-order writes | Low | Social feeds |
| **Eventual** | No ordering guarantees | Lowest | Counters, likes, analytics |

---

## Creating a Cosmos DB Account

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
ACCOUNT_NAME="cosmos-my-app-prod-eastus"

# Create account (NoSQL API, multi-region, session consistency)
az cosmosdb create \
    --resource-group $RESOURCE_GROUP \
    --name $ACCOUNT_NAME \
    --kind GlobalDocumentDB \
    --locations regionName=eastus failoverPriority=0 isZoneRedundant=true \
    --locations regionName=westus failoverPriority=1 isZoneRedundant=false \
    --default-consistency-level Session \
    --enable-automatic-failover true \
    --enable-multiple-write-locations false \
    --network-acl-bypass None \
    --public-network-access Disabled \
    --tags Environment=production Service=my-app

# Create database
az cosmosdb sql database create \
    --resource-group $RESOURCE_GROUP \
    --account-name $ACCOUNT_NAME \
    --name myappdb \
    --throughput 400  # Shared throughput for all containers in the database

# Create container with partition key
az cosmosdb sql container create \
    --resource-group $RESOURCE_GROUP \
    --account-name $ACCOUNT_NAME \
    --database-name myappdb \
    --name orders \
    --partition-key-path "/customerId" \
    --throughput 1000

# Container with autoscale (recommended for variable workloads)
az cosmosdb sql container create \
    --resource-group $RESOURCE_GROUP \
    --account-name $ACCOUNT_NAME \
    --database-name myappdb \
    --name events \
    --partition-key-path "/eventType" \
    --max-throughput 10000  # Autoscale: will scale 1000–10000 RU/s automatically
```

---

## Throughput — RU/s and Autoscale

```bash
# Update container throughput (manual)
az cosmosdb sql container throughput update \
    --resource-group $RESOURCE_GROUP \
    --account-name $ACCOUNT_NAME \
    --database-name myappdb \
    --name orders \
    --throughput 5000

# Migrate from manual to autoscale
az cosmosdb sql container throughput migrate \
    --resource-group $RESOURCE_GROUP \
    --account-name $ACCOUNT_NAME \
    --database-name myappdb \
    --name orders \
    --throughput-type autoscale

# Show current throughput
az cosmosdb sql container throughput show \
    --resource-group $RESOURCE_GROUP \
    --account-name $ACCOUNT_NAME \
    --database-name myappdb \
    --name orders
```

---

## Multi-Region Writes (Active-Active)

```bash
# Enable multi-region writes (all regions accept writes)
az cosmosdb update \
    --resource-group $RESOURCE_GROUP \
    --name $ACCOUNT_NAME \
    --enable-multiple-write-locations true

# Add a write region
az cosmosdb update \
    --resource-group $RESOURCE_GROUP \
    --name $ACCOUNT_NAME \
    --locations regionName=eastus failoverPriority=0 isZoneRedundant=true \
    --locations regionName=westeurope failoverPriority=1 isZoneRedundant=true \
    --locations regionName=southeastasia failoverPriority=2 isZoneRedundant=false

# Manual failover (for planned maintenance)
az cosmosdb failover-priority-change \
    --resource-group $RESOURCE_GROUP \
    --name $ACCOUNT_NAME \
    --failover-policies eastus=0 westus=1
```

---

## Python SDK

```python
import os
import logging
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

def get_cosmos_client() -> CosmosClient:
    """Get Cosmos DB client using managed identity (no connection string)."""
    account_url = os.environ["COSMOS_ACCOUNT_URL"]
    credential = DefaultAzureCredential()
    logger.info("Creating Cosmos DB client", extra={"account": account_url})
    return CosmosClient(url=account_url, credential=credential)


def upsert_order(order: dict) -> dict:
    """Upsert an order document into the orders container."""
    client = get_cosmos_client()
    container = (
        client.get_database_client("myappdb")
              .get_container_client("orders")
    )

    order_id = order.get("id", "unknown")
    customer_id = order.get("customerId", "unknown")
    logger.info("Upserting order", extra={"order_id": order_id, "customer_id": customer_id})

    try:
        result = container.upsert_item(body=order)
        logger.info("Order upserted", extra={"order_id": order_id, "etag": result.get("_etag")})
        return result
    except exceptions.CosmosHttpResponseError as exc:
        logger.error("Cosmos upsert failed", extra={"order_id": order_id, "status": exc.status_code, "error": str(exc)})
        raise


def query_orders(customer_id: str) -> list[dict]:
    """Query all orders for a customer."""
    client = get_cosmos_client()
    container = (
        client.get_database_client("myappdb")
              .get_container_client("orders")
    )

    query = "SELECT * FROM c WHERE c.customerId = @customerId ORDER BY c._ts DESC"
    params = [{"name": "@customerId", "value": customer_id}]

    logger.info("Querying orders", extra={"customer_id": customer_id})
    items = list(container.query_items(
        query=query,
        parameters=params,
        partition_key=customer_id,  # Cross-partition query avoided — always pass partition key
    ))
    logger.info("Orders query complete", extra={"customer_id": customer_id, "count": len(items)})
    return items


def delete_order(order_id: str, customer_id: str) -> None:
    """Delete an order by ID and partition key."""
    client = get_cosmos_client()
    container = (
        client.get_database_client("myappdb")
              .get_container_client("orders")
    )

    logger.info("Deleting order", extra={"order_id": order_id, "customer_id": customer_id})
    try:
        container.delete_item(item=order_id, partition_key=customer_id)
        logger.info("Order deleted", extra={"order_id": order_id})
    except exceptions.CosmosResourceNotFoundError:
        logger.warning("Order not found for deletion", extra={"order_id": order_id})
```

---

## Change Feed

The change feed streams all inserts and updates from a container in order, enabling event-driven patterns.

```python
from azure.cosmos import CosmosClient
from azure.cosmos.partition_key import PartitionKey
import logging

logger = logging.getLogger(__name__)

def process_change_feed(account_url: str, credential, last_continuation: str | None = None):
    """Process the change feed from the orders container."""
    client = CosmosClient(url=account_url, credential=credential)
    container = client.get_database_client("myappdb").get_container_client("orders")

    logger.info("Starting change feed processing", extra={"has_continuation": bool(last_continuation)})
    feed_iterator = container.query_items_change_feed(
        is_start_from_beginning=not last_continuation,
        continuation=last_continuation,
    )

    for item in feed_iterator:
        logger.info("Change feed item", extra={"id": item.get("id"), "type": item.get("type")})
        # Process item...

    continuation = container.client_connection.last_response_headers.get("etag")
    logger.info("Change feed batch complete", extra={"continuation_token": continuation})
    return continuation
```

---

## TTL (Time-to-Live)

```bash
# Enable TTL on a container (items with _ttl field auto-expire)
az cosmosdb sql container update \
    --resource-group $RESOURCE_GROUP \
    --account-name $ACCOUNT_NAME \
    --database-name myappdb \
    --name sessions \
    --ttl 3600  # Items expire 1 hour after last update
    # Set --ttl -1 to enable container-level TTL but respect per-item ttl field
```

---

## References

- [Azure Cosmos DB documentation](https://docs.microsoft.com/azure/cosmos-db/)
- [Consistency levels](https://docs.microsoft.com/azure/cosmos-db/consistency-levels)
- [Partitioning strategy](https://docs.microsoft.com/azure/cosmos-db/partitioning-overview)
- [Python SDK](https://docs.microsoft.com/azure/cosmos-db/nosql/quickstart-python)

---

← [Previous: Azure SQL](./azure-sql.md) | [Home](../../README.md) | [Next: Redis Cache →](./redis.md)
