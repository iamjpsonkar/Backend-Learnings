# Complete Solution: Distributed Task Scheduler

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Schedule one-time and recurring jobs, cancel/pause/resume them, prioritize work,
retry failures, enforce deadlines, expose execution history, and recover from
scanner/worker crashes. Delivery is at least once; business effects must be
idempotent. Exactly-once execution across process and external-service failure is
not promised.

Targets: 1 billion stored schedules, 100 thousand executions/second peak, p99
scheduling delay below 2 seconds for the high-precision tier, and no silent missed
runs. Large payloads live outside the scheduling index.

## 2. Capacity estimation

Assume 100K executions/s peak and 2 KB execution metadata:

```text
execution metadata/day = 100K * 86,400 * 2 KB ~= 17.3 TB at sustained peak
```

Actual average should be much lower; execution history needs retention/tiering.
One billion schedules at 1 KB is about 1 TB raw, but indexes and replicas multiply
it. Partition due work by time bucket and hash so no scanner reads all schedules.

## 3. API and states

```text
POST /v1/schedules        {run_at | cron, timezone, payload_ref, policy}
POST /v1/schedules/{id}/pause|resume
DELETE /v1/schedules/{id}
GET  /v1/schedules/{id}
GET  /v1/schedules/{id}/executions?cursor=...
```

```text
Schedule(id, tenant, type, expression, timezone, payload_ref,
         next_run_at, state, version, policy)
Execution(id, schedule_id, occurrence_at, state, priority, attempt,
          lease_owner, lease_epoch, lease_expires_at, result_ref, deadline)
```

Schedule states: `ACTIVE`, `PAUSED`, `CANCELLED`. Execution states: `READY`,
`LEASED`, `SUCCEEDED`, `RETRY_WAIT`, `FAILED`, `CANCELLED`.

`execution_id = hash(schedule_id, occurrence_at)` makes materialization idempotent.

## 4. Architecture

```text
API -> partitioned schedule store + transactional outbox
                         |
time-bucket scanners ----+----> durable priority queues -> workers -> target
     |                                      |               |
lease coordinator                       retry/DLQ       result/history
     |
reconciler -> finds missed due runs, expired leases, stuck executions

payload/result bodies -> object storage
```

Use separate queues and capacity pools for latency-sensitive, normal, and bulk
jobs so a bulk backlog cannot starve critical work.

## 5. Time partitioning

Store an active schedule in the bucket containing `next_run_at`, for example:

```text
bucket_key = UTC minute(next_run_at) + hash(schedule_id) mod 256
```

High-precision schedules may use second buckets; low-cost schedules use minute or
hour buckets. A bucket is leased to one scanner epoch at a time. The scanner reads
only a bounded look-ahead window.

## 6. Step-by-step workflow

### Create

1. Validate time/cron, IANA time zone, payload reference, deadline, retry policy,
   tenant quota, and idempotency key.
2. Compute first occurrence and its bucket.
3. Transactionally insert schedule plus bucket index/outbox.
4. Return schedule only after durable commit.

### Materialize and dispatch

1. Scanner obtains fenced lease for due bucket.
2. It reads active rows with `next_run_at <= lookAheadEnd` in pages.
3. For each occurrence it conditionally creates deterministic execution ID.
4. It publishes execution ID to priority queue through outbox.
5. For recurring schedule, transactionally calculate/store next occurrence and
   move its bucket index.
6. Worker receives ID, leases execution, loads payload, and invokes handler.
7. Success commits terminal result; retryable failure schedules a new ready time;
   permanent/exhausted failure goes to DLQ.

## 7. Core scanner logic

```text
function scanBucket(bucket, lease):
    require lease.valid() and lease.epoch == bucket.currentEpoch

    cursor = bucket.resumeCursor
    while lease.hasSafetyMargin():
        page = scheduleStore.readDue(bucket, cursor, now()+LOOKAHEAD, PAGE_SIZE)
        if page.empty: break

        for schedule in page:
            transaction:
                current = scheduleStore.getForUpdate(schedule.id)
                if current.state != ACTIVE: continue
                if current.nextRunAt != schedule.nextRunAt: continue

                executionId = hash(current.id, current.nextRunAt)
                executions.insertIfAbsent(Execution(
                    id=executionId, scheduleId=current.id,
                    occurrenceAt=current.nextRunAt, state=READY,
                    attempt=0, deadline=deriveDeadline(current)
                ))
                outbox.insertIfAbsent(ExecutionReady(executionId))
                current.nextRunAt = calculateNext(current)
                scheduleStore.moveToBucket(current)

        cursor = page.nextCursor
        bucket.saveCursor(cursor, expectedLeaseEpoch=lease.epoch)
```

If the scanner crashes after commit but before queue publish, the outbox publisher
still sends it. If it crashes before commit, another scanner repeats safely.

## 8. Worker lease logic

```text
function handle(executionId, worker):
    lease = executions.compareAndLease(
        executionId, allowedState in [READY, RETRY_WAIT],
        owner=worker.id, expiresAt=now()+LEASE_TTL)
    if lease not acquired: return

    execution = executions.get(executionId)
    if now() >= execution.deadline:
        executions.fail(executionId, lease.epoch, DEADLINE_EXCEEDED)
        return

    heartbeat = startHeartbeat(executionId, lease.epoch)
    result = invokeHandler(
        payload=objectStore.get(execution.payloadRef),
        idempotencyKey=execution.id,
        deadline=execution.deadline)
    heartbeat.stop()

    if result.success:
        executions.completeIfLease(executionId, lease.epoch, result.ref)
    else if retryable(result) and execution.attempt < policy.maxAttempts:
        next = now() + cappedExponentialBackoff(execution.attempt, jitter=true)
        executions.scheduleRetryIfLease(executionId, lease.epoch, next)
    else:
        executions.failIfLease(executionId, lease.epoch, result.reason)
        dlq.publish(executionId)
```

Lease epoch fences a slow old worker after reassignment. The target handler must
deduplicate `execution.id`; a crash can occur after the side effect but before the
completion record.

## 9. Recurrence and time zones

- Store original cron/rule plus IANA time zone, not only UTC intervals.
- Calculate next occurrence from the rule and previous intended occurrence, not
  worker completion time, so delays do not drift the schedule.
- Define daylight-saving gaps/folds explicitly: skip, run once, or run twice.
- A scheduler outage may use catch-up policy: run every missed occurrence, only
  latest, or skip. Store this policy per schedule.

## 10. Cancellation semantics

Cancelling prevents future materialization and queued executions not yet leased.
It cannot guarantee rollback of a handler already running. Cooperative handlers
may poll cancellation token. API must report whether work was prevented, requested
to stop, or had already completed.

## 11. Reconciliation

Continuously scan for:

- due active schedules without deterministic execution row;
- READY execution without published outbox/queue record;
- expired worker leases;
- RETRY_WAIT whose ready time passed;
- LEASED execution beyond deadline;
- schedule whose next bucket/index disagrees with authoritative row.

Repair is idempotent and rate-limited. Reconciliation is a correctness component,
not an optional maintenance script.

## 12. Failure handling

| Failure | Behavior |
| --- | --- |
| Scanner crashes | Bucket lease expires; new epoch resumes cursor/repeats idempotently |
| Worker crashes before effect | Lease expires and execution redelivers |
| Worker crashes after effect | Redelivery occurs; handler idempotency prevents duplicate business effect |
| Queue unavailable | Outbox retains ready event and publisher retries |
| Schedule DB unavailable | Creation/scanning pauses; queued leased work continues within policy |
| Clock skew | Server/database time controls due comparisons and leases |
| Huge backlog | Priority isolation, admission, catch-up policy, and autoscaling |
| Poison task | Bounded attempts then DLQ with replay after correction |

## 13. Security

- Tenant-scoped auth, quotas, allowed handler types/destinations, and payload limits.
- Payload references use short-lived credentials; secrets are resolved at runtime,
  not embedded in schedule records.
- Prevent arbitrary internal URL invocation/SSRF with destination allowlists.
- Encrypt data, audit create/change/cancel/replay, and redact payloads from logs.
- DLQ replay requires explicit privileged action and a new audit event.

## 14. Observability

Measure schedule create latency, due-to-enqueue delay, queue age by priority,
start lateness, runtime, success/retry/failure, lease expiry, duplicate attempts,
heartbeat loss, scanner bucket lag, outbox backlog, reconciliation repairs, DLQ
size/age, deadline misses, and tenant saturation.

Test scanner/worker death at every boundary, queue outage, delayed outbox,
time-zone DST changes, clock skew, backlog recovery, cancellation races, and
side-effect-before-ACK duplicates.

## 15. Implementation path

1. **MVP:** SQL schedules/executions, one scanner with lock, durable queue,
   idempotent worker, one-time tasks, and basic retries.
2. **Correct recovery:** transactional outbox, worker leases/epochs, deterministic
   execution IDs, reconciler, DLQ, deadlines, and cancellation semantics.
3. **Scale:** time/hash buckets, scanner leases, priority pools, payload storage,
   pagination, tenant quotas, and history tiering.
4. **Advanced scheduling:** recurring rules/time zones, precision tiers, catch-up
   policies, regional placement, chaos tests, and recovery drills.

## 16. Final design

Use a partitioned time-bucket schedule store, fenced scanners, deterministic
execution IDs, transactional outbox, durable priority queues, and leased workers.
The core guarantee is at-least-once execution with no silently missed due record;
idempotency keys and fencing convert duplicate delivery into exactly-once business
effects where the handler supports it.
