# Stream-Processing Engine

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Run partitioned stateful operators with windows, joins, event-time watermarks, checkpoints, and replay.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Job graph of sources/operators/sinks; keyed state and timers; checkpoint metadata maps input offsets to state snapshots.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
sources -> partitioned operators -> shuffle -> stateful operators -> sinks; coordinator -> barriers/checkpoints
```

Co-locate keyed state, use incremental snapshots, propagate backpressure, rescale with savepoints, and advance watermarks using bounded lateness/idleness.

## Failure, security, and observability

Restore state and source offsets atomically, use transactional/idempotent sinks, isolate bad records, and monitor lag, watermark delay, checkpoint duration/failure, and state size.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Exactly-once state adds checkpoint and sink coordination; at-least-once is faster and adequate when outputs are idempotent.
