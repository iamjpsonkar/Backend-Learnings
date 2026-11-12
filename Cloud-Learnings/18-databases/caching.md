← [Previous: NoSQL](./nosql.md) | [Home](../README.md) | [Next: Migrations →](./migrations.md)

---

# Caching

Caching reduces database load, lowers latency, and improves throughput. Use it strategically — a cache that is hard to invalidate correctly is worse than no cache.

---

## Caching Strategies

| Strategy | How it works | Best for |
|----------|-------------|---------|
| **Cache-aside** (lazy) | App checks cache first; miss → fetch DB → populate cache | Read-heavy, tolerable stale data |
| **Write-through** | Write to cache and DB simultaneously | Write-heavy with strong consistency |
| **Write-behind** (write-back) | Write to cache first; async flush to DB | High write throughput; risk of data loss |
| **Read-through** | Cache layer fetches from DB on miss | Transparent caching layer |
| **Refresh-ahead** | Pre-populate cache before TTL expires | Latency-sensitive, predictable access |

---

## Redis (AWS ElastiCache / self-managed)

```python
import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import redis.asyncio as aioredis
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "300"))  # 5 min default

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Singleton Redis client with connection pooling."""
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        logger.info("Redis client initialized", extra={"url": REDIS_URL.split("@")[-1]})
    return _redis_client


# ─── Cache-aside pattern ─────────────────────────────────────────────────────
async def get_cached(key: str, ttl: int = DEFAULT_TTL) -> Optional[Any]:
    """Get a value from cache. Returns None on miss or error."""
    try:
        r = await get_redis()
        value = await r.get(key)
        if value is not None:
            logger.debug("Cache hit", extra={"key": key})
            return json.loads(value)
        logger.debug("Cache miss", extra={"key": key})
        return None
    except Exception as exc:
        logger.warning("Cache get failed — treating as miss",
                       extra={"key": key, "error": str(exc)})
        return None


async def set_cached(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    """Store a value in cache with TTL."""
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value, default=str))
        logger.debug("Cache set", extra={"key": key, "ttl": ttl})
    except Exception as exc:
        logger.warning("Cache set failed", extra={"key": key, "error": str(exc)})


async def invalidate_cache(*keys: str) -> None:
    """Delete one or more cache keys."""
    if not keys:
        return
    try:
        r = await get_redis()
        deleted = await r.delete(*keys)
        logger.info("Cache invalidated", extra={"keys": list(keys), "deleted": deleted})
    except Exception as exc:
        logger.warning("Cache invalidation failed", extra={"keys": keys, "error": str(exc)})


# ─── Cache decorator ─────────────────────────────────────────────────────────
F = TypeVar("F", bound=Callable)


def cached(key_prefix: str, ttl: int = DEFAULT_TTL) -> Callable[[F], F]:
    """
    Decorator: cache async function result keyed by prefix + args.
    Usage: @cached("product", ttl=3600)
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"
            if kwargs:
                cache_key += ":" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

            cached_value = await get_cached(cache_key, ttl)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            if result is not None:
                await set_cached(cache_key, result, ttl)
            return result
        return wrapper  # type: ignore[return-value]
    return decorator


# ─── Usage ───────────────────────────────────────────────────────────────────
@cached("product", ttl=3600)
async def get_product(product_id: str) -> Optional[dict]:
    logger.info("Cache miss — fetching from DB", extra={"product_id": product_id})
    return await db.fetch_product(product_id)


async def update_product(product_id: str, data: dict) -> dict:
    result = await db.update_product(product_id, data)
    # Invalidate on write
    await invalidate_cache(f"product:{product_id}")
    return result
```

---

## Redis Data Structures

```python
import redis
r = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)

# ─── String (simple cache) ────────────────────────────────────────────────────
r.setex("user:123:session", 3600, json.dumps(session_data))
r.get("user:123:session")

# ─── Hash (object with multiple fields) ──────────────────────────────────────
r.hset("user:123", mapping={"name": "Alice", "email": "alice@example.com", "role": "admin"})
r.hget("user:123", "email")
r.hmget("user:123", "name", "role")
r.hgetall("user:123")

# ─── Counter / Rate limiting ──────────────────────────────────────────────────
# Rate limit: max 100 requests per minute per user
import time

def check_rate_limit(user_id: str, max_requests: int = 100, window: int = 60) -> bool:
    key = f"ratelimit:{user_id}:{int(time.time()) // window}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, window * 2)
    count, _ = pipe.execute()
    allowed = count <= max_requests
    logger.debug("Rate limit check", extra={"user_id": user_id, "count": count, "allowed": allowed})
    return allowed

# ─── Sorted Set (leaderboard, priority queue) ─────────────────────────────────
r.zadd("leaderboard:weekly", {"user:alice": 1500, "user:bob": 1200, "user:carol": 1800})
r.zrevrangebyscore("leaderboard:weekly", "+inf", "-inf", withscores=True, start=0, num=10)
r.zincrby("leaderboard:weekly", 50, "user:alice")

# ─── Set (tags, memberships) ──────────────────────────────────────────────────
r.sadd("product:123:tags", "electronics", "sale", "featured")
r.smembers("product:123:tags")
r.sismember("product:123:tags", "sale")  # O(1) membership check

# ─── List (queue, recent activity) ───────────────────────────────────────────
r.lpush("notifications:user:123", json.dumps({"type": "order_shipped", "order_id": "ord_abc"}))
r.lrange("notifications:user:123", 0, 9)  # Most recent 10
r.ltrim("notifications:user:123", 0, 99)   # Keep only last 100

# ─── Pub/Sub ──────────────────────────────────────────────────────────────────
# Publisher
r.publish("order-events", json.dumps({"event": "order_created", "order_id": "ord_abc"}))

# Subscriber (blocking)
pubsub = r.pubsub()
pubsub.subscribe("order-events")
for message in pubsub.listen():
    if message["type"] == "message":
        data = json.loads(message["data"])
        logger.info("Received event", extra={"event": data})
```

---

## Cache TTL Strategy

```python
# TTL guidelines by data type
CACHE_TTLS = {
    # Almost static
    "product_catalog":     86400,   # 24h — products don't change frequently
    "configuration":       3600,    # 1h
    "country_list":        86400,   # 24h

    # Semi-dynamic
    "user_profile":        300,     # 5min — balance freshness vs DB load
    "search_results":      60,      # 1min — acceptable stale
    "product_inventory":   30,      # 30s — inventory needs to be fairly fresh
    "exchange_rates":      300,     # 5min

    # Ephemeral
    "session":             1800,    # 30min inactivity timeout
    "rate_limit_counter":  60,      # 1min window
    "otp_code":            300,     # 5min — one-time password
    "csrf_token":          3600,    # 1h

    # Never cache (always fresh)
    # - Account balances during checkout
    # - Payment status
    # - Security-sensitive settings
}
```

---

## AWS ElastiCache

```bash
# Create Redis cluster (cluster mode disabled — simpler, good for most use cases)
aws elasticache create-replication-group \
    --replication-group-id my-app-redis \
    --replication-group-description "My App Redis" \
    --engine redis \
    --engine-version 7.0 \
    --cache-node-type cache.r7g.large \
    --num-cache-clusters 2 \       # Primary + 1 replica
    --automatic-failover-enabled \
    --at-rest-encryption-enabled \
    --transit-encryption-enabled \
    --auth-token "$(openssl rand -base64 32)" \
    --cache-subnet-group-name my-redis-subnet-group \
    --security-group-ids sg-redis-prod \
    --snapshot-retention-limit 7 \
    --preferred-snapshot-window "05:00-06:00" \
    --tags Key=service,Value=cache Key=environment,Value=production

# Get the endpoint
aws elasticache describe-replication-groups \
    --replication-group-id my-app-redis \
    --query 'ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint'
```

---

## References

- [Redis documentation](https://redis.io/docs/)
- [AWS ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/)
- [Caching strategies](https://aws.amazon.com/caching/best-practices/)
- [Redis data types](https://redis.io/docs/data-types/)

---

← [Previous: NoSQL](./nosql.md) | [Home](../README.md) | [Next: Migrations →](./migrations.md)
