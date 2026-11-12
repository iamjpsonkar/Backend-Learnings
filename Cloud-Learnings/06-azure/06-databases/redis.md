← [Previous: Cosmos DB](./cosmos-db.md) | [Home](../../README.md) | [Next: Azure Containers →](../07-containers/README.md)

---

# Azure Cache for Redis

Azure Cache for Redis is a fully managed in-memory cache based on Redis. It is used for session storage, pub/sub, distributed locking, and reducing database load via cache-aside.

---

## SKU Tiers

| Tier | Max Memory | Persistence | Geo-replication | Clustering | Use Case |
|------|-----------|-------------|-----------------|------------|----------|
| **Basic** | 53 GB | No | No | No | Dev/test |
| **Standard** | 53 GB | No | No | No | Production (HA pair) |
| **Premium** | 530 GB | RDB + AOF | Yes | Yes | High throughput, persistence |
| **Enterprise** | 1 TB+ | RDB + AOF | Active-Active | Yes | Highest performance, RediSearch, RedisJSON |

---

## Creating a Redis Cache

```bash
RESOURCE_GROUP="rg-my-app-prod-eastus"
LOCATION="eastus"
REDIS_NAME="redis-my-app-prod-eastus"

# Create Premium tier Redis (VNet injection supported)
az redis create \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --location $LOCATION \
    --sku Premium \
    --vm-size P2 \
    --redis-version 7 \
    --enable-non-ssl-port false \
    --minimum-tls-version 1.2 \
    --subnet-id $(az network vnet subnet show \
        --resource-group $RESOURCE_GROUP \
        --vnet-name vnet-my-app-prod-eastus-001 \
        --name snet-data \
        --query id -o tsv) \
    --tags Environment=production Service=my-app

# Get connection details
az redis show \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --query '{Host:hostName,Port:sslPort,ProvisioningState:provisioningState}' \
    --output json

# Get access keys (store in Key Vault)
az redis list-keys \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --query '{Primary:primaryKey,Secondary:secondaryKey}'
```

---

## Redis Persistence (Premium+)

```bash
# Enable RDB persistence (snapshot every 15 minutes)
az redis update \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --set redisConfiguration.rdb-backup-enabled=true \
    --set redisConfiguration.rdb-backup-frequency=15 \
    --set redisConfiguration.rdb-storage-connection-string="$STORAGE_CONNECTION_STRING"

# Enable AOF persistence (append-only file — every second)
az redis update \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --set redisConfiguration.aof-backup-enabled=true \
    --set redisConfiguration.aof-storage-connection-string-0="$STORAGE_CONNECTION_STRING"
```

---

## Geo-Replication (Premium)

```bash
# Create primary and secondary cache
# Link them for geo-replication
az redis geo-replication link \
    --name $REDIS_NAME \
    --resource-group $RESOURCE_GROUP \
    --secondary-resource-group rg-my-app-dr-westus \
    --secondary-name redis-my-app-dr-westus

# View geo-replication links
az redis geo-replication linked-server list \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --output table
```

---

## Python — Cache-Aside Pattern

```python
import os
import json
import logging
import functools
from typing import Any, Callable
import redis
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

def get_redis_client() -> redis.Redis:
    """Create Redis client using Key Vault-stored access key."""
    kv_url = os.environ["KEY_VAULT_URL"]
    credential = DefaultAzureCredential()
    kv_client = SecretClient(vault_url=kv_url, credential=credential)

    redis_key = kv_client.get_secret("redis-primary-key").value
    redis_host = os.environ["REDIS_HOST"]

    logger.info("Creating Redis client", extra={"host": redis_host})
    return redis.Redis(
        host=redis_host,
        port=6380,
        password=redis_key,
        ssl=True,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Cache-aside decorator — read from cache, fall back to DB, write result back."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            cache_key = f"{key_prefix or func.__name__}:{args}:{kwargs}"
            client = get_redis_client()

            # Try cache first
            try:
                cached_val = client.get(cache_key)
                if cached_val is not None:
                    logger.debug("Cache hit", extra={"key": cache_key})
                    return json.loads(cached_val)
                logger.debug("Cache miss", extra={"key": cache_key})
            except redis.RedisError as exc:
                logger.warning("Redis read failed, falling back to DB", extra={"key": cache_key, "error": str(exc)})

            # Cache miss — call the underlying function
            result = func(*args, **kwargs)

            # Write to cache
            try:
                client.setex(cache_key, ttl_seconds, json.dumps(result))
                logger.debug("Cached result", extra={"key": cache_key, "ttl": ttl_seconds})
            except redis.RedisError as exc:
                logger.warning("Redis write failed", extra={"key": cache_key, "error": str(exc)})

            return result
        return wrapper
    return decorator


@cached(ttl_seconds=600, key_prefix="product")
def get_product(product_id: str) -> dict:
    """Fetch product from database — result cached for 10 minutes."""
    logger.info("Fetching product from DB", extra={"product_id": product_id})
    # DB query here...
    return {"id": product_id, "name": "Example Product", "price": 9.99}


def invalidate_product_cache(product_id: str) -> None:
    """Invalidate cache entry when product is updated."""
    cache_key = f"product:('{product_id}',):{{}}"
    client = get_redis_client()
    deleted = client.delete(cache_key)
    logger.info("Cache invalidated", extra={"product_id": product_id, "deleted": deleted})
```

---

## Distributed Lock (Redlock)

```python
import redis
import uuid
import time
import logging

logger = logging.getLogger(__name__)

class RedisLock:
    """Simple Redis-based distributed lock."""

    def __init__(self, client: redis.Redis, lock_name: str, ttl_seconds: int = 30):
        self.client = client
        self.lock_key = f"lock:{lock_name}"
        self.ttl = ttl_seconds
        self.token = str(uuid.uuid4())

    def acquire(self, wait_seconds: float = 5.0) -> bool:
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            acquired = self.client.set(
                self.lock_key,
                self.token,
                nx=True,           # Only set if not exists
                ex=self.ttl,       # Auto-expire
            )
            if acquired:
                logger.info("Lock acquired", extra={"key": self.lock_key, "ttl": self.ttl})
                return True
            time.sleep(0.1)
        logger.warning("Lock acquisition timed out", extra={"key": self.lock_key})
        return False

    def release(self) -> None:
        """Release only if we hold the lock (atomic compare-delete)."""
        lua_script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        result = self.client.eval(lua_script, 1, self.lock_key, self.token)
        if result:
            logger.info("Lock released", extra={"key": self.lock_key})
        else:
            logger.warning("Lock not held or already expired", extra={"key": self.lock_key})
```

---

## Useful Commands

```bash
# Rotate access key (key 1 or 2)
az redis regenerate-keys \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --key-type Primary

# Scale up SKU
az redis update \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --sku Premium \
    --vm-size P3

# View server metrics
az monitor metrics list \
    --resource $(az redis show --resource-group $RESOURCE_GROUP \
        --name $REDIS_NAME --query id -o tsv) \
    --metric "cachehits,cachemisses,usedmemory" \
    --interval PT5M \
    --aggregation Total \
    --output table
```

---

## References

- [Azure Cache for Redis documentation](https://docs.microsoft.com/azure/azure-cache-for-redis/)
- [Best practices](https://docs.microsoft.com/azure/azure-cache-for-redis/cache-best-practices)
- [Python redis-py client](https://redis-py.readthedocs.io/)

---

← [Previous: Cosmos DB](./cosmos-db.md) | [Home](../../README.md) | [Next: Azure Containers →](../07-containers/README.md)
