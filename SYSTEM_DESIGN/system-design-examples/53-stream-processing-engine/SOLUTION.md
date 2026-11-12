# Complete Solution: Stream-Processing Engine

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Compile a logical streaming job into parallel source, map/filter, key-by shuffle,
window/aggregate/join, timer and sink tasks. Support processing/event time, watermarks,
late data, durable keyed/operator/broadcast state, periodic consistent checkpoints,
failure replay, savepoints/upgrades/rescaling, backpressure, schemas/UDFs and tenant
resource isolation.

Targets: ten million events/s at 1 KB, seconds/subsecond end-to-end latency by job,
99.99% control-plane availability and automatic recovery within minutes. Exactly-once
means each input affects managed operator state and a compatible transactional/idempotent
sink once after recovery. It does not make arbitrary HTTP/email/database effects exactly
once. Jobs can explicitly choose at-least-once for lower checkpoint cost.

## 2. Capacity estimation

Ten million events/s creates 10 GB/s source ingress. A full repartition adds roughly
10 GB/s shuffle send and receive before protocol/compression; multiple shuffles multiply it.

- With 60-second checkpoints and 10 TB keyed state, full snapshots are infeasible;
  incremental changed-state uploads and local recovery are mandatory.
- At 1% state churn/s, checkpoint change rate can be 100 GB/s before compaction/dedupe;
  state schema/TTL and checkpoint interval matter greatly.
- A 30-second outage/recovery may create 300 million events of replay/backlog.
- Key skew can send a large fraction of traffic/state to one task despite ample total
  capacity; hot-key detection and domain-specific splitting/partial aggregation matter.
- Separate shuffle, state/checkpoint object-store and source/sink bandwidth budgets so
  checkpoints do not collapse live processing.

## 3. Job API and semantics

```text
POST /v1/jobs                            {graph, resources, checkpointing} Idempotency-Key
GET  /v1/jobs/{id}
POST /v1/jobs/{id}:cancel
POST /v1/jobs/{id}:savepoint             {target, drain}
POST /v1/jobs/{id}:rescale               {parallelism, savepoint}
POST /v1/jobs/{id}:upgrade               {artifact, stateMapping, savepoint}
GET  /v1/jobs/{id}/checkpoints?cursor=
GET  /v1/jobs/{id}/metrics
```

Logical DSL defines source offsets, schemas, event-time extractor, keys, windows,
triggers, allowed lateness/output changelog mode, state TTL, joins, sink guarantees and
UDF artifact/version. Validate DAG, serializers, resource ceilings and connector
capabilities before deployment.

## 4. Execution and metadata model

```text
Job(id, tenant, graph_version, state, guarantee, restart_policy, config_version)
Operator(id, job_id, uid, type, parallelism, max_parallelism,
         input_schemas, output_schema, state_descriptors, code_version)
Task(job_id, operator_uid, subtask, attempt_epoch, worker, state)
Edge(source_operator, target_operator, partitioner, buffer_config)
KeyGroup(id, max_parallelism, assigned_subtask)
Checkpoint(id, job_id, graph_version, status, trigger_time,
           source_offsets, operator_handles, channel_state_handles,
           sink_transactions, completed_at, checksum)
Savepoint(id, job_id, operator_uid_mapping, state_handles, source_offsets, manifest)
JobMasterLease(job_id, epoch, leader, expires_at)
```

Stable operator UIDs and state names are part of upgrade contract. Attempts/epochs fence
old workers/sinks after restart. Checkpoint metadata is small consensus/HA state;
bulk snapshots are immutable checksummed object-store files.

## 5. Architecture

```text
client -> API/compiler/optimizer -> HA job coordinator/resource scheduler
                                         |                 |
                                   task assignments    checkpoint coordinator
                                         |
source tasks -> operator chains -> network shuffle -> keyed/window/join tasks -> sinks
                    |                              |
               local buffers               embedded state backend/timers
                                                   |
                                      incremental checkpoint object store

workers -> heartbeat/metrics/logs; artifact/schema/secret registries
```

Cluster manager allocates CPU/memory/network/disk slots. Job coordinator owns graph,
attempt epochs, checkpoint decisions and recovery. Task data plane continues briefly
through coordinator failover but accepts commands only from current fenced epoch.

## 6. Step-by-step workflow

1. Compiler type-checks graph/schemas/state, assigns stable operator UIDs/key-group
   max parallelism, chains compatible local operators, inserts shuffle/exchange and
   chooses resources/checkpoint mode.
2. Scheduler places tasks across workers/zones with slots, source locality, state size
   and anti-affinity; distributes signed code/config/secrets and attempt epochs.
3. Sources read assigned partitions, attach event timestamps/watermarks, and emit
   records into operator chains. Key-by hashes serialized key to fixed key group and
   routes to owning downstream subtask.
4. Stateful tasks process one keyed mailbox/order stream, update local durable state,
   register event/processing timers, emit records/retractions/upserts and propagate
   watermarks/backpressure.
5. Coordinator injects checkpoint barrier at all sources. Barriers flow with records;
   tasks snapshot state/input/channel position and prepare transactional sinks.
6. After every task ACK/checksum, coordinator atomically marks checkpoint complete and
   notifies sinks to commit. Sources may then expose offsets for retention.
7. Failure cancels/fences affected attempt, restores all job tasks from latest completed
   checkpoint, resets sources/sinks, and replays deterministically.

## 7. Key partitioning and operator loop

```text
keyGroup = positiveHash(serializeKey(record.key)) % operator.maxParallelism
targetSubtask = floor(keyGroup * currentParallelism / operator.maxParallelism)
```

Fixed max parallelism lets rescaling move key groups without rehashing keys.

```text
function processRecord(record, input):
    verify schema and deserialize with configured version
    currentInputWatermark[input] is unchanged by data record
    keyContext.set(record.key)
    stateBackend.beginMailboxStep(keyGroup(record.key))
    outputs = operator.onRecord(record, keyedState, timerService)
    stateBackend.commitMailboxStep()
    for output in outputs: emitWithTimestamp(output)

function onTimer(timer):
    keyContext.set(timer.key)
    operator.onTimer(timer.timestamp, timer.domain, keyedState, emit)
```

One task processes mailbox actions serially, avoiding user-state locks. Async I/O uses
bounded futures and ordered/unordered completion semantics declared by operator; barrier
handling must include or drain pending async requests correctly.

## 8. Watermarks and idleness

A source partition estimates watermark, for example:

```text
partitionWatermark = maxObservedEventTime - allowedOutOfOrderness
operatorWatermark = min(nonIdleInputPartitionWatermarks)
```

Watermark asserts no normal event with timestamp <= watermark is expected; it is a
policy, not fact. Mark partition idle only after configured silence and source evidence,
so an empty partition does not hold all windows forever. On resumption, its watermark
cannot regress global watermark; late events follow allowed-lateness policy.

Multi-input operator output watermark is minimum of inputs after alignment/idleness.
Watermark alignment can pause faster sources so their state does not grow unbounded
while a slow input lags.

## 9. Windowing and late updates

Tumbling `[floor(t/S)*S, +S)`, sliding windows, sessions merged by inactivity gap and
global/custom assigners are supported. State key is `(user key, window namespace)`.

```text
function onWindowRecord(record):
    windows = assigner.assign(record.eventTime)
    for window in windows:
        accumulator[record.key, window].add(record)
        registerEventTimer(window.end)
        registerCleanupTimer(window.end + allowedLateness)

on event-time timer at window.end:
    emit INSERT/UPSERT(windowResult, version++)

if late record arrives before cleanup:
    update accumulator and emit UPDATE_BEFORE/UPDATE_AFTER or UPSERT
else:
    send to late side output/drop with metric per policy

on cleanup timer: delete window state/timers
```

Sink must understand append versus update/retraction changelog. Session-window merge
merges accumulators/timers and retracts superseded results if emitted early. State TTL
must not delete before watermark + allowed lateness.

## 10. Stream joins

Interval join buffers keyed left/right records until opposite watermark proves no more
matches within bounds. For `left.time + lower <= right.time <= left.time + upper`,
retain each side through its matching horizon plus lateness, emit each pair with stable
identity and clean via event-time timer. Outer joins delay unmatched output until
watermark proves absence, then late correction requires changelog semantics.

Stream-table join uses versioned/changelog table keyed state and defines processing-
time latest versus temporal event-time/as-of semantics. Unbounded join without time/
TTL constraint is rejected or requires explicit infinite state budget.

## 11. State backend

Small state can be heap-based; large state uses embedded LSM/ordered KV with write
buffers, SSTables, block cache and local SSD. Namespace keys by job/operator/key-group/
state/window. Serializer snapshots carry schema/version. TTL cleanup uses incremental
scan/compaction and remains semantically compatible with event-time rules.

Incremental checkpoint references immutable SSTables already uploaded and only adds
new files/metadata; shared-file reference counting prevents premature deletion. Local
recovery retains prior checkpoint files on worker/nearby replica to avoid downloading
terabytes, while object store is durable source. Encrypt/checksum state and compact
without blocking mailbox excessively.

## 12. Aligned checkpoint algorithm

```text
onBarrier(input, checkpointId):
    block input from delivering post-barrier records
    mark input barrier received
    if barriers received from all inputs:
        snapshot operator/keyed/timer state asynchronously
        snapshot source offsets or prepare sink transaction
        forward barrier to outputs
        unblock all inputs and drain buffered records in order
        ACK coordinator with state/sink handles and attemptEpoch

coordinator:
    inject barrier into all sources
    wait for current-epoch ACK from every task before timeout
    atomically persist COMPLETED checkpoint manifest
    notify all prepared sinks COMMIT(checkpointId)
```

Records before barrier are in snapshot; records after are not. Backpressure/skew can
make alignment buffers huge. Checkpoint upload is asynchronous but local state snapshot
must provide a consistent immutable view (copy-on-write/LSM snapshot).

## 13. Unaligned checkpoints

When alignment stalls, record input/output channel buffers and inflight data as part of
checkpoint, forward barrier immediately and snapshot state. This reduces checkpoint
duration under backpressure but increases snapshot size/recovery replay complexity and
requires deterministic channel-state restoration. Adaptive mode switches based on
alignment time/bytes. It does not fix permanently undersized jobs; autoscale/backpressure
remediation remains necessary.

## 14. Source and sink exactly-once

Replayable sources checkpoint partition offsets with operator state and seek to them on
restore. Nonreplayable sources cannot provide full exactly-once unless engine durably
logs input first.

Transactional sink uses two-phase checkpoint protocol:

```text
begin transaction T(checkpoint interval)
write outputs to T
on barrier: preCommit T and store transaction handle in task checkpoint; begin next T
after global checkpoint COMPLETE: commit T idempotently
on abort/failure: abort uncommitted T; restored task resumes from completed handles
```

Sink coordinator fences old attempt epoch and handles coordinator crash by querying
transaction status. Alternatively idempotent upsert key `(job, operator, source identity,
window/version)` tolerates repeats. Arbitrary side effects inside UDF are forbidden or
documented at-least-once.

## 15. Failure recovery

```text
onTaskFailure(task, cause):
    jobMasterEpoch remains/current leader fences failed attempt
    choose latest checkpoint with complete manifest and compatible graph
    cancel job tasks/sink open transactions under old attempt epoch
    allocate new attempts
    download/local-link each assigned key-group state and timers
    restore source offsets and channel state
    start tasks behind coordination gate, then resume all
```

All tasks normally restart together for exactly-once consistent cut; region/local
recovery optimizations must preserve dependencies. Exponential restart budget avoids
poison crash loops. Bad records can go to bounded side output with evidence; silently
skipping them changes semantics and must be configured/audited.

## 16. Savepoints, upgrades, and rescaling

Savepoint is user-retained portable consistent snapshot with stable operator UID/state
mapping. Optionally drain sources/watermarks first. Upgrade validates new artifact
signature, serializers/state compatibility and topology mapping; removed state needs
explicit allow-discard. Restore to canary/shadow where possible.

Rescale assigns fixed key groups to new subtasks, reads only their state handles and
restores timers; operator/list/broadcast state has redistribution strategies. Source
partitions and sink transactions rebalance at same savepoint/checkpoint boundary.
Online rescaling can reduce pause but is far more complex; start with stop-savepoint-
restore and measure downtime/state bandwidth.

## 17. Backpressure and skew

Bounded network buffers/credits cause a slow sink/operator to stop upstream emission,
propagating to sources. Sources pause partitions instead of buffering infinitely.
Dashboard shows busy/backpressured/idle time and buffer occupancy per edge/task.

Autoscale based on input/output rate, utilization, lag, watermark, state/checkpoint and
predicted catch-up. Hot key cannot be solved by adding subtasks if it remains one key:
use two-stage combinable preaggregation with salted partial keys then final key, domain
subkeys or dedicated hot-key operator, preserving semantics. Async sink batching and
capacity limits prevent downstream overload.

## 18. Scheduling and tenant isolation

Slots have CPU/heap/managed-memory/SSD/network; place task chains for locality, shuffle
anti-affinity and zone resilience. Stateful tasks prefer local recovery but replicas/
checkpoints span failure domains. Tenant/job quotas cover resources, events/bytes,
state, timers, checkpoint bandwidth/object bytes, artifacts and restarts. Separate
checkpoint traffic pool and fair scheduling avoid one huge job starving all.

## 19. Schema, UDF, and determinism

Schema registry enforces source/sink compatibility; serializers store snapshot/version
and migrations. UDF artifacts are signed/scanned, isolated classloader/process/container,
resource-limited and denied ambient credentials/network/filesystem unless declared.

Exactly-once replay requires deterministic logic for a fixed input/state: use engine
clock/timers, seeded randomness in state and versioned external dimension snapshots or
async lookup results checkpointed/idempotent. Calling `now()`/random/live HTTP inside
UDF makes replay differ and must be controlled. Side inputs/broadcast config carry
effective version and checkpoint state.

## 20. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Worker/task crashes | Fence attempt, restore complete checkpoint, replay source |
| Coordinator crashes | HA leader restores metadata/epoch; rejects old command/ACK |
| Checkpoint upload partly fails | Mark failed and retain previous complete snapshot |
| Barrier alignment stalls | Timeout/adaptive unaligned; diagnose backpressure |
| Transactional sink commit reply lost | Query/idempotently commit same checkpoint transaction |
| One source partition idle | Mark idle under policy so watermark advances safely |
| Late event after cleanup | Side output/drop/correction per explicit policy |
| Rescale state transfer fails | Original savepoint/checkpoint remains; retry/rollback |
| Poison event crashes UDF | Restart budget then quarantine/fail job per configured semantics |

## 21. Security and governance

Use OAuth/mTLS service identities, tenant/job/source/sink/savepoint/artifact ACLs, secret
vault injection with rotation, encrypted shuffle/state/checkpoints, signed artifacts,
network egress policies and tamper-evident config/deploy/savepoint/data-access audit.
Prevent cross-tenant state/checkpoint reads, malicious UDF escape, connector SSRF,
deserialization/decompression bombs, schema abuse, secret logging, checkpoint path
traversal, resource exhaustion and unsafe admin restore.

Apply source data classification, field masking, retention/deletion/legal hold/residency
through state, checkpoints, savepoints, DLQ/side outputs, logs and sinks. State deletion
must include shared incremental files only after no manifest references them.

## 22. Observability

Track event/byte input/output, end-to-end/processing latency, source/consumer lag,
watermark and event-time delay/idleness/late rate, task busy/backpressured/idle, mailbox/
buffer/shuffle throughput, records per key/skew, state/timer/window size/TTL cleanup,
checkpoint trigger/alignment/snapshot/upload/total duration/bytes/failure/age, local vs
remote recovery time/bytes, restart/failure loops, sink transaction age/commit/abort,
savepoint/rescale/upgrade, resource/quota and correctness counters/retractions.

Operator test harness feeds deterministic events/watermarks/timers and verifies state/
changelog. Property-test duplicates/replay/checkpoint crash points and compare exactly-
once compatible sink. State-migration golden tests restore old savepoints. Load-test
skew/backpressure/checkpoint storms; chaos workers/coordinator/network/object/sinks and
regularly restore sampled checkpoints/savepoints to independent clusters.

## 23. Implementation path

1. **MVP:** stateless DAG/tasks, partitioned source/shuffle/sink, bounded buffers,
   job coordinator/restarts and at-least-once replay.
2. **State/time:** key groups, embedded keyed state/timers, event-time/watermarks,
   windows/late data/joins, aligned checkpoints and complete recovery.
3. **Exactly-once/scale:** incremental/unaligned checkpoints, transactional/idempotent
   sinks, HA coordinator, savepoints/rescaling/upgrades, local recovery/autoscaling.
4. **Hardening:** UDF sandbox/schema/security/governance, property/migration/skew/load/
   chaos tests, checkpoint/restore drills, runbooks, dashboards, and SLOs.

## 24. Final design

Compile a typed DAG into partitioned epoch-fenced tasks whose fixed key groups own
local state and event-time timers. Watermarks close bounded windows and explicit
allowed-lateness/changelog rules handle late corrections. Barriers establish one
consistent cut across replayable source offsets, operator/timer/channel state and
prepared sink transactions; only a globally completed checkpoint commits output.
Failure restores that cut and replays, while savepoints redistribute key groups for
upgrades/rescaling. Bounded buffers propagate backpressure, incremental snapshots make
large state practical, and explicit sink/UDF boundaries keep “exactly once” truthful.
