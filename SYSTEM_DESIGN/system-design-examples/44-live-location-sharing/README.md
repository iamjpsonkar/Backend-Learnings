# Live Location Sharing

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Share a user's position with an authorized set for a bounded session while controlling freshness and battery use.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

ShareSession(id,owner,viewers,expires,precision); Position(session,sequence,lat,lng,accuracy,time), with only short retention.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
mobile -> regional ingest -> session shard/latest store -> pub/sub -> authorized viewers
```

Adapt update frequency to movement/battery, coalesce points, shard by session/owner, use latest-value storage, and send deltas over persistent connections.

## Failure, security, and observability

Expire sessions and viewer tokens, reject replayed sequences, degrade to last-known with age, and monitor ingest/fan-out latency, stale positions, battery/network usage, and unauthorized attempts.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Higher frequency improves freshness but consumes battery, bandwidth, and privacy budget; adaptive sampling is usually preferable.
