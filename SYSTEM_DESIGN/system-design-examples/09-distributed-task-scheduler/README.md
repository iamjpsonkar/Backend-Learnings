# Distributed Task Scheduler

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Run one-time and recurring jobs with priorities, retries, deadlines, and bounded duplicate execution.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

Create/cancel/query schedules; workers lease ready executions, heartbeat, and report completion using an attempt token.

Schedule(id, expression, payload_ref, next_run, state); Execution(id, schedule_id, due_at, attempt, lease_owner, lease_expiry, status).

## High-level design

```text
API -> schedule store -> time-bucket scanner -> ready queue -> workers -> result store
```

Partition schedules by due-time bucket and hash, enqueue ahead within a look-ahead window, use priority queues, and keep payloads outside hot indexes.

## Reliability, security, and operations

Lease executions with fencing tokens, make handlers idempotent, retry with capped exponential backoff, dead-letter exhausted tasks, and reconcile missing runs.

Measure scheduling delay, queue age, runtime, retries, expired leases, duplicate completions, dead letters, and worker saturation.

## Key trade-off

Exactly-once execution is impractical across crashes; at-least-once dispatch plus idempotent effects is simpler and recoverable.
