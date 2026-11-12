# Complete Solution: Publish-Subscribe Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Publishers append schema-validated events to topics. Each independent subscription
selects all events or a bounded attribute filter and consumes through pull, push or
export with its own cursor, ACK deadline, retry/dead-letter and retention policy.
Subscribers can pause, seek/replay, scale workers and change delivery config without
affecting others. Store payload once where possible and isolate slow/broken subscribers.

Targets: one billion events/day, average five matching subscriptions, publish p99 below
100 ms, pull fetch below 200 ms, healthy push starts within seconds, 99.99% service
availability and no loss of acknowledged durable publications. Delivery is at least
once; stable event/delivery IDs let consumers deduplicate. Ordering is only within a
declared topic partition/subscription stream and may be relaxed by retries.

## 2. Capacity estimation

One billion events/day averages 11,600/s. At 1 KB/event and 5x peaks:

- logical payload ingress is 1 TB/day before replication/compression;
- five matching subscriptions yield five billion delivery references/day, average
  58,000/s and peak near 300,000/s;
- a 40-byte reference is 200 GB/day before indexes/replicas, so shared cursors/ranges
  are better when filters/order permit;
- independent subscriber egress can be 5 TB/day or much more if fan-out is high;
- one slow subscription cannot pin unlimited shared payload retention—enforce age/
  bytes limits and tier/archive/DLQ policy.

## 3. APIs

```text
POST /v1/topics                           {schemaPolicy, partitions, retention}
POST /v1/topics/{topic}/events            {events[]} Idempotency-Key/producer sequence
POST /v1/subscriptions                    {topic, filter, mode, config} Idempotency-Key
PATCH /v1/subscriptions/{id}              If-Match: version
POST /v1/subscriptions/{id}:pull           {maxEvents, maxBytes, waitSeconds}
POST /v1/subscriptions/{id}:ack            {ackIds[]}
POST /v1/subscriptions/{id}:nack           {ackIds[], delay}
POST /v1/subscriptions/{id}:seek           {timestamp|eventId|offset} Idempotency-Key
GET  /v1/subscriptions/{id}/dead-letters?cursor=
POST /v1/subscriptions/{id}:replay-dead-letters Idempotency-Key
```

Filters operate only on indexed allowlisted envelope attributes, not arbitrary payload
code. Bound publish batch/payload/attributes, subscriptions/topic, filter complexity,
ACK deadline/extensions, inflight deliveries, replay range/rate, retention and push endpoints.

## 4. Data model

```text
Topic(id, tenant_id, name, partitions, retention, schema_policy, config_version)
Event(topic_id, partition, offset, event_id, ordering_key, schema_id,
      attributes, payload_ref_or_bytes, publish_time, producer_identity)
Subscription(id, tenant_id, topic_id, filter_ast, filter_version,
             start_offsets, delivery_mode, ack_deadline, retry_policy,
             dead_letter_topic, state, version, created_at)
SubscriptionPartition(subscription_id, topic_partition, scan_offset,
                      delivered_watermark, backlog_generation, version)
DeliveryRef(subscription_id, topic_partition, event_offset, delivery_generation,
            state, attempt, next_at, lease_epoch, lease_until, last_error)
PushAttempt(delivery_ref, attempt, started_at, status, latency, response_excerpt)
DeadLetter(subscription_id, event_ref, attempts, reason, first_at, last_at)
Inbox/Idempotency(caller, key_or_event_id, request_hash, result)
```

Event log/payload is authoritative. Delivery refs/cursors are derived operational state
and rebuildable within retention. Immutable subscription/filter versions define why an
event did or did not match.

## 5. Architecture

```text
publisher -> auth/schema/quota -> durable partitioned topic log + payload tier
                                           |
                                     matcher/index workers
                                      /              \
                            shared scan cursors    delivery-reference backlogs
                                      \              /
                                  subscription scheduler
                                   /        |         \
                               pull API  push workers  export connector
                                  |          |
                           ACK leases   signed endpoint
                                  \          /
                               retry scheduler -> dead-letter topics/store

control plane -> topic/subscription/schema/filter/config/version metadata
```

For unfiltered/cheap ordered subscriptions, store only per-partition scan/commit state.
For selective filters, delayed independent retry, push and merged partitions, materialize
compact delivery references. Never duplicate payload bytes per subscription by default.

## 6. Step-by-step workflow

1. Publisher authenticates, schema/envelope validates, selects partition from ordering
   key, and durably quorum-appends event/payload with stable ID/producer sequence.
2. Matcher consumes topic partitions in offset order and chooses the subscription
   snapshot effective for event publish/scan semantics. It evaluates compiled indexed
   filters and advances scan checkpoints.
3. For a match, conditionally create delivery reference or make offset visible to a
   shared cursor. Duplicate matcher replay is harmless.
4. Pull scheduler leases visible refs and returns receipt/ACK IDs; push worker leases,
   signs body/timestamp/delivery ID and calls controlled endpoint.
5. ACK current lease marks delivered/advances contiguous cursor. Timeout/NACK/transient
   push failure schedules jittered retry. Permanent/max-attempt/max-age moves reference
   to DLQ and unblocks ordering according to policy.
6. Replay creates a bounded audited generation/seek and competes under lower-priority
   quotas; consumer deduplicates original event ID.

## 7. Publish logic

```text
function publish(principal, topic, batch):
    authorize(principal, topic, PUBLISH)
    enforceQuotaAndBatchLimits(principal.tenant, batch)
    for event in batch:
        schemaRegistry.validate(topic.schemaPolicy, event.schemaId, event.payload)
        validateIndexedAttributes(event.attributes)
        partition = stablePartition(topic, event.orderingKey ?? event.eventId)
        log.appendIdempotent(
          topic, partition, producerId=principal.producerId,
          producerEpoch, sequence,
          Event(eventId, schemaId, attributes, payload, serverPublishTime),
          requiredAcks=ALL)
    return assigned partitions/offsets after high watermark
```

Producer timeout retries same identity/sequence. Event ID remains stable across any
business retry and is globally unique within topic/tenant policy. Publish success does
not wait for every subscription match/delivery.

## 8. Filter compilation and matching

Support bounded equality/set/range/prefix/existence expressions over declared envelope
attributes, for example:

```text
attributes.eventType IN ["order.created", "order.cancelled"]
AND attributes.region == "IN-WEST"
AND attributes.totalMinor >= 10000
```

Compile type-checked AST against attribute schema, cap nodes/sets/ranges, reject regex/
payload traversal unless specialized safe engine. Build inverted subscription indexes:
attribute-value -> candidate subscription IDs, with a residual predicate. For each
event, intersect/select most selective posting then evaluate residual, rather than scan
millions of subscriptions.

```text
function match(event, subscriptionSnapshot):
    candidates = index.lookupRarestClauses(event.attributes)
    for sub in candidates:
        if sub.state == ACTIVE and sub.compiledFilter.evaluate(event.attributes):
            refs.insertUnique(sub.id, event.partition, event.offset,
                              filterVersion=sub.filterVersion)
    checkpoint matcher partition offset transactionally/idempotently
```

No-filter subscriptions use range/cursor registration and avoid per-event reference.

## 9. Subscription creation and filter changes

Creation transaction stores start offsets (latest, earliest within retention, or
timestamp), immutable filter version and activation watermark. Define boundary:
events at offsets before activation use old/no subscription, later offsets use new.
Matcher uses metadata snapshot by partition offset/control version.

A filter update creates new version/effective offsets; it does not retroactively change
past matches unless user explicitly seeks/replays under chosen filter version. Delivery
config changes (endpoint, ACK deadline) can apply immediately to future attempts with
version. Delete pauses delivery, revokes tokens/leases, then removes backlog/payload
references after retention policy.

## 10. Pull lease and ACK logic

```text
function pull(consumer, subscriptionId, limits):
    authorize consumer; enforce inflight quota
    transaction/batch CAS:
        refs = select due AVAILABLE refs ordered by subscription policy
        for ref in refs:
            ref.state = LEASED
            ref.leaseEpoch += 1
            ref.leaseUntil = now + ackDeadline
            ref.attempt += 1
    return payloads plus ackId=sign(sub, ref, leaseEpoch, leaseUntil)

function ack(consumer, ackIds):
    transaction/batched:
        for ackId:
            verify signature/subscription/consumer
            ref = getForUpdate(ackId.ref)
            if ref.state == LEASED and ref.leaseEpoch == ackId.epoch:
                ref.state = ACKED
                advance contiguous delivered watermark where applicable
```

Expired lease sweeper returns to AVAILABLE with backoff or DLQ. An old ACK cannot delete
a message leased to another worker. ACK is idempotent; after response loss, repeated ACK
or redelivery is safe. Extension is bounded and epoch-checked.

## 11. Push delivery logic

```text
function deliverPush(ref):
    lease current ref under endpoint concurrency/fair quota
    event = topicLog.fetchVerified(ref.topicPartitionOffset)
    body = canonicalEnvelope(event, subscription, deliveryId=stable(ref))
    signature = HMAC(secretVersion, timestamp + "." + body)
    result = egressProxy.post(endpoint, body, headers, strictTimeout/responseLimit)
    transaction:
        record attempt
        if 2xx: mark ACKED
        else if retryable (timeout, 408, 425, 429, 5xx): schedule full-jitter backoff
        else: dead-letter/permanent-failure policy
```

Prevent SSRF: HTTPS, validate/pin public DNS IP, block internal/metadata/private ranges,
revalidate redirects (prefer none), verify TLS and cap response/time. Stable delivery
and event IDs let endpoint dedupe. Secret rotation overlaps versions briefly.

## 12. Ordering choices

Ordering can be:

- per source topic partition: preserve offsets but one failed event can block later;
- ordered per ordering key if key always maps to one partition;
- unordered/parallel: retries do not block but arrival order varies;
- best-effort merge across partitions: attach publish time/offset, no total order.

Strict mode delivers only next offset/reference and waits for ACK/DLQ/skip. Parallel
mode permits configurable inflight; ACK watermark advances only across contiguous
terminal refs while sparse states remain. Document whether DLQ counts terminal and
manual replay order.

## 13. Retry, DLQ, and replay

Backoff example uses random `0..min(maxDelay, base*2^(attempt-1))`, honoring bounded
`Retry-After`. Different lanes for first attempt/retry/replay prevent storms starving
fresh events. Circuit-break failing push endpoint and auto-pause under policy.

DLQ retains event reference/payload retention pin or copy, original topic/partition/
offset/event ID, subscription/filter version, attempts/errors and timestamps. Access is
sensitive/audited. Replay validates schema/current subscription, creates new delivery
generation with original event ID, and checkpoints job; it never erases DLQ evidence.

## 14. Backlog and payload retention

Shared payload expires by topic policy unless a subscription contract pins it. Options:

- enforce max backlog age/bytes and DLQ/expire oldest with explicit data-loss metric;
- copy cold payload to subscription-owned archive before shared expiry;
- charge tenant for retention pin and cap it;
- pause producer/topic only for dedicated/private systems, not a shared multi-tenant bus.

Track oldest unacked offset versus topic log start. Before deleting shared segment,
ensure all guaranteed subscribers are terminal or archived. A cursor behind log start
receives `DATA_LOSS/SEEK_REQUIRED`, never silent jump.

## 15. Exactly-once boundary

Network delivery to arbitrary pull/push consumers cannot be exactly once: process may
succeed and ACK be lost. Promise at least once. Consumer deduplicates event ID in same
transaction as business effect/outbox, or calls an idempotent API.

For broker-native consume-transform-publish, transactional producer can atomically
commit output plus input subscription offsets, and readers hide aborted records. This
does not cover email, external DB or webhook unless a connector uses compatible sink
transaction/idempotency.

## 16. Partitioning and scaling

Topic partitions own event order; subscription matcher shards by topic partition and
subscription-index bucket. Delivery refs shard by subscription ID + topic partition,
allowing consumer concurrency. A giant fan-out event is spread by subscription buckets
while unique ref prevents duplicates. Hot subscriber receives dedicated shards/quotas.

Regional topic placement follows publisher/data residency. Cross-region subscriptions
use async mirrored topic with explicit lag/RPO/order identity or synchronous replicated
topic with WAN cost. Never merge independent active regions and claim one total order.

## 17. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Publisher times out after commit | Same producer sequence returns original offset |
| Matcher dies/replays | Unique delivery ref and checkpoint make replay harmless |
| Pull worker dies | Lease expires; event redelivers |
| Old pull ACK arrives | Lease epoch rejects it |
| Push endpoint accepts but response is lost | Delivery repeats; stable ID enables dedupe |
| Subscription filter changes mid-scan | Effective offset/version chooses one filter |
| Payload would expire behind backlog | Archive/DLQ/explicit data-loss per contract |
| One tenant endpoint fails | Per-endpoint circuit/quota isolates it |
| Region fails | Resume from replicated log/state with documented RPO/fencing |

## 18. Security and governance

Use mTLS/OAuth/service identities, topic publish/subscription/consume/seek/DLQ ACLs,
tenant quotas, envelope schema/attribute policy, TLS/encryption, secrets vault, signed
push, egress proxy, audit for config/seek/replay/admin and credential rotation. Prevent
cross-tenant subscription, filter inference of secret attributes, topic enumeration,
payload/decompression bombs, retention pin abuse, ACK forgery, replay storms, webhook
SSRF, DLQ leakage and insider payload access.

Apply data classification, consent, retention/deletion/legal hold/residency and key-
based erasure. Payloads/logs may contain secrets; minimize samples/error excerpts and
never expose them in metric labels. Filterable attributes must be safe to index.

## 19. Observability

Track publish/match/fetch/ACK/push latency/errors/bytes, events and matched refs/event,
matcher offset/lag/filter candidates/CPU, subscriptions/state/version, backlog count/
bytes/oldest age and distance to retention loss, lease inflight/expiry/extensions,
attempt/retry/DLQ/replay, push status/latency/circuits/signature, delivery duplicate/
end-to-end age, payload fetch/tier/cache, strict-order blocked age, per-tenant quota and
storage/egress cost.

Property tests replay/duplicate matcher events, lease/ACK races, filter activation
boundaries, retention and strict ordering. Contract-test push signature/SSRF/retries.
Load-test high fan-out, one huge backlog and failing endpoint. Chaos topic/matcher/state/
workers/region; reconcile topic offsets against guaranteed subscription refs/cursors,
DLQ and payload retention manifests.

## 20. Implementation path

1. **MVP:** durable partitioned topic, no-filter pull subscriptions, per-partition
   cursor/lease/ACK, at-least-once IDs, retention and basic ACLs.
2. **Independent delivery:** materialized refs, retry scheduler/DLQ/replay, ordering
   policies, filter compiler/index, subscription versions and backlog quotas.
3. **Channels/scale:** push with signed SSRF-safe egress, export connectors, high fan-
   out matching, tier/archive, transactional broker flow, regional mirrors.
4. **Hardening:** governance/security/privacy, property/contract/fanout-load/chaos tests,
   retention/replay/restore drills, runbooks, dashboards, and SLOs.

## 21. Final design

Publish each event once to a quorum-durable partitioned topic, then give every
subscription independent versioned match, backlog and delivery state. Compiled attribute
indexes avoid scanning all filters; shared cursors serve simple subscriptions and compact
references serve selective/retrying push/pull flows. Lease epochs make redelivery/old
ACK races safe, signed push retries use stable IDs, and DLQ/replay is bounded/audited.
Explicit ordering, retention and at-least-once contracts keep one slow or failing
subscriber isolated without pretending an arbitrary external side effect is exactly once.
