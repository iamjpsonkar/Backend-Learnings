# Complete Solution: Distributed Unique ID Generator

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Generate globally unique positive 64-bit IDs without a network call per ID. IDs
should be roughly time ordered, sustain 10 million IDs/second globally, work in 32
regions, and remain unique through restarts, clock rollback, and worker failure.

Strict consecutive ordering and gap-free sequences are not required. Consumers
must treat IDs as opaque; embedded fields are for routing and debugging only.

## 2. Capacity estimation

Use 63 payload bits so IDs remain positive signed 64-bit integers:

```text
41 bits timestamp milliseconds since custom epoch = 2^41 ms ~= 69.7 years
 5 bits region ID                                  = 32 regions
 7 bits worker ID                                  = 128 workers/region
10 bits sequence                                   = 1,024 IDs/ms/worker
---------------------------------------------------------------
63 bits total
```

One worker can generate 1.024 million IDs/second. One region can theoretically
generate 131 million/second, leaving ample headroom. Real capacity is lower due to
runtime contention, so benchmark and shard callers across workers.

```text
id = (timestamp_delta << 22) | (region_id << 17) |
     (worker_id << 10) | sequence
```

The custom epoch is immutable once IDs exist. Store it in specification and code,
not dynamic configuration.

## 3. Architecture

```text
                     +---------------------------+
                     | consensus lease registry  |
                     | worker IDs + fencing epoch|
                     +------------+--------------+
                                  | lease/renew only
                                  v
applications -> local ID worker/library -> 64-bit IDs
                                  |
                         clock/sequence checkpoint
```

The hot path is local. A small consensus-backed registry (etcd/ZooKeeper or a
transactional database with leases) allocates `(region, worker)` identities.
Workers contact it only on startup and renewal.

## 4. Lease model

```text
WorkerLease
  region_id
  worker_id
  owner_instance_id
  fencing_epoch
  lease_expires_at
  last_issued_timestamp_ms
```

Allocation is a compare-and-set. Reassignment increments `fencing_epoch`. A worker
must stop generating before its lease expires; a watchdog terminates generation if
renewal cannot complete with a safety margin.

## 5. Step-by-step workflow

1. Instance authenticates to its regional lease registry.
2. Registry conditionally assigns a free worker ID and fencing epoch.
3. Worker loads its durable last timestamp and verifies the system clock.
4. Each request obtains the next `(timestamp, sequence)` under a local lock or
   atomic state update and packs the bits.
5. Worker periodically checkpoints the greatest timestamp it has emitted.
6. Lease renews well before expiry. Failure to renew disables generation.
7. On shutdown, worker persists timestamp, releases lease, and waits through the
   configured reuse quarantine before that worker ID can be reassigned.

## 6. Core generation logic

```text
CUSTOM_EPOCH_MS = timestamp("2026-01-01T00:00:00Z")
MAX_SEQUENCE = 1023
TIMESTAMP_SHIFT = 22
REGION_SHIFT = 17
WORKER_SHIFT = 10

state lastTimestamp = loadCheckpoint()
state sequence = 0

function nextId():
    require lease.isValidWithSafetyMargin()

    atomic section:
        physicalNow = wallClockMilliseconds()

        if physicalNow < lastTimestamp:
            rollback = lastTimestamp - physicalNow
            if rollback <= SMALL_ROLLBACK_LIMIT_MS:
                now = lastTimestamp       // logical time; consume sequence space
            else:
                disableGeneration()
                raise ClockUnsafe(rollback)
        else:
            now = physicalNow

        if now == lastTimestamp:
            if sequence == MAX_SEQUENCE:
                now = waitUntilClockAfter(lastTimestamp)
                sequence = 0
            else:
                sequence = sequence + 1
        else:
            sequence = 0

        delta = now - CUSTOM_EPOCH_MS
        require 0 <= delta < 2^41 else EpochExhausted

        id = (delta << TIMESTAMP_SHIFT) |
             (lease.regionId << REGION_SHIFT) |
             (lease.workerId << WORKER_SHIFT) |
             sequence

        lastTimestamp = now
        maybeCheckpoint(lastTimestamp)
        return id
```

The atomic section must cover timestamp and sequence together. Implement it with a
mutex, a compare-and-swap packed state, or one single-threaded generator loop.
Never generate `sequence = 0` twice for the same worker and millisecond.

## 7. Batch generation

```text
function nextBatch(count):
    require 1 <= count <= MAX_BATCH
    result = []
    repeat count times:
        result.append(nextId())
    return result
```

Optimize only after profiling. A batch may reserve a contiguous sequence range
within one millisecond, but if the process crashes unused IDs become gaps. Gaps are
acceptable; reusing them is not.

## 8. Decoding for operations

```text
function inspect(id):
    sequence = id & 0x3FF
    worker = (id >> 10) & 0x7F
    region = (id >> 17) & 0x1F
    createdAt = ((id >> 22) & ((1 << 41) - 1)) + CUSTOM_EPOCH_MS
    return {createdAt, region, worker, sequence}
```

Expose decoding only as a diagnostic utility. Authorization, tenancy, and business
time must never be inferred from an ID.

## 9. Clock rollback handling

NTP should slew clocks rather than step them, but software must still defend:

- Small rollback: hold logical time at `lastTimestamp` and use remaining sequence.
- Sequence exhausted while clock is behind: block briefly, never wrap.
- Large rollback: stop and alert; move traffic to healthy workers.
- Restart: checkpoint plus lease quarantine prevents a reused worker from emitting
  an old timestamp/sequence pair.
- VM snapshot restore: instance identity changes and must obtain a new lease.

A monotonic clock measures waits but cannot supply a timestamp across restarts, so
both wall clock and persisted safety state are needed.

## 10. Consistency and ordering

- IDs from one worker are strictly increasing.
- IDs across workers are roughly ordered, not totally ordered; clock skew can place
  a later event before an earlier event.
- Database queries requiring business order must use event time plus a tie-breaker
  or an ordered log, not rely solely on ID order.
- Uniqueness comes from unique worker lease plus unique timestamp/sequence pair.

## 11. Failure handling

| Failure | Behavior and recovery |
| --- | --- |
| Lease registry unavailable after startup | Existing worker continues only until safety deadline, then stops |
| Worker crashes | Its lease expires; replacement uses new epoch and quarantine before ID reuse |
| Clock moves backward slightly | Logical timestamp remains at last value; sequence advances |
| Clock moves backward significantly | Worker refuses IDs and is removed from service |
| Sequence exhausts in one millisecond | Wait for next safe millisecond; never wrap |
| Region ID misconfiguration | Registry rejects unallocated/out-of-range identity |
| Epoch nearly exhausted | Years-ahead alert and planned version/ID-width migration |
| Duplicate detected downstream | Page immediately; quarantine worker and preserve evidence |

## 12. Security

- Authenticate lease clients and authorize only their region.
- Keep registry writes audited and require controlled worker-ID overrides.
- Rate-limit batch size to prevent one caller starving shared generator capacity.
- Treat embedded time/region as public information; use UUIDv4 if metadata leakage
  is unacceptable.
- Do not expose an endpoint publicly when a local library or sidecar is enough.

## 13. Observability

Measure IDs/second, generation p99, sequence utilization, waits for next
millisecond, clock offset/rollback, lease age and renewal failures, active worker
IDs, checkpoint failures, batch sizes, and any downstream uniqueness violation.

Continuously test uniqueness by sampling generated IDs into a set across workers.
Before launch, simulate clock steps, registry partitions, process pauses, snapshot
restore, lease expiry, worker reassignment, and maximum sequence pressure.

## 14. Implementation path

1. **Simplest correct choice:** use database sequences or UUIDv7 if they meet
   throughput, size, privacy, and index requirements.
2. **Single-region generator:** fixed worker IDs, local algorithm, clock monitoring,
   checkpoints, and collision tests.
3. **Safe dynamic fleet:** consensus leases, fencing, renewal watchdog, quarantine,
   and automated allocation.
4. **Global deployment:** region IDs, independent regional registries, epoch
   monitoring, capacity/load tests, and documented consumer semantics.

## 15. Alternatives

| Option | Strength | Cost |
| --- | --- | --- |
| Database sequence | Simple, strictly ordered | Central dependency and throughput ceiling |
| UUIDv4 | No coordination, private randomness | 128 bits, random index locality |
| UUIDv7 | No coordination, time ordered | 128 bits and not compact numeric |
| Range allocation | Fast local counters | Wasted ranges and allocator dependency |
| Snowflake-style chosen design | Compact, sortable, high throughput | Clock and worker-lease complexity |

The core invariant is that no two live or recently restarted generators may use
the same `(region, worker, timestamp, sequence)` tuple. The lease, clock rules,
atomic local state, checkpoint, and quarantine all exist to preserve that invariant.
