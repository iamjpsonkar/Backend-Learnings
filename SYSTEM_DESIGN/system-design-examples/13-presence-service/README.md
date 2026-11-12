# Presence Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Expose online, idle, and last-seen state across devices using best-effort freshness rather than durable truth.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

Clients heartbeat sessions; authorized subscribers watch users or groups; last-seen reads are rate-limited and privacy-aware.

Session(user, device, connection, region, last_heartbeat, expires_at); aggregate presence is derived from active sessions.

## High-level design

```text
client -> regional gateway -> presence shard -> pub/sub -> authorized subscribers
```

Store expiring sessions in memory, shard by user, aggregate multi-device state, coalesce changes, and sample updates for very large audiences.

## Reliability, security, and operations

Treat presence as soft state, expire without explicit disconnect, suppress flapping, enforce visibility settings, and degrade to unknown during partitions.

Measure heartbeat volume, expiry lag, fan-out, stale sessions, subscription size, and transition latency.

## Key trade-off

Short TTLs improve freshness but cost battery and traffic; longer TTLs are cheaper but overstate online status.
