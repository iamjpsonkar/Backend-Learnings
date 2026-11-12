# Complete Solution: Distributed Message Queue

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Producers append keyed records to named topics. Records are durably ordered within a
partition, replicated across zones, retained for replay, optionally compacted by key,
and fetched in batches. Consumer groups assign each partition to at most one active
member and commit progress. Support idempotent producers, delayed/dead-letter workflows,
schema controls, quotas, tiered storage and safe cluster expansion/failure recovery.

Targets: ten million records/s at 1 KB average, publish/fetch p99 below 20/50 ms for
normal load, 99.99% service availability, no loss for acknowledged quorum writes, and
bounded failover/rebalance. Ordering exists only per partition. Base delivery is at
least once; consumers must make side effects idempotent unless using a compatible
transactional read-process-write protocol.

## 2. Capacity estimation

Ten million records/s × 1 KB is 10 GB/s ingress. With replication factor 3:

- broker replication ingress/egress adds roughly 20 GB/s plus producer/consumer reads;
- one day of logical retention is 864 TB before compression; seven days is 6 PB,
  requiring compression, large fleet and/or object-store tier;
- at 5:1 compression, physical hot retention falls significantly but plan by data type;
- 100,000 partitions × three replicas create 300,000 logs, leader tasks, open segments,
  indexes and metadata; partitions are not free;
- batch 1–10 MB requests to turn random RPC overhead into sequential disk/network I/O;
- egress can exceed ingress by number of independent consumer groups and must be quotaed.

## 3. API and wire operations

```text
CreateTopic(name, partitions, replication, retention, cleanupPolicy, schemaPolicy)
Produce(topic, partition|key, records[], producerId, producerEpoch,
        firstSequence, requiredAcks, timeout)
Fetch(topic, partition, offset, maxBytes, minBytes, maxWait, isolation)
JoinGroup(groupId, memberId, protocols, subscriptions)
SyncGroup(groupId, generation, assignments)
Heartbeat(groupId, memberId, generation)
CommitOffsets(groupId, generation, memberId, offsets, metadata)
ListOffsets(topic, partition, timestamp|earliest|latest)
Begin/Commit/AbortTransaction(transactionalId)
```

Administrative APIs are versioned/audited. Bound record/batch/header size, partitions/
tenant, producer inflight requests, fetch bytes, groups, retention, transaction timeout
and schemas. Client discovers partition leader/coordinator from metadata and refreshes
on epoch errors.

## 4. Data model and durable structures

```text
Topic(id, tenant, name, partition_count, replication_factor,
      cleanup_policy, retention, min_isr, config_version)
Partition(topic_id, number, leader_broker, leader_epoch,
          replicas[], in_sync_replicas[], high_watermark, log_start_offset)
RecordBatch(base_offset, last_offset, leader_epoch, producer_id,
            producer_epoch, first_sequence, record_count, compression,
            max_timestamp, crc, transactional_state)
LogSegment(base_offset, end_offset, file_ref, size, created_at, checksum, state)
SparseOffsetIndex(relative_offset -> byte_position)
TimeIndex(timestamp -> relative_offset)
ProducerState(producer_id, epoch, last_sequence, last_offset, recent_batches)
ConsumerGroup(id, state, generation, protocol, leader_member, assignment_version)
GroupMember(id, instance_id, subscriptions, session_timeout, assignment)
CommittedOffset(group_id, topic, partition, next_offset, generation, metadata)
```

Controller metadata is a small replicated consensus state machine. Partition records
live in immutable/append-only segments; caches/indexes rebuild from logs.

## 5. Architecture

```text
producers -> metadata lookup -> partition leader -> page cache/segment log
                                      |       \
                                      |        follower replicas across zones
                                      |                 |
                                 high watermark <-------+

consumers -> group coordinator -> partition assignment
     |                                  |
     +-------- fetch leaders ---------->+ logs
     +-------- commit offsets -> coordinator log/state

consensus controllers -> broker/topic/partition/leader/config metadata
segment uploader -> object tier; remote fetch cache <- tiered segments
```

Broker data plane does not synchronously call controller per request. Controller elects
leaders and changes assignments/config with epochs; broker rejects stale metadata.

## 6. Step-by-step workflow

### Produce

1. Producer fetches metadata, serializes key/value against schema policy, chooses
   partition (explicit or stable key hash), batches, compresses and assigns producer
   sequence.
2. Current leader verifies topic ACL/quota/leader epoch, CRC, producer epoch/sequence
   and batch limits; duplicate known sequence returns prior offsets.
3. Leader appends batch to local log/page cache with assigned contiguous offsets and
   followers fetch/append it in order.
4. Leader advances high watermark only to offset replicated on required in-sync quorum.
   `acks=all` responds after the durability rule; timeout leaves result unknown and
   producer retries same ID/sequence.

### Consume

1. Members join group; coordinator increments generation and assigns partitions using
   range/round-robin/sticky/cooperative protocol.
2. Assigned consumer fetches at its next offset. Leader returns only committed/high-
   watermark data under `read_committed` and long-polls when empty.
3. Consumer processes records and commits the **next** offset only after side effects.
4. Crash before commit causes replay (at least once); commit before side effect can lose
   processing and is incorrect for ordinary consumers.

## 7. Core leader append logic

```text
function produce(request):
    partition = localPartition(request.topic, request.partition)
    require partition.isLeader and request.metadataEpoch <= partition.leaderEpoch
    authorizeAndQuota(request.tenant, WRITE, request.bytes)
    validateBatchCrcSchemaAndLimits(request.batch)

    with partition.appendLock:
        producer = producerState.get(request.producerId)
        require request.producerEpoch >= producer.epoch
        if request.producerEpoch > producer.epoch:
            fence older epoch and reset allowed sequence to 0
        if request.lastSequence <= producer.lastSequence:
            return offsetsOfKnownDuplicate(request)
        require request.firstSequence == producer.lastSequence + 1

        base = partition.logEndOffset
        encoded = request.batch.withOffsets(base).withLeaderEpoch(partition.leaderEpoch)
        log.append(encoded)
        producerState.stageAdvance(request, base)
        replication.notifyFollowers(partition)

    if request.acks == ALL:
        wait until partition.highWatermark > encoded.lastOffset
              and currentISR.size >= topic.minISR
              or timeout/leadership change
    return baseOffset and lastOffset
```

Persist/recover producer state from log snapshots plus recent scan. Sequence-window
dedupe is bounded; producers retry only unresolved recent requests. Same producer ID
with higher epoch fences a zombie client.

## 8. Replication and high watermark

Followers continuously fetch from leader at their log end offset, verify epoch/CRC,
append and report durable progress. Leader keeps a replica in ISR only when lag/time
is within thresholds. High watermark is the maximum offset such that all required ISR/
quorum replicas contain records below it. Consumers do not see uncommitted tail.

`acks=leader` can lose acknowledged records after leader failure and is an explicit
trade-off. With `acks=all`, require `minISR >= 2` across failure domains. Do not elect
an out-of-sync replica under lossless policy; prefer unavailability. Unclean election
must be a deliberate topic policy with acknowledged data-loss risk.

## 9. Leader failure and log reconciliation

Controller detects broker session loss, chooses the most up-to-date eligible ISR,
increments leader epoch, commits metadata, and tells replicas. New leader exposes only
committed prefix. Followers compare leader-epoch checkpoint/divergence, truncate an
uncommitted conflicting tail, then fetch from new leader. Old leader is fenced by
controller epoch and cannot accept writes.

Clients receive `NOT_LEADER_OR_EPOCH`, refresh metadata and retry same producer
sequence/fetch offset. Never truncate below committed high watermark. Cross-zone quorum
survives one zone loss if placement/minISR/capacity are correct.

## 10. Log storage

Each partition uses sequential segment files:

```text
00000000000000000000.log / .index / .timeindex
00000000001000000000.log / .index / .timeindex
```

Record batches contain CRC and compression; sparse offset index locates nearest byte,
then scan. Roll by bytes/time, fsync according to durability/group-commit policy, use
zero-copy send/page cache, preallocate and checksum segments. Recovery scans last
segment, discards incomplete trailing batch, rebuilds indexes and verifies committed
boundaries. Disk scheduler separates replication/fetch/compaction workloads.

## 11. Consumer-group coordination

```text
function join(member):
    coordinator transaction/log append:
        add/update member and subscriptions
        group.generation += 1
        compute or delegate assignment so each partition has <= 1 active owner
        persist generation/assignment
    return generation, assignment

function commit(group, member, generation, offsets):
    require group.generation == generation
    require member owns every partition in offsets
    append compacted coordinator record
    return committed
```

Heartbeats/session timeout detect dead members. Generation fences zombie commits.
Cooperative sticky rebalance revokes only partitions that move: consumer stops fetching,
finishes/commits within deadline, acknowledges revoke, then new owner starts. Static
membership reduces churn after brief restart. Long processing uses bounded polling or
worker pool with per-partition ordered commit tracking.

## 12. Delivery semantics

### At least once

Process then commit. Crash after side effect before commit repeats record. Consumer
uses message/business ID uniqueness, inbox table, conditional state transition or
idempotent external API.

### At most once

Commit before process. Crash can lose effect. Appropriate only for explicitly lossy data.

### Transactional read-process-write

A producer with `transactional_id` atomically commits output batches and consumed
offsets to this broker. Coordinator fences epochs, transaction markers resolve batches,
and `read_committed` skips aborted/uncommitted records. This provides exactly-once
processing **inside compatible queue topics/state**, not an arbitrary database/email/
payment side effect. External sinks still need idempotency or transactional connector.

## 13. Pull queue versus visibility-lease mode

The partition-offset log favors ordered streams/replay. A work-queue API may add
per-message visibility leases when consumers need independent concurrent tasks:

```text
Ready -> Leased(receiptHandle, leaseEpoch, deadline) -> Acknowledged
                    \-> Ready on expiry/nack -> DeadLetter after attempts
```

Ack validates current receipt/epoch; old worker cannot delete a reassigned task.
Durable due/lease indexes and sweepers recover expirations. This mode sacrifices simple
partition offset compression/order and has much more state. Do not combine semantics
implicitly—offer separate topic/queue types and document ordering/replay behavior.

## 14. Delayed messages and dead-letter queues

For moderate delays, write message reference to durable hierarchical time buckets/
timing wheel partitioned by due time. Scheduler claims due entries, appends original
payload/reference idempotently to destination partition, and marks scheduled record
released. Database/object index sweep recovers lost timer notifications.

Consumer/application counts attempts by stable record identity and republishes to
retry topics with increasing delay; after policy, append to DLQ with original topic/
partition/offset/schema, error class, attempts and timestamps. DLQ is encrypted/
access-controlled, retained/quotaed and has audited replay with new generation.

## 15. Retention, compaction, and tiered storage

Time/size retention deletes only whole segments older than policy and below safety
constraints. Consumer lag does not automatically prevent deletion unless topic offers
that contract; expose data-loss risk/lag horizon.

Log compaction retains latest value per key plus tombstones long enough for consumers/
replicas to observe deletes. Cleaner rewrites eligible closed segments into new files,
verifies offsets/checksums, then atomically swaps; offsets remain stable with gaps.

Tiered storage uploads immutable closed segments/checksums/indexes to object store,
records remote manifest, then evicts local copy after replication/verification. Remote
fetch uses cache/range reads and is slower/quotaed. Never delete last verified copy
before manifest/object durability is proven.

## 16. Partitioning and rebalancing data

Stable hash(key) modulo a fixed partition count preserves per-key order until count
changes. Increasing partitions changes mapping; use versioned partitioner or virtual
buckets if long-lived key ordering matters. Keyless round-robin improves balance but
no entity order. Hot key remains one partition; producer-side aggregation or domain
key redesign is needed—not random salting if order is required.

Broker balancer moves follower replica first, catches up, adds to ISR, transfers leader
if desired, then removes old replica. Throttle migration to protect client latency and
respect rack/zone/disk placement. Controller state tracks reassign generation.

## 17. Backpressure and quotas

Hierarchical quotas limit tenant/topic/producer/group bytes, requests, connections,
partitions, retention and remote reads. Broker delays/throttles before overload and
returns retry time. Producer has bounded buffer/inflight batches and blocks/fails by
policy, never infinite memory. Consumers use fetch size/wait and pause partitions.

Protect replication/controller traffic over client traffic, then durable produce,
consumer fetch, remote replay/compaction. Disk nearly full triggers admission and
placement remediation before corruption; never delete data outside retention to appear healthy.

## 18. Schema and compatibility

Topic can require schema ID in record header. Registry authenticates owners, versions
schemas and enforces backward/forward/full compatibility per topic. Broker checks ID/
size cheaply; producer/consumer libraries serialize/validate. Retain schemas as long
as retained records. Quarantine/DLQ poison data at consumer boundary without blocking
an entire partition indefinitely; sensitive schemas/fields follow classification policy.

## 19. Multi-region choices

- Single-region multi-zone quorum: low latency and zone durability.
- Async mirror to disaster region: local latency, nonzero RPO and independent offsets/
  failover runbook; dedupe after promotion.
- Synchronous cross-region quorum: stronger RPO but WAN latency/lower availability.
- Active-active independent topics: requires application conflict/idempotency and does
  not give one global partition order.

Document RPO/RTO and producer DNS/metadata fencing. Disaster failover must prevent old
region from accepting the same logical writer or reconcile duplicates.

## 20. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Producer times out after commit | Retry same producer sequence returns prior offsets |
| Partition leader dies | Elect eligible ISR, increment epoch, expose committed prefix |
| Old leader/producer returns | Leader/producer epoch fences it |
| Consumer dies after effect | Record replays; consumer idempotency prevents duplicate effect |
| Consumer rebalance races commit | Group generation rejects zombie offset commit |
| Segment tail is torn | CRC scan truncates only incomplete/uncommitted tail |
| Disk/broker fails | Replicas serve/elect; replace and bootstrap from peer/object tier |
| Object tier unavailable | Hot local data works; remote reads fail explicitly/backpressure |
| Controller loses leader | Consensus elects; data plane continues cached metadata briefly |

## 21. Security and tenant isolation

Use mTLS/OAuth/service identities, topic/group/transactional-ID ACLs, tenant quotas,
TLS, per-tenant/cluster encryption keys where required, signed metadata/artifacts,
credential rotation, network segmentation and tamper-evident admin/config/access audit.
Prevent topic/group enumeration, cross-tenant fetch/commit, producer-ID hijack, schema/
payload bombs, decompression attacks, SSRF in connectors, DLQ secret leaks, disk exhaustion,
request amplification and malicious consumer pinning retention.

Classify/encrypt payloads, minimize broker logs, support retention/deletion/legal hold/
residency, secure erase via keys, and restrict operator data inspection. Broker cannot
enforce field privacy for encrypted opaque payloads; client governance is part of contract.

## 22. Observability

Track produce/fetch latency/error/throttle/bytes/batches/compression, records/s, partition
leaders/epochs/skew/hot keys, log end/high watermark, ISR shrink/under-replicated/offline
partitions, follower lag, disk/page-cache/network/fsync, controller elections/metadata
age, producer duplicate/out-of-order/fencing, groups/members/rebalance duration/churn,
consumer lag/time-to-retention-loss/commit failures, transactions age/aborts, compaction/
tombstone/remote-tier lag, DLQ/retry/lease expiry, quotas and cost/GB.

Property/model tests generate leader failover, duplicate/reordered producer requests,
epoch changes, consumer rebalances and transactional markers and assert acknowledged
prefix/order/dedupe invariants. Fuzz batch/CRC/compression. Load-test hot key, small
records, large batches and many partitions/groups. Chaos disk/network/zone/controller/
object tier; scrub segment checksums and restore/replay regularly.

## 23. Implementation path

1. **MVP:** single broker append-only partition logs, batch produce/fetch, offsets,
   retention, CRC/index recovery and simple ACLs.
2. **Durability:** multi-zone replication/high watermark, consensus controller, leader
   epochs/failover, idempotent producer sequences, minISR and reconciliation.
3. **Consumption/scale:** group coordinator/generations/cooperative rebalance, quotas,
   compaction, schema registry, transactions, delayed/DLQ or separate lease queue.
4. **Hardening:** tiered storage, broker balancing, regional DR, security/governance,
   model/property/fuzz/load/chaos tests, scrub/restore drills, runbooks, and SLOs.

## 24. Final design

Make each partition a single-leader append-only offset log. The leader validates an
epoch-fenced producer sequence, assigns offsets, replicates and acknowledges only after
the configured in-sync durability boundary; consumers see the committed high-watermark
prefix. Group generations give each partition one active owner and fence zombie commits,
while processing-then-commit deliberately yields at-least-once delivery. Immutable
segments, idempotent sequences, consensus metadata, safe leader-tail reconciliation,
bounded retention/compaction/tiering and explicit transactional/visibility semantics
form a queue that remains honest and recoverable across every retry and failure.
