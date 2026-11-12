← [Previous: DynamoDB](./dynamodb.md) | [Home](../../README.md) | [Next: Redshift →](./redshift.md)

---

# Amazon ElastiCache

ElastiCache is a fully managed in-memory caching service supporting Redis and Memcached. It dramatically reduces database load, improves application response times, and enables use cases like session storage, leaderboards, pub/sub messaging, and rate limiting.

---

## Redis vs Memcached

| | ElastiCache for Redis | ElastiCache for Memcached |
|--|----------------------|--------------------------|
| Data structures | Strings, hashes, lists, sets, sorted sets, streams, bitmaps | String only |
| Persistence | RDB snapshots + AOF | None |
| Replication | Yes (primary + replicas) | No |
| Cluster mode | Disabled (single shard) or Enabled (multiple shards) | Multi-threaded, simple |
| Multi-AZ | Yes | Yes |
| Pub/Sub | Yes | No |
| Lua scripting | Yes | No |
| Sorted sets / leaderboards | Yes | No |
| Use case | Sessions, caching, pub/sub, leaderboards, rate limiting, queues | Pure caching only |
| **Choose when** | You need persistence, replication, or rich data types | Simplest possible cache; multi-threaded performance |

**In practice, choose Redis for almost all new workloads.**

---

## ElastiCache for Redis — Creating a Cluster

```bash
VPC_ID="vpc-0abc1234"
SG_CACHE="sg-0cache1234"
SUBNET_GROUP="my-cache-subnet-group"

# Create subnet group (spans multiple AZs)
aws elasticache create-cache-subnet-group \
    --cache-subnet-group-name my-cache-subnet-group \
    --cache-subnet-group-description "Private subnets for ElastiCache" \
    --subnet-ids subnet-private-1a subnet-private-1b

# Security group for cache (app SG → port 6379)
SG_CACHE=$(aws ec2 create-security-group \
    --group-name elasticache-sg \
    --description "Allow Redis from app instances" \
    --vpc-id $VPC_ID \
    --query 'GroupId' --output text)

SG_APP="sg-0app1234"
aws ec2 authorize-security-group-ingress \
    --group-id $SG_CACHE \
    --protocol tcp \
    --port 6379 \
    --source-group $SG_APP

# Create Redis replication group (cluster mode DISABLED — single shard with replicas)
REDIS_ID=$(aws elasticache create-replication-group \
    --replication-group-id my-redis \
    --replication-group-description "Application cache" \
    --cache-node-type cache.r7g.large \
    --engine redis \
    --engine-version 7.2 \
    --cache-parameter-group-name default.redis7 \
    --cache-subnet-group-name $SUBNET_GROUP \
    --security-group-ids $SG_CACHE \
    --num-cache-clusters 3 \
    --automatic-failover-enabled \
    --multi-az-enabled \
    --at-rest-encryption-enabled \
    --transit-encryption-enabled \
    --auth-token "$(openssl rand -base64 32)" \
    --snapshot-retention-limit 7 \
    --snapshot-window "02:00-03:00" \
    --preferred-maintenance-window "sun:04:00-sun:05:00" \
    --tags Key=Name,Value=my-redis Key=Environment,Value=production \
    --query 'ReplicationGroup.ReplicationGroupId' --output text)

echo "Redis cluster: $REDIS_ID"

# Wait until available
aws elasticache wait replication-group-available --replication-group-id $REDIS_ID

# Get the primary and reader endpoints
aws elasticache describe-replication-groups \
    --replication-group-id $REDIS_ID \
    --query 'ReplicationGroups[0].{
        Primary:NodeGroups[0].PrimaryEndpoint.Address,
        Reader:NodeGroups[0].ReaderEndpoint.Address,
        Port:NodeGroups[0].PrimaryEndpoint.Port,
        Status:Status
    }'
```

### Cluster Mode Enabled (Multiple Shards)

```bash
# Cluster mode enabled — required for >6.5 GB dataset or horizontal write scaling
aws elasticache create-replication-group \
    --replication-group-id my-redis-cluster \
    --replication-group-description "Sharded Redis cluster" \
    --cache-node-type cache.r7g.large \
    --engine redis \
    --engine-version 7.2 \
    --cache-subnet-group-name $SUBNET_GROUP \
    --security-group-ids $SG_CACHE \
    --num-node-groups 3 \
    --replicas-per-node-group 2 \
    --automatic-failover-enabled \
    --multi-az-enabled \
    --at-rest-encryption-enabled \
    --transit-encryption-enabled \
    --auth-token "$(openssl rand -base64 32)" \
    --cluster-mode enabled
```

---

## Cache-Aside Pattern (Python)

The cache-aside pattern is the most common caching strategy: read from cache; on miss, load from database and populate cache.

```python
import json
import logging
import redis
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Initialize clients (do this once at module level, not inside functions)
redis_client = redis.Redis(
    host="my-redis.abc.cache.amazonaws.com",
    port=6379,
    password="your-auth-token",
    ssl=True,
    decode_responses=True,
)
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("MyAppTable")


def get_user_profile(user_id: str, ttl: int = 300) -> dict | None:
    """
    Cache-aside: read from Redis, fall back to DynamoDB on miss.
    """
    cache_key = f"user:profile:{user_id}"
    logger.debug("Cache lookup: key=%s", cache_key)

    # 1. Try cache first
    try:
        cached = redis_client.get(cache_key)
        if cached:
            logger.debug("Cache hit: key=%s", cache_key)
            return json.loads(cached)
        logger.debug("Cache miss: key=%s", cache_key)
    except redis.RedisError as e:
        # Cache failure should not break the application — fall through
        logger.warning("Cache read failed: key=%s error=%s", cache_key, str(e))

    # 2. Load from database
    try:
        response = table.get_item(
            Key={"PK": f"USER#{user_id}", "SK": "PROFILE"},
            ConsistentRead=True,
        )
        item = response.get("Item")
    except ClientError as e:
        logger.error("DynamoDB read failed: user_id=%s error=%s", user_id, e.response["Error"]["Code"])
        raise

    if not item:
        logger.info("User not found: user_id=%s", user_id)
        return None

    # 3. Populate cache (fire-and-forget — don't fail if cache write fails)
    try:
        redis_client.setex(cache_key, ttl, json.dumps(item))
        logger.debug("Cache populated: key=%s ttl=%d", cache_key, ttl)
    except redis.RedisError as e:
        logger.warning("Cache write failed: key=%s error=%s", cache_key, str(e))

    return item


def invalidate_user_cache(user_id: str) -> None:
    """Delete cached profile after update."""
    cache_key = f"user:profile:{user_id}"
    logger.info("Invalidating cache: key=%s", cache_key)
    try:
        deleted = redis_client.delete(cache_key)
        logger.info("Cache invalidated: key=%s deleted=%d", cache_key, deleted)
    except redis.RedisError as e:
        logger.error("Cache invalidation failed: key=%s error=%s", cache_key, str(e))
```

---

## Common Redis Use Cases

### Session Storage

```python
import secrets

def create_session(user_id: str, ttl: int = 86400) -> str:
    """Create a server-side session token stored in Redis."""
    session_token = secrets.token_urlsafe(32)
    session_key = f"session:{session_token}"
    session_data = json.dumps({"user_id": user_id, "created_at": str(int(__import__("time").time()))})

    logger.info("Creating session: user_id=%s ttl=%d", user_id, ttl)
    redis_client.setex(session_key, ttl, session_data)
    return session_token


def get_session(session_token: str) -> dict | None:
    """Retrieve and extend a session."""
    session_key = f"session:{session_token}"
    data = redis_client.get(session_key)
    if data:
        redis_client.expire(session_key, 86400)   # extend TTL on activity
        return json.loads(data)
    return None
```

### Rate Limiting (Token Bucket via Redis)

```python
def is_rate_limited(user_id: str, limit: int = 100, window_seconds: int = 60) -> bool:
    """
    Fixed window rate limiter using Redis INCR + EXPIRE.
    Returns True if the request should be blocked.
    """
    key = f"ratelimit:{user_id}:{int(__import__('time').time()) // window_seconds}"
    logger.debug("Rate limit check: user_id=%s key=%s limit=%d", user_id, key, limit)

    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = pipe.execute()

    current_count = results[0]
    logger.info("Rate limit count: user_id=%s count=%d limit=%d", user_id, current_count, limit)
    return current_count > limit
```

### Sorted Set Leaderboard

```bash
# CLI demonstration of sorted set operations
redis-cli ZADD leaderboard 1500 "player:alice"
redis-cli ZADD leaderboard 2300 "player:bob"
redis-cli ZADD leaderboard 1800 "player:carol"

# Get top 10 (highest scores first)
redis-cli ZREVRANGE leaderboard 0 9 WITHSCORES

# Get rank of a player (0-indexed)
redis-cli ZREVRANK leaderboard "player:bob"
```

---

## Scaling

```bash
REDIS_ID="my-redis"

# Scale vertically (change node type) — causes brief failover
aws elasticache modify-replication-group \
    --replication-group-id $REDIS_ID \
    --cache-node-type cache.r7g.xlarge \
    --apply-immediately

# Add a read replica
aws elasticache increase-replica-count \
    --replication-group-id $REDIS_ID \
    --new-replica-count 4 \
    --apply-immediately

# Remove a replica
aws elasticache decrease-replica-count \
    --replication-group-id $REDIS_ID \
    --new-replica-count 2 \
    --apply-immediately
```

---

## Monitoring

```bash
REDIS_ID="my-redis"

# Key CloudWatch metrics for Redis:
# CacheHits / CacheMisses          — hit rate (target >90%)
# CurrConnections                  — active connections (alert if nearing limit)
# Evictions                        — non-expired keys removed (alert if > 0)
# EngineCPUUtilization             — Redis process CPU (alert if >80%)
# DatabaseMemoryUsagePercentage    — alert at >80%
# ReplicationLag                   — replica sync lag in seconds

aws cloudwatch get-metric-statistics \
    --namespace AWS/ElastiCache \
    --metric-name CacheHitRate \
    --dimensions Name=ReplicationGroupId,Value=$REDIS_ID \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Average \
    --output table

# Alert on evictions (evictions mean the cache is too small)
aws cloudwatch put-metric-alarm \
    --alarm-name redis-evictions \
    --namespace AWS/ElastiCache \
    --metric-name Evictions \
    --dimensions Name=ReplicationGroupId,Value=$REDIS_ID \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:ops-alerts
```

---

## References

- [ElastiCache for Redis documentation](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/)
- [Redis commands reference](https://redis.io/commands/)
- [Caching strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Strategies.html)
- [ElastiCache pricing](https://aws.amazon.com/elasticache/pricing/)
---

← [Previous: DynamoDB](./dynamodb.md) | [Home](../../README.md) | [Next: Redshift →](./redshift.md)
