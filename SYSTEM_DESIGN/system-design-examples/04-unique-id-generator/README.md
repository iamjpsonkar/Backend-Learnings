# Unique ID Generator

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Generate collision-free, roughly time-sortable IDs across regions and workers at high throughput.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

Clients request one ID or a bounded batch; the service exposes timestamp extraction for debugging but no mutable state.

ID bits contain time, region, worker, and sequence. Store worker leases with owner, epoch, and expiration in a consensus store.

## High-level design

```text
client -> local ID worker -> clock/sequence; worker -> lease service only on startup or renewal
```

Allocate worker IDs through leases and increment a per-millisecond sequence. Pause or move to a logical clock if physical time moves backward.

## Reliability, security, and operations

Fence expired workers with lease epochs, alert on clock drift, and refuse generation before sequence wrap would cause duplication.

Track IDs/second, clock rollback, sequence exhaustion, lease renewal latency, and duplicate detection in sampled downstream writes.

## Key trade-off

More timestamp bits extend lifetime; more worker/sequence bits increase concurrency. Random UUIDs remove coordination but are larger and less index-friendly.
