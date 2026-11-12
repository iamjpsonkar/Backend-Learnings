← [Previous: AWS Fundamentals](./aws-fundamentals.md) | [Home](../README.md) | [Next: DevOps & SRE →](./devops-sre.md)

---

# Interview Prep: System Design

System design interviews test your ability to translate ambiguous requirements into a working architecture. The goal is not to get the "right answer" — it's to show structured thinking, awareness of trade-offs, and practical experience.

---

## Framework for System Design Interviews

```
1. Clarify requirements (5 min)
   ├── Scale: users, requests/second, data volume
   ├── Consistency requirements: strong vs eventual
   ├── Latency: p99 target in ms
   ├── Read/write ratio
   └── Global vs single-region

2. Back-of-envelope estimation (3 min)
   ├── Storage: e.g., 100M users × 1 KB = 100 GB
   ├── Throughput: 10M req/day = 116 req/s, peak = 5× = 580 req/s
   └── Bandwidth: 580 req/s × 10 KB = 5.8 MB/s

3. High-level architecture (10 min)
   ├── Draw the main components and data flows
   ├── Choose: monolith vs microservices, SQL vs NoSQL, sync vs async
   └── Don't over-engineer — solve the stated requirements

4. Deep dive one component (15 min)
   ├── Interviewer usually directs this
   ├── Database schema, API design, caching strategy, or scaling mechanism
   └── Justify choices with trade-offs

5. Address bottlenecks and edge cases (5 min)
   ├── Single points of failure
   ├── Hot spots (popular data, viral content)
   └── What happens when X fails?
```

---

## Common Design Problems

### Design a URL Shortener

**Requirements (clarified):** 100M URLs created/day, 10B redirects/day, links expire after 1 year, globally available.

**Estimation:**
- 100M writes/day = 1,160 writes/s
- 10B reads/day = 115,000 reads/s → read-heavy (100:1)
- Storage: 100M × 365 days × 500 bytes = ~18 TB/year

**Architecture:**
```
Client → CDN (cache popular redirects)
  → API Gateway → Redirect Service → Redis (hot URLs)
                                   → DynamoDB (all URLs, TTL=1year)

URL creation:
  Client → API → ID Generator (base62 encode 7 chars) → DynamoDB (PK=short_code)

Redirect:
  1. Check Redis (< 1ms, cache hit)
  2. Miss → DynamoDB (< 5ms) → cache in Redis
  3. 301 redirect (browser caches) or 302 (track each click)
```

**Key decisions and trade-offs:**
- DynamoDB: schemaless, auto-scaling, TTL built-in — ideal for key-value lookups
- Base62 (a-z, A-Z, 0-9): 7 chars = 62^7 = 3.5 trillion unique codes — sufficient for decades
- 301 vs 302: 301 (permanent) — browser caches, fewer server hits; 302 (temporary) — every click hits server, allows analytics

---

### Design a Notification System

**Requirements:** send email, SMS, push notifications; 10M notifications/day; guarantee delivery; support retries.

**Architecture:**
```
Producer services (orders, payments, auth)
  │ publish events
  ▼
SNS Topics (per event type: order-placed, payment-failed, password-reset)
  │ fan-out
  ├── SQS Queue (email)   → Lambda → SES (email)
  ├── SQS Queue (SMS)     → Lambda → Twilio/SNS SMS
  └── SQS Queue (push)    → Lambda → Firebase FCM / APNs

DLQ (Dead Letter Queue) for each SQS queue
  → CloudWatch alarm → alert on-call when DLQ grows
  → Manual replay after fixing the bug
```

**Key decisions:**
- SNS + SQS fan-out: decoupled, each channel fails independently
- SQS visibility timeout > Lambda timeout: prevents duplicate processing if Lambda times out
- Idempotency: each notification has a `notification_id`; recipient stores processed IDs to deduplicate retries
- DLQ: failed messages preserved for analysis and replay — never silently dropped

---

### Design a Distributed Rate Limiter

**Requirements:** 1,000 req/min per user; work across multiple API servers; < 5ms overhead.

**Fixed window algorithm (simple):**
```python
import redis
import time

r = redis.Redis()

def is_allowed(user_id: str, limit: int = 1000) -> bool:
    key = f"rate:{user_id}:{int(time.time() // 60)}"  # 1-min window
    count = r.incr(key)
    if count == 1:
        r.expire(key, 120)  # 2× window as safety
    return count <= limit
```

Problem: burst at window boundary (1000 req at 0:59, 1000 req at 1:00 = 2000 req in 2 sec).

**Sliding window (token bucket via Redis):**
```python
# Use Redis sorted set with timestamps as scores
def is_allowed_sliding(user_id: str, limit: int = 1000, window_sec: int = 60) -> bool:
    now = time.time()
    window_start = now - window_sec
    key = f"rate:{user_id}"

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)  # remove old entries
    pipe.zadd(key, {str(now): now})              # add current request
    pipe.zcard(key)                               # count in window
    pipe.expire(key, window_sec + 10)
    _, _, count, _ = pipe.execute()

    return count <= limit
```

---

### Design a File Storage Service (S3-like)

**Requirements:** Upload and download files up to 5 GB; billions of files; 99.99% durability; global access.

**Architecture:**
```
Upload:
  Client → API Server → generate presigned URL → S3 (direct upload)
  S3 → EventBridge → Lambda → update metadata DB (DynamoDB)

Download:
  Client → CloudFront (CDN) → S3 origin
  Popular files served from CDN edge (<50ms)

Large files (>5MB):
  Client → API → initiate multipart upload → upload parts directly to S3
          → complete multipart upload → S3 assembles
```

**Storage tiers:**
- Hot (accessed last 30d): S3 Standard
- Warm (last 6 months): S3 Standard-IA (same AZ durability, lower cost, retrieval fee)
- Cold (older): S3 Glacier Instant Retrieval (ms access, much cheaper)

---

## Trade-offs to Know Cold

### SQL vs NoSQL

| Choose SQL (RDS, PostgreSQL) | Choose NoSQL (DynamoDB) |
|------------------------------|------------------------|
| Complex joins and relationships | Simple key-value or document access |
| ACID transactions across tables | Predictable single-digit ms at any scale |
| Schema migrations needed | Flexible / evolving schema |
| Ad-hoc queries (reporting, analytics) | Access patterns known upfront |
| Moderate scale (< 100M rows or < 50k req/s) | Internet-scale, unpredictable traffic |

### Cache placement

| Type | Example | When |
|------|---------|------|
| **Cache-aside** (lazy loading) | Redis + application reads cache first | Read-heavy, tolerates cache miss latency |
| **Write-through** | Write to cache + DB simultaneously | Read-heavy, need cache consistency |
| **Write-behind** | Write to cache, async flush to DB | Write-heavy, can tolerate async persistence |
| **TTL** | Cache expires after N seconds | Acceptable staleness, simple invalidation |

### Consistency vs Availability (CAP)

In a network partition:
- **CP systems** (choose consistency): reject writes when can't confirm majority (etcd, ZooKeeper)
- **AP systems** (choose availability): accept writes, reconcile later (DynamoDB with eventual consistency, Cassandra)
- **CA is not possible** during a partition — you must choose

For most web applications: eventual consistency is fine for reads (user profile, product catalog). Strong consistency is required for inventory counts, financial transactions, authentication.

---

← [Previous: AWS Fundamentals](./aws-fundamentals.md) | [Home](../README.md) | [Next: DevOps & SRE →](./devops-sre.md)
