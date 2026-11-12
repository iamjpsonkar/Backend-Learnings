← [Previous: CI/CD](./cicd.md) | [Home](../README.md) | [Next: AWS CLI Cheatsheet →](../24-cheatsheets/README.md)

---

# Troubleshooting: Performance

Performance problems present as high latency, elevated error rates under load, or resource exhaustion. Work from the outside in: measure the symptom, identify the bottleneck, eliminate it.

---

## High API Latency

### Step 1: Identify the Bottleneck

```
High p99 latency
  │
  ├── Is it consistent or spiky?
  │     Consistent → capacity/resource issue
  │     Spiky → GC pause, cold start, noisy neighbor, lock contention
  │
  ├── Is it across all endpoints or just some?
  │     All → infrastructure (network, load balancer, DNS)
  │     Some → specific endpoint code or DB query
  │
  └── Does it correlate with traffic increase?
        Yes → autoscaling lag or capacity ceiling
        No  → resource leak, memory pressure, or external dependency
```

```bash
# CloudWatch: compare p50 vs p99 vs p999 latency
# High p999/p99 spread = outlier requests (cold starts, GC, lock waits)
# High p50 = baseline is slow (query, code efficiency)

aws cloudwatch get-metric-statistics \
    --namespace AWS/ApplicationELB \
    --metric-name TargetResponseTime \
    --dimensions Name=LoadBalancer,Value=$ALB_DIMENSION \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics p50 p90 p99 \
    --query 'sort_by(Datapoints, &Timestamp)[-5:].{Time:Timestamp,p50:ExtendedStatistics.p50,p99:ExtendedStatistics.p99}'
```

### Step 2: Trace the Request

```python
# Enable distributed tracing (OpenTelemetry) to see time per span
# See 15-observability/tracing.md for setup

# Quick manual timing approach in FastAPI
import time
import logging

logger = logging.getLogger(__name__)

@app.middleware("http")
async def timing_middleware(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000

    logger.info("Request timing", extra={
        "method": request.method,
        "path": request.url.path,
        "duration_ms": round(duration_ms, 2),
        "status": response.status_code,
    })
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
    return response
```

---

## Lambda Cold Starts

```bash
# Check cold start rate (invocations vs init duration)
aws logs start-query \
    --log-group-name "/aws/lambda/order-api" \
    --start-time $(($(date +%s) - 3600)) \
    --end-time $(date +%s) \
    --query-string '
        filter @type = "REPORT"
        | stats
            count(*) as total_invocations,
            count(initDuration) as cold_starts,
            avg(initDuration) as avg_init_ms,
            max(initDuration) as max_init_ms,
            avg(duration) as avg_duration_ms,
            max(maxMemoryUsed) as max_memory_mb
        by bin(5min)
    '

# Fix 1: Provisioned Concurrency (eliminates cold starts for critical functions)
aws lambda put-provisioned-concurrency-config \
    --function-name order-api \
    --qualifier prod \
    --provisioned-concurrent-executions 5

# Fix 2: Reduce package size (faster initialization)
# Check current package size
aws lambda get-function-configuration \
    --function-name order-api \
    --query 'CodeSize'

# Use Lambda Layers for heavy dependencies (boto3, etc.)
# Use --zip-file only with production dependencies

# Fix 3: Reduce import time (Python-specific)
# Lazy imports — only import at function handler time, not module level
# Bad:  import pandas  (at module level)
# Good: def handler(): import pandas (only when needed, but this defeats caching)
# Better: use Lambda Layers + keep handler lightweight

# Fix 4: Lambda SnapStart (Java 21 only — ms-level cold starts)
aws lambda update-function-configuration \
    --function-name java-order-api \
    --snap-start ApplyOn=PublishedVersions
```

---

## ECS / EC2 Resource Pressure

```bash
# Check ECS service CPU and memory utilization
aws cloudwatch get-metric-statistics \
    --namespace AWS/ECS \
    --metric-name CPUUtilization \
    --dimensions Name=ClusterName,Value=prod-cluster Name=ServiceName,Value=order-api \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Average Maximum

# Check if tasks are being throttled (CPU limit hit)
# CPU throttling is invisible in CloudWatch but visible in container metrics
# Enable Container Insights:
aws ecs update-cluster-settings \
    --cluster prod-cluster \
    --settings name=containerInsights,value=enabled

# With Container Insights, get per-task metrics:
aws cloudwatch get-metric-statistics \
    --namespace ECS/ContainerInsights \
    --metric-name CpuUtilized \
    --dimensions Name=ClusterName,Value=prod-cluster Name=ServiceName,Value=order-api \
    --start-time $(date -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Average

# Quick fix: increase task CPU/memory
aws ecs update-service \
    --cluster prod-cluster \
    --service order-api \
    --task-definition order-api-large  # pre-registered with more CPU/memory
```

---

## Autoscaling Lag

```bash
# Problem: traffic spike hits before scaling completes (typically 3-5 min delay)
# Solution: scale proactively, set lower thresholds, or use scheduled scaling

# Check scaling activities
aws autoscaling describe-scaling-activities \
    --auto-scaling-group-name prod-asg \
    --max-records 10 \
    --query 'Activities[*].{Status:StatusCode,Cause:Cause,Start:StartTime,End:EndTime}'

# Scale-out is too slow? Reduce:
# 1. CloudWatch alarm period (default: 5 min × 2 data points = 10 min)
# 2. cooldown period (default: 300s)
# 3. instance warmup period

aws autoscaling update-auto-scaling-group \
    --auto-scaling-group-name prod-asg \
    --default-cooldown 60 \
    --default-instance-warmup 60

# Add predictive scaling (scales 1 hour ahead based on historical patterns)
aws autoscaling put-scaling-policy \
    --auto-scaling-group-name prod-asg \
    --policy-name predictive-scaling \
    --policy-type PredictiveScaling \
    --predictive-scaling-configuration '{
        "MetricSpecifications": [{
            "TargetValue": 70.0,
            "PredefinedMetricPairSpecification": {
                "PredefinedMetricType": "ASGCPUUtilization"
            }
        }],
        "Mode": "ForecastAndScale",
        "SchedulingBufferTime": 300
    }'
```

---

## Database Connection Pool Exhaustion Under Load

```python
# Symptom: p99 latency spikes exactly at traffic ramp
# Cause: connection pool saturated, requests queue waiting for a connection

import logging
from sqlalchemy import event
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)


def instrument_pool(engine):
    """Log connection pool saturation events."""

    @event.listens_for(Pool, "checkout")
    def on_checkout(dbapi_conn, conn_record, conn_proxy):
        logger.debug("Connection checked out from pool")

    @event.listens_for(Pool, "checkin")
    def on_checkin(dbapi_conn, conn_record):
        logger.debug("Connection returned to pool")

    @event.listens_for(Pool, "connect")
    def on_connect(dbapi_conn, conn_record):
        logger.info("New DB connection created")

    @event.listens_for(Pool, "timeout")
    def on_timeout(dbapi_conn):
        logger.error(
            "Connection pool timeout — pool exhausted. "
            "Consider increasing pool_size or using PgBouncer.",
        )


# Tuning: pool_size should not exceed (max_connections / num_pods)
# Example: RDS max_connections=200, 10 pods → pool_size=15 per pod (plus overhead)
engine = create_engine(
    DATABASE_URL,
    pool_size=15,
    max_overflow=5,
    pool_timeout=10,     # raise after 10s wait
    pool_pre_ping=True,  # verify connection before checkout
)
instrument_pool(engine)
```

---

## Memory Leaks

```bash
# Detect memory growth over time
# CloudWatch: check ECS container memory utilization trend

aws cloudwatch get-metric-statistics \
    --namespace ECS/ContainerInsights \
    --metric-name MemoryUtilized \
    --dimensions Name=ClusterName,Value=prod-cluster Name=ServiceName,Value=order-api \
    --start-time $(date -v-12H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -d '12 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
    --period 300 \
    --statistics Average \
    --query 'sort_by(Datapoints, &Timestamp)[*].{Time:Timestamp,MemMB:Average}'

# Python: profile memory allocations
# Add to local debugging (not production):
# pip install memory-profiler
from memory_profiler import profile

@profile
def my_suspect_function():
    ...
```

```python
# Common memory leak patterns in Python web apps

# Pattern 1: Global list/dict that grows unbounded
_cache = {}  # Never cleared → grows forever
# Fix: use functools.lru_cache(maxsize=1000) or a proper TTL cache

# Pattern 2: Unclosed file handles or DB connections
# Fix: always use context managers
with open("file.txt") as f:
    data = f.read()

async with db_pool.acquire() as conn:
    result = await conn.fetchval("SELECT 1")

# Pattern 3: Circular references preventing garbage collection
# Fix: use weakref for parent→child references where child holds parent
import weakref

class Parent:
    def __init__(self):
        self.children = []

class Child:
    def __init__(self, parent: "Parent"):
        self.parent = weakref.ref(parent)  # weak reference — won't prevent GC
```

---

## References

- [AWS Lambda performance best practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [ECS Container Insights](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cloudwatch-container-insights.html)
- [PostgreSQL EXPLAIN ANALYZE](https://www.postgresql.org/docs/current/using-explain.html)

---

← [Previous: CI/CD](./cicd.md) | [Home](../README.md) | [Next: AWS CLI Cheatsheet →](../24-cheatsheets/README.md)
