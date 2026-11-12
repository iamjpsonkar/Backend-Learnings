← [Previous: Firestore](./firestore.md) | [Home](../../README.md) | [Next: BigQuery →](./bigquery.md)

---

# Memorystore for Redis

Memorystore is a fully managed Redis and Memcached service. It handles patching, backups, failover, and scaling with no infrastructure management.

---

## Memorystore Redis Tiers

| Tier | HA | Persistence | Scaling | Use Case |
|------|----|------------|---------|----------|
| **Basic** | No | No | Manual | Dev/test, non-critical cache |
| **Standard** | Yes (auto-failover) | RDB | Manual | Production |
| **Cluster** | Yes | RDB + AOF | Horizontal (shards) | High-throughput, large datasets |

---

## Creating a Redis Instance

```bash
PROJECT="my-app-prod-123456"
REGION="us-central1"
ZONE="us-central1-a"

# Create a Standard tier instance (HA) with private IP
gcloud redis instances create redis-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --zone=$ZONE \
    --alternative-zone=us-central1-b \
    --tier=STANDARD \
    --size=4 \
    --redis-version=redis_7_0 \
    --network=projects/$PROJECT/global/networks/vpc-my-app-prod \
    --labels=environment=production,service=my-app \
    --redis-config maxmemory-policy=allkeys-lru,notify-keyspace-events=Ex

# Get connection details
gcloud redis instances describe redis-my-app-prod \
    --project=$PROJECT \
    --region=$REGION \
    --format="table(host,port,state,memorySizeGb,redisVersion)"
# host: 10.0.x.x (private VPC IP), port: 6379 (or 6380 for TLS)

# Enable in-transit encryption (TLS) — only at creation
gcloud redis instances create redis-my-app-prod-tls \
    --project=$PROJECT \
    --region=$REGION \
    --tier=STANDARD \
    --size=4 \
    --redis-version=redis_7_0 \
    --transit-encryption-mode=SERVER_AUTHENTICATION \
    --network=projects/$PROJECT/global/networks/vpc-my-app-prod
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

logger = logging.getLogger(__name__)

REDIS_HOST = os.environ["REDIS_HOST"]  # Private IP from Memorystore
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        logger.info("Redis client created", extra={"host": REDIS_HOST, "port": REDIS_PORT})
    return _redis_client


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Cache-aside decorator."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            key = f"{key_prefix or func.__name__}:{args}:{sorted(kwargs.items())}"
            client = get_redis()

            try:
                cached_value = client.get(key)
                if cached_value is not None:
                    logger.debug("Cache hit", extra={"key": key})
                    return json.loads(cached_value)
                logger.debug("Cache miss", extra={"key": key})
            except redis.RedisError as exc:
                logger.warning("Redis read error, bypassing cache", extra={"key": key, "error": str(exc)})

            result = func(*args, **kwargs)

            try:
                client.setex(key, ttl_seconds, json.dumps(result))
            except redis.RedisError as exc:
                logger.warning("Redis write error", extra={"key": key, "error": str(exc)})

            return result
        return wrapper
    return decorator


@cached(ttl_seconds=600, key_prefix="product")
def get_product(product_id: str) -> dict:
    logger.info("DB fetch for product", extra={"product_id": product_id})
    return {"id": product_id, "name": "Example", "price": 9.99}


def invalidate_product(product_id: str) -> None:
    client = get_redis()
    pattern = f"product:(('{product_id}',),*"
    keys = list(client.scan_iter(pattern))
    if keys:
        deleted = client.delete(*keys)
        logger.info("Cache invalidated", extra={"product_id": product_id, "keys_deleted": deleted})


# Session storage helper
def set_session(session_id: str, data: dict, ttl_seconds: int = 3600) -> None:
    client = get_redis()
    client.setex(f"session:{session_id}", ttl_seconds, json.dumps(data))
    logger.debug("Session stored", extra={"session_id": session_id, "ttl": ttl_seconds})


def get_session(session_id: str) -> dict | None:
    client = get_redis()
    raw = client.get(f"session:{session_id}")
    if raw is None:
        return None
    client.expire(f"session:{session_id}", 3600)  # Sliding window TTL
    return json.loads(raw)
```

---

## Import and Export

```bash
# Export Redis data to Cloud Storage (RDB snapshot)
gcloud redis instances export gs://my-app-prod-backups/redis/redis-$(date +%Y%m%d).rdb \
    --instance=redis-my-app-prod \
    --region=$REGION \
    --project=$PROJECT

# Import from RDB file (restores data, overwrites existing keys)
gcloud redis instances import gs://my-app-prod-backups/redis/redis-20240615.rdb \
    --instance=redis-my-app-prod \
    --region=$REGION \
    --project=$PROJECT
```

---

## Scaling

```bash
# Scale up memory (downtime-free for Standard tier)
gcloud redis instances update redis-my-app-prod \
    --size=8 \
    --region=$REGION \
    --project=$PROJECT

# Check maintenance schedule
gcloud redis instances describe redis-my-app-prod \
    --region=$REGION \
    --project=$PROJECT \
    --format="json(maintenanceSchedule)"
```

---

## References

- [Memorystore for Redis documentation](https://cloud.google.com/memorystore/docs/redis)
- [Redis tiers](https://cloud.google.com/memorystore/docs/redis/redis-tiers)
- [Python redis-py client](https://redis-py.readthedocs.io/)

---

← [Previous: Firestore](./firestore.md) | [Home](../../README.md) | [Next: BigQuery →](./bigquery.md)
