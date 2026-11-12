# Complete Solution: Webhook Delivery Platform

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and delivery contract

Internal producers publish tenant events. Customers register HTTPS endpoints,
event-type filters, secrets, ordering preferences, and retry policy. The platform
signs requests, retries transient failures, records every attempt, disables abusive
or unhealthy endpoints, and supports controlled replay.

The contract is **durable at-least-once delivery**, not exactly once: one logical
delivery has a stable ID but its HTTP request may be received multiple times.
Consumers must deduplicate that ID. Default ordering is best effort; strict ordering
is optional per subscription and accepts head-of-line blocking.

Targets: 99.99% publish durability, accept publish p99 below 100 ms, begin 99% of
healthy-endpoint deliveries within 10 seconds, and retain attempt audit data for 30
days. Customer endpoint availability is excluded from platform availability.

## 2. Capacity estimation

Assume one billion logical deliveries/day, 10x bursts, average 4 KB payload, three
attempts/delivery, 100 ms median endpoint latency, and 1 MB maximum payload.

- Average logical rate is about 11,600/s; design for 120,000/s bursts.
- Three attempts average about 35,000 outbound requests/s.
- At 100 ms, average concurrency is 3,500; slow endpoints can multiply this, so
  concurrency and timeout limits are mandatory.
- Payload bytes are about 4 TB/day before compression/replication. Store one
  immutable payload per event, not one copy per subscription.
- Compact attempt metadata (~500 bytes) is roughly 1.5 TB/day for three billion
  attempts before indexes.

## 3. APIs

```text
POST   /v1/events                         Idempotency-Key
POST   /v1/subscriptions                  {url, eventTypes, filter, ordering}
PATCH  /v1/subscriptions/{id}             If-Match: version
POST   /v1/subscriptions/{id}/rotate-secret
GET    /v1/deliveries?subscriptionId=&status=&cursor=
GET    /v1/deliveries/{deliveryId}/attempts
POST   /v1/deliveries/{deliveryId}/replay Idempotency-Key
POST   /v1/endpoints/verify               {url}
```

Publish accepts tenant ID from authentication, immutable event ID/type/schema
version, occurrence time, and payload. Enforce payload, event-type, subscription,
filter-cost, replay-range, and retention quotas.

## 4. Data model and state machine

```text
Subscription(id, tenant_id, endpoint_url, event_types, filter_ast,
             ordering_mode, secret_current, secret_previous, secret_overlap_until,
             status, failure_score, max_concurrency, version)
Event(id, tenant_id, type, schema_version, payload_ref, checksum, occurred_at)
Delivery(id, event_id, subscription_id, sequence, state, attempt_count,
         next_attempt_at, lease_owner, lease_until, last_error, created_at)
Attempt(id, delivery_id, number, started_at, finished_at, status_code,
        error_class, latency_ms, response_excerpt)
ReplayJob(id, tenant_id, selector, state, cursor, requested_by)
Outbox(id, aggregate_id, kind, payload, published_at)
```

```text
PENDING -> IN_FLIGHT -> SUCCEEDED
                  \-> RETRY_WAIT -> IN_FLIGHT
                  \-> DEAD_LETTERED
PENDING/RETRY_WAIT -> CANCELLED (subscription disabled/deleted)
```

Every transition uses a conditional update on current state and lease/version.
`(event_id, subscription_id)` is unique, and every attempt number is unique within
a delivery.

## 5. Architecture

```text
producers -> publish API -> durable event log -> matcher/filter workers
                    |                            |
              payload object store        delivery database
                                                  |
                         due-time index/queues -> dispatch workers
                                                   |     |
                                           concurrency  egress proxy -> customer
                                               limiter       |
                                                     result/attempt log

control API -> subscriptions/secrets/replay/DLQ
```

Partition the event log by tenant/event ID and delivery records by subscription ID.
Queues contain delivery IDs, not payload bodies. A database due-time index remains
the source of recoverable work; the broker is an acceleration mechanism.

## 6. Step-by-step workflow

1. Authenticate producer, validate schema/size, and claim its idempotency key.
2. Store large payload immutably with checksum, then transactionally insert event
   metadata and an outbox/log record. A retry returns the same event ID.
3. Matcher loads the tenant's indexed candidate subscriptions by event type, then
   evaluates bounded compiled filters.
4. For each match, insert a stable delivery using unique `(event, subscription)` and
   set `next_attempt_at = now`; duplicates become no-ops.
5. Publish delivery ID to its ready partition. A sweeper also finds due database
   rows in case this publish is lost.
6. Dispatcher leases the delivery, obtains an endpoint concurrency token, signs and
   sends the request, records its attempt, then commits success/retry/dead-letter.

## 7. Core dispatcher logic

```text
function dispatch(deliveryId, workerId):
    delivery = deliveries.claimIfDue(
        deliveryId, workerId, now + LEASE_DURATION,
        allowedStates=[PENDING, RETRY_WAIT])
    if delivery == null: return

    sub = subscriptions.get(delivery.subscriptionId)
    if sub.status != ACTIVE:
        deliveries.transition(delivery, CANCELLED); return
    if !limiter.tryAcquire(sub.id, sub.maxConcurrency):
        reschedule(delivery, now + shortJitter()); return

    try:
        event = events.get(delivery.eventId)
        body = payloadStore.getVerified(event.payloadRef, event.checksum)
        timestamp = unixSeconds(now)
        signature = hmacSha256(sub.currentSecret,
                               timestamp + "." + body)
        result = http.postThroughEgressProxy(
            sub.endpointUrl, body,
            headers={"Webhook-Id": delivery.id,
                     "Webhook-Timestamp": timestamp,
                     "Webhook-Signature": "v1=" + signature},
            connectTimeout=2s, totalTimeout=10s,
            maxResponseBytes=64KB)
        finishAttempt(delivery, classify(result))
    finally:
        limiter.release(sub.id)
```

The network call cannot share a database transaction. If the process dies after the
customer accepts but before success is recorded, the lease expires and the request
is sent again. Stable `Webhook-Id` makes that unavoidable ambiguity manageable.

## 8. Atomic result and retry logic

```text
function finishAttempt(delivery, outcome):
    transaction:
        current = deliveries.getForUpdate(delivery.id)
        require current.state == IN_FLIGHT
        require current.leaseOwner == thisWorker
        attempts.insert(current.id, current.attemptCount + 1, outcome)

        if outcome.kind == SUCCESS:
            current.state = SUCCEEDED
        else if outcome.kind == PERMANENT or attemptsExhausted(current):
            current.state = DEAD_LETTERED
        else:
            current.state = RETRY_WAIT
            current.nextAttemptAt = now + backoff(current.attemptCount + 1)
        current.attemptCount += 1
        clearLease(current)
        outbox.insert(DeliveryStateChanged(current.id, current.state))
```

Treat 2xx as success; 408, 425, 429, 5xx, timeout, reset, and DNS/transient network
errors as retryable. Most other 4xx responses are permanent. Honor a bounded
`Retry-After`. Use full-jitter exponential backoff, for example a random duration
between zero and `min(24h, 30s * 2^(attempt-1))`, with maximum attempts/age.

## 9. Ordering modes

For default unordered delivery, partition by subscription but permit multiple
in-flight deliveries up to its concurrency cap. Consumers use event occurrence
time/sequence when business ordering matters.

For strict mode, assign a monotonically increasing subscription sequence and allow
only the lowest nonterminal sequence in flight. A failed event blocks successors
until success, operator skip, or expiry. Replay creates a new attempt generation but
retains the same logical delivery ID; an explicit redelivery can instead receive a
new ID when customers need a new business action.

## 10. Fairness, backpressure, and hot destinations

- Use hierarchical scheduling: global capacity, tenant token bucket, endpoint
  concurrency, then fair queue among subscriptions.
- Key destination limits by normalized host/IP as well as subscription so one host
  cannot evade limits with many URLs.
- Keep separate queue classes for first attempts, retries, and manual bulk replay;
  replay cannot starve live events.
- Increase failure score on timeout/5xx and apply circuit-breaker probes. Auto-pause
  persistently failing subscriptions after threshold and notify owner.
- Bound retained backlog per tenant/subscription; dead-letter or expire under the
  documented retention contract rather than exhausting shared storage.

## 11. Signing and secret rotation

Sign raw request bytes and timestamp using HMAC-SHA-256. The consumer verifies the
signature with constant-time comparison, rejects timestamps outside (for example)
five minutes, and deduplicates `Webhook-Id` in durable storage before applying the
business effect.

Rotation creates a new version and retains the previous key for a short overlap.
During overlap include `v1=<new>,v1=<old>` signatures or a key version. Secrets live
in a KMS-backed secret store and never appear in logs, delivery rows, or UI after
creation.

## 12. SSRF-safe egress

1. Require HTTPS and disallow URL credentials, fragments, unsupported ports, and
   unsafe redirect behavior.
2. Resolve DNS through a controlled resolver; reject loopback, link-local, private,
   multicast, metadata, and platform-owned ranges for every A/AAAA answer.
3. Pin the validated destination IP for the connection to prevent DNS rebinding;
   set correct TLS SNI/Host and validate the certificate.
4. Route only through a network proxy with the same deny rules and no internal
   service credentials.
5. Revalidate every redirect (prefer no redirects), cap request/response bytes,
   connection time, total time, and redirect count.

Endpoint verification proves control with a challenge but does not replace egress
checks on each delivery.

## 13. Replay and audit

Replay authorization is tenant-scoped and audited. A replay job scans a bounded
event/delivery range with a durable cursor, creates or resets work conditionally,
and emits through a low-priority quota. Display attempt time, status, latency, error
class, and truncated/redacted response—not secrets or arbitrary full response
bodies. Payload access uses short-lived authorization and follows retention policy.

## 14. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Producer retries publish | Idempotency key returns the same event |
| Matcher repeats an event | Unique event/subscription delivery prevents duplicates |
| Queue publish is lost | Due-row sweeper republishes unleased work |
| Worker dies before HTTP | Lease expires; another worker retries |
| Worker dies after HTTP | Request may repeat; stable ID enables consumer dedupe |
| Endpoint is slow | Timeout, per-host concurrency, circuit breaker isolate it |
| Result database unavailable | Stop new sends before leases become unsafe; retry later |
| Payload is corrupt/missing | Dead-letter and page; never send unverified bytes |
| Region fails | Promote fenced data replica and rebuild queues from due rows |
| Secret rotates mid-retry | Sign with active overlap versions; event identity is unchanged |

## 15. Security and privacy

Enforce tenant isolation and roles for subscriptions, payloads, attempts, replays,
and secrets. Encrypt storage and queues, use mTLS internally, minimize payload logs,
redact sensitive headers/responses, audit changes and replay, and scan/filter
payload display. Apply deletion, retention, residency, and legal hold to events,
payload blobs, attempts, caches, backups, and DLQs. Rate-limit API keys and prevent
subscription/event enumeration.

## 16. Observability

Measure publish and end-to-end success latency, oldest ready/retry age, attempts per
delivery, success by status/error class, endpoint latency, due-row/queue divergence,
expired leases, dedupe conflicts, concurrency saturation, circuit state, disabled
subscriptions, DLQ growth, replay progress, payload failures, and fairness by
tenant. Avoid high-cardinality endpoint URLs in metric labels.

Synthetic receivers exercise success, timeout, TLS, DNS rebinding, 429, retry-after,
and malformed responses. Chaos tests kill workers immediately before/after HTTP and
database commit. Reconciliation proves every matched durable event has one logical
delivery and every due nonterminal delivery is queued or leased.

## 17. Implementation path

1. **MVP:** event/payload persistence, subscription CRUD, stable delivery IDs,
   leases, fixed retries, attempt history, and one region.
2. **Correctness/security:** outbox and sweepers, HMAC rotation, response classifier,
   jittered retry, SSRF-safe proxy, idempotent replay, and reconciliation.
3. **Scale:** partitioned due index, fair scheduling, endpoint concurrency/circuits,
   filter index, DLQ, quotas, and backlog isolation.
4. **Hardening:** strict ordering option, regional failover/fencing, privacy
   lifecycle, load/chaos tests, restore drills, and customer-facing SLOs.

## 18. Final design

Persist one immutable event payload, materialize one stable delivery per matched
subscription, and drive a leased state machine from recoverable due-time storage.
The platform deliberately provides at-least-once HTTP delivery: leases, retries,
and sweepers prevent loss, while the stable signed delivery ID lets consumers make
duplicate requests harmless. Fair queues, destination isolation, and SSRF-controlled
egress keep arbitrary customer endpoints from threatening the shared system.
