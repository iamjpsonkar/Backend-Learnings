# Complete Solution: Distributed Rate Limiter

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Enforce limits by tenant, user, API key, IP, and endpoint; allow controlled bursts;
return remaining quota and retry time; update policies without restarting gateways;
and support regional operation. The decision path targets 99.99% availability and
under 5 ms p99 added latency inside a region.

The system does not replace authentication, billing metering, or downstream
concurrency limits. A client may satisfy its rate limit and still be rejected by
load shedding when the service is saturated.

## 2. Capacity estimation

Assume 1 million decisions/second globally across 20 regions, 3x regional peak,
100 million active counter keys, and a 2 ms store budget.

```text
average per region = 1,000,000 / 20 = 50,000 decisions/s
planned peak       = 50,000 * 3     = 150,000 decisions/s/region
counter memory     = 100M * ~100 B  = ~10 GB before replicas/overhead
```

Counters are ephemeral and expire after inactivity. Policies are durable and
strongly audited; counter state can tolerate bounded loss according to policy.

## 3. Policy and API

```text
Policy
  id, scope, resource_pattern
  algorithm = TOKEN_BUCKET
  refill_tokens, refill_period_ms
  burst_capacity
  failure_mode = OPEN | CLOSED | LOCAL_FALLBACK
  version, effective_at
```

The gateway uses an internal call or library:

```text
check(
  key="tenant:t1:user:u9:route:POST-/orders",
  policy_version=42,
  cost=1,
  request_id="..."
) -> {allowed, remaining, retry_after_ms, limit, policy_version}
```

HTTP rejection is `429 Too Many Requests` with `Retry-After` and rate-limit
headers. Invalid credentials remain `401/403`; do not hide auth failures as quota.

## 4. Chosen algorithm

Use a token bucket. Capacity controls the maximum burst; tokens refill continuously.
It uses constant state per key and maps naturally to one atomic Redis script.

```text
state: tokens, last_refill_ms

function decide(state, now, capacity, tokensPerMs, cost):
    elapsed = max(0, now - state.last_refill_ms)
    available = min(capacity, state.tokens + elapsed * tokensPerMs)

    if available >= cost:
        state.tokens = available - cost
        state.last_refill_ms = now
        return ALLOW, floor(state.tokens), 0

    missing = cost - available
    retryMs = ceil(missing / tokensPerMs)
    state.tokens = available
    state.last_refill_ms = now
    return DENY, floor(available), retryMs
```

Fixed windows are simpler but allow a 2x boundary burst. Exact sliding logs are
expensive. Sliding counters are useful when policy demands a closer window model,
but token bucket is the default.

## 5. Architecture

```text
admin -> policy API -> durable policy DB -> signed version stream
                                             |
client -> gateway -> local policy cache -> regional limiter proxy/library
                                             |
                                             v
                                   sharded Redis counter cluster
                                             |
                                   sampled decision event stream
```

- Gateways cache policies and never query the policy database per request.
- Redis shards counters by a stable hash of the complete limit key.
- Lua/function execution performs refill and consumption atomically on one shard.
- Metrics/events are sampled asynchronously and are not correctness dependencies.

## 6. Step-by-step workflow

1. Gateway authenticates the request and resolves route plus tenant.
2. It selects applicable policy versions and builds canonical keys. Multiple
   policies may apply, such as tenant, user, and route.
3. Cheap local protections run first: malformed/blocked clients and an emergency
   concurrency guard do not consume distributed-counter capacity.
4. Gateway sends keys and costs to the owning regional counter shards. Keys on
   different shards are checked in parallel.
5. Each shard runs the token-bucket function atomically using server time.
6. If every mandatory policy allows, gateway forwards the request. Otherwise it
   returns the strictest rejection and `Retry-After`.
7. The result updates metrics. A sampled immutable event supports analysis, not
   real-time correctness.

Checking several independent keys cannot be one atomic cross-shard transaction.
Some buckets may consume a token before another rejects. This conservative
over-count is acceptable; rollback would add complexity and permit abuse races.

## 7. Atomic Redis logic

```text
function checkBucket(key, policy, cost):
    now = redisServerTimeMs()
    state = HMGET(key, "tokens", "last_ms")

    if state missing:
        tokens = policy.capacity
        last = now
    else:
        tokens = parse(state.tokens)
        last = parse(state.last_ms)

    elapsed = clamp(now - last, 0, policy.maxRefillGapMs)
    tokens = min(policy.capacity,
                 tokens + elapsed * policy.tokensPerMs)

    if tokens >= cost:
        tokens = tokens - cost
        allowed = true
        retry = 0
    else:
        allowed = false
        retry = ceil((cost - tokens) / policy.tokensPerMs)

    HMSET(key, "tokens", tokens, "last_ms", now,
               "policy_version", policy.version)
    PEXPIRE(key, policy.inactiveTtlMs)
    return allowed, floor(tokens), retry
```

Using Redis server time avoids gateway clock disagreement. The key stores policy
version; when capacity changes, the script clamps existing tokens to the new
capacity rather than granting an unintended burst.

## 8. Key design and sharding

Canonicalize keys so equivalent paths do not create separate buckets. Use route
templates (`/users/{id}`), not raw paths. Hash sensitive IP/API identifiers before
storage, and include tenant to prevent cross-tenant collisions.

```text
rl:{tenant_hash}:{scope}:{subject_hash}:{route_id}
```

Consistent hashing maps keys to Redis shards. A single celebrity key is inherently
hot. Mitigations are local token leasing for that policy, a dedicated shard, or
hierarchical regional budgets—not salting a strict counter, which loses accuracy.

## 9. Local token leasing for extreme scale

A regional shard may lease small token batches to gateways:

1. Gateway atomically reserves 100 tokens from the regional bucket.
2. It spends them locally with an in-process bucket.
3. Lease expires quickly; unused tokens may be lost rather than returned.
4. Maximum overshoot is bounded by lease size times active gateways.

Use leasing only where this bound is acceptable. Authentication, payment, and
fraud-sensitive limits should keep per-request atomic checks.

## 10. Global limits

Strict cross-region counters require every request to coordinate with a home
region or consensus system, increasing latency and reducing availability. Prefer:

1. Split a global quota into regional budgets.
2. Regions report consumption periodically.
3. Allocator moves future budget toward demand while retaining safety reserve.
4. Total possible overshoot is explicitly bounded and monitored.

Use a home-region strict limit only when business risk outweighs latency and
regional availability.

## 11. Policy rollout

1. Admin writes a validated immutable policy version.
2. Control plane canaries it to selected gateways.
3. Gateways atomically swap complete snapshots and report active version.
4. Decisions include version in metrics and counter state.
5. Health regression pauses or rolls back. Last-known-good remains cached during
   control-plane failure.

## 12. Failure handling

| Failure | Behavior |
| --- | --- |
| One Redis replica fails | Promote healthy replica; client retries once within deadline |
| Whole counter shard unavailable | Apply policy-specific OPEN, CLOSED, or conservative local fallback |
| Policy control plane unavailable | Continue signed last-known-good snapshot |
| Gateway restarts | Distributed counters remain; local emergency/leasing state resets conservatively |
| Network partition | Regional limits continue; global budget may temporarily drift within bound |
| Hot key overload | Dedicated capacity or bounded local leases; never silently split strict counter |
| Redis data loss | Buckets reset according to recovery mode; sensitive policies fail closed until restored |

Failure mode must be explicit per policy. Login attempts may fail closed; a public
read API may fail open with local protection. One universal choice is unsafe.

## 13. Security and correctness

- Only trusted gateway identities can call limiter shards.
- Sign and version policy snapshots; audit every policy change.
- Hash personal identifiers and set short counter TTLs.
- Bound key length, cost, capacity, and refill values to prevent memory/CPU abuse.
- Do not trust client-provided IP headers except from the controlled edge.
- Idempotency is usually not applied to decisions: two actual attempts should cost
  two tokens. Retries internal to the gateway must not execute the decision twice.
- Separate rate limits from concurrency limits and circuit breakers.

## 14. Observability

Measure decision QPS and p99, allow/deny by policy/version, Redis latency/errors,
hot keys/shards, memory and expirations, fail-open/fail-closed/local-fallback count,
policy propagation age, regional/global budget drift, and downstream load after
limiter decisions.

Test boundary bursts, clock anomalies, policy reductions, shard loss, region
partition, hot keys, and whether the returned `Retry-After` matches refill math.

## 15. Implementation path

1. **MVP:** gateway-local token buckets for one instance or a single Redis cluster,
   static policies, and clear 429 responses.
2. **Distributed correctness:** atomic server-time script, canonical keys, TTL,
   sharding, replicas, and per-policy failure mode.
3. **Control plane:** durable versioned policies, validation, signed snapshots,
   canaries, audit, and last-known-good behavior.
4. **Global scale:** regional clusters and budgets, hot-key isolation, optional
   bounded token leasing, capacity tests, and disaster drills.

## 16. Final design

Use regional atomic token buckets backed by sharded Redis, with policies evaluated
from gateway memory and managed by a versioned control plane. Prefer bounded
regional budgets over strict global coordination. The core invariant is: one
accepted distributed decision consumes its cost atomically from every strict
bucket that is successfully evaluated, while failure behavior is explicit and
observable for each policy.
