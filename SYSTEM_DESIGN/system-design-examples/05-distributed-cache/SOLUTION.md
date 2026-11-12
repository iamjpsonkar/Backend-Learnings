# Complete Solution: Distributed Cache

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Provide `GET`, `SET`, `DELETE`, TTL, compare-and-set, and optional multi-get for
small opaque values. Scale horizontally, survive a node/zone failure, rebalance
without a fleet-wide miss storm, and keep p99 reads below 5 ms inside a region.

The cache is not the authoritative database. Losing an entry is a miss, not data
loss. Cross-key transactions, arbitrary queries, and permanent durability are out
of scope.

## 2. Capacity estimation

Assume 20 TB usable values, 5 million operations/second, 80% reads, 1 KB average
value, replication factor 2, and nodes with 128 GB RAM operated below 70%.

```text
usable/node             = 128 GB * 0.70              ~= 90 GB
copies stored           = 20 TB * 2                  = 40 TB
minimum data nodes      = 40 TB / 90 GB              ~= 456
provisioned nodes       = 600+ for skew/failure/growth
read payload bandwidth  = 4M/s * 1 KB                ~= 4 GB/s
write payload bandwidth = 1M/s * 1 KB * 2 replicas   ~= 2 GB/s
```

Protocol overhead and network copies increase those numbers. Benchmark memory
overhead per entry: small keys/values may spend more RAM on metadata than payload.

## 3. API and semantics

```text
get(key) -> {found, value, version, expires_at}
set(key, value, ttl, mode=UPSERT) -> {version}
compareAndSet(key, expected_version, value, ttl) -> {changed, version}
delete(key, expected_version?) -> {deleted, version}
multiGet(keys[<=100]) -> result per key
```

- Maximum key: 512 bytes; maximum value: 1 MB initially.
- TTL is relative at the API but stored as an absolute server timestamp.
- A successful primary write gives read-your-write when reading that primary.
- Replica reads may be stale within a documented bound.
- Versions are monotonically increasing within one key ownership epoch.

## 4. Data and metadata

```text
Entry
  key bytes
  value bytes | tombstone
  version = (ownership_epoch, primary_counter)
  expires_at_ms | none
  checksum
  size_bytes
  access/admission metadata
```

```text
RingSnapshot
  epoch
  virtual_token -> {primary_node, replica_nodes}
  node address, zone, state, weight
```

Every request carries the ring epoch. Nodes reject writes from epochs older than
their current ownership, fencing a former primary after a partition or rebalance.

## 5. Architecture

```text
clients -> routing proxies (or smart client) -> primary cache node
                                      |             |
                                      |             +-> replica node(s)
                                      |
control plane -> consensus membership/ring snapshots

optional: mutation log/object snapshot for warm restart, never correctness source
```

Use consistent hashing with many virtual nodes so one physical node owns many
small token ranges. Zone-aware placement keeps replicas off the primary's zone.
Routing proxies simplify clients and hide migrations; smart clients remove a hop
but make rollout and stale topology handling harder. This design chooses proxies.

## 6. Step-by-step workflow

### GET

1. Proxy hashes the binary key and selects its token range from one ring snapshot.
2. It sends the request to the primary, or a local replica when stale reads are
   explicitly allowed.
3. Node locates entry in its hash table.
4. Missing entry returns miss. Expired entry is atomically unlinked and returns
   miss; cleanup never depends solely on a background timer.
5. Valid entry updates approximate access metadata and returns value/version.

### SET

1. Proxy validates size/TTL and routes to current primary with ring epoch.
2. Primary rejects stale epoch or non-owned key with a topology hint.
3. Primary allocates next key version and applies admission/eviction if needed.
4. It sends versioned mutation to replicas.
5. For normal cache mode, acknowledge after primary memory plus one replica; a
   low-latency mode may acknowledge primary only and document weaker survival.
6. Replica applies only a version newer than its current value.

### DELETE

1. Primary creates a versioned tombstone rather than immediately forgetting the
   key.
2. Tombstone replicates and remains through the maximum replication/rebalance
   delay, preventing an old replica from resurrecting a deleted value.
3. After the safety window, all copies may physically remove it.

## 7. Core node logic

```text
function get(key, now, requestEpoch):
    require ownsForRead(key, requestEpoch) else Moved(currentOwner)
    entry = table.lookup(key)
    if entry missing or entry.tombstone:
        return Miss
    if entry.expiresAt exists and now >= entry.expiresAt:
        if table.compareAndRemove(key, entry.version):
            expirationMetrics.increment()
        return Miss
    accessPolicy.recordApproximate(key)
    return Hit(copy(entry.value), entry.version, entry.expiresAt)

function set(key, value, ttl, requestEpoch, expectedVersion=ANY):
    require requestEpoch == ring.epoch
    require isPrimary(key, self)
    require size(value) <= MAX_VALUE

    lock stripeFor(key):
        current = table.lookup(key)
        if expectedVersion != ANY and current.version != expectedVersion:
            return CompareFailed(current?.version)

        ensureCapacityFor(key, value)
        version = (ring.epoch, nextLocalCounter())
        entry = Entry(value, version, deadline(ttl), checksum(value))
        table.replace(key, entry)

    replicaAcks = replicate(key, entry, deadline=request.deadline)
    if replicaAcks < configuredWriteAcks:
        // Entry may exist; return an explicit unknown outcome, not a false failure.
        return WriteOutcomeUnknown(version)
    return Stored(version)

function applyReplica(key, incoming):
    table.compute(key, current ->
        incoming.version > current?.version ? incoming : current)
```

The `unknown` write outcome requires callers to retry with compare-and-set or read
the version. Blindly reporting failure can cause a later retry to overwrite newer
data.

## 8. Eviction and admission

Pure LRU lets a one-time scan evict the useful working set. Use TinyLFU-style
frequency admission plus segmented LRU:

1. A small window admits recent entries.
2. Frequency sketch estimates whether a candidate is more valuable than the
   probation victim.
3. Frequently reused entries graduate to protected segment.
4. Evict until both byte and item-count limits are satisfied.

Eviction operates by bytes, not only item count. Run it before crossing the hard
memory limit so allocator fragmentation and replication buffers have headroom.

## 9. Expiration

- Lazy expiration on reads is the correctness path.
- A hierarchical timing wheel schedules known expirations efficiently.
- Background sampling removes expired cold keys that are never read.
- TTL jitter is a client/library option for computed caches; the service preserves
  the exact TTL requested by callers unless policy says otherwise.

## 10. Rebalancing

When adding node N:

1. Control plane publishes epoch E+1 with N in `JOINING` state.
2. Old owners stream snapshot of only token ranges moving to N.
3. Concurrent mutations are dual-written or appended to a per-range delta log.
4. N applies snapshot then deltas and reports caught-up watermark.
5. Control plane marks N primary for those ranges and publishes E+2.
6. Proxies move traffic gradually; old owners forward/reject stale requests.
7. After grace period, old copies are deleted.

Rate-limit migration and cap concurrent ranges so rebalance cannot consume all
network/disk/CPU. Never remap the whole key space at once.

## 11. Hot keys and stampedes

- Replicate extremely hot immutable keys to additional read replicas.
- Add a tiny in-process proxy cache for the hottest values.
- Use request coalescing (`single-flight`) when a missing value is loaded from an
  authoritative backend by callers.
- Use soft TTL plus stale-while-revalidate only when caller semantics permit it.
- Apply per-key bandwidth limits so a single 1 MB value cannot monopolize egress.

The cache service cannot prevent a database stampede by itself when clients all
observe a miss; provide coalescing primitives or a cache-aside client library.

## 12. Failure handling

| Failure | Behavior |
| --- | --- |
| Primary process fails | Control plane promotes caught-up replica with new epoch; stale primary is fenced |
| Replica fails | Continue at reduced redundancy; replace and stream its ranges |
| Zone fails | Zone-aware replicas serve/promote; shed load if surviving capacity is unsafe |
| Proxy has stale ring | Node returns `MOVED` with newer epoch; proxy refreshes and retries once |
| Network partition | Only epoch-authorized side accepts writes; other side rejects or serves explicitly stale reads |
| Memory full | Admission/eviction runs; reject oversized/unadmittable writes before OOM |
| Rebalance interrupted | Resume from range watermark; old owner remains until cutover committed |
| Warm-recovery log unavailable | Start empty and refill from traffic; cache correctness remains intact |

## 13. Security

- Mutual TLS between clients, proxies, and nodes; tenant-scoped authorization.
- Per-tenant byte, QPS, connection, and item-size quotas.
- Hash or encrypt sensitive keys; encrypt values when threat model requires it.
- Never expose administrative flush/ring operations on the data port.
- Redact keys/values from ordinary logs and debug dumps.
- Validate compression ratios to avoid decompression bombs.

## 14. Observability

Measure hit/miss/negative/expired rates, p50/p99 by operation, item/byte occupancy,
admission and eviction, hot keys, replica lag and write ACKs, stale-epoch requests,
MOVED retries, ring age, migration throughput, memory fragmentation, network
bandwidth, connection pressure, and per-tenant quota rejection.

Test node/zone loss, stale proxies, split brain, OOM pressure, sequence/version
ordering, interrupted rebalance, hot keys, stampedes, TTL waves, and cold restart.

## 15. Implementation path

1. **MVP:** one node, hash table, TTL, byte-based eviction, metrics, and strict
   memory bounds.
2. **Sharding:** routing proxy, consistent-hash virtual nodes, membership snapshots,
   client deadlines, and multi-get scatter/gather limits.
3. **Resilience:** zone-aware replicas, versioned mutations/tombstones, epoch
   fencing, promotion, and automated replacement.
4. **Operations:** online rebalance, admission policy, hot-key controls, quotas,
   chaos tests, and optional warm recovery.

## 16. Final design

The selected design is a regional, proxy-routed, consistent-hash cache with
zone-aware replication, epoch fencing, versioned entries/tombstones, lazy plus
active expiration, and frequency-aware admission. The core invariant is that only
the primary for the current ownership epoch may create a new version, and every
replica applies versions monotonically. Because the cache is disposable, safety
prefers a miss or rejected write over serving an ownership-conflicted value.
