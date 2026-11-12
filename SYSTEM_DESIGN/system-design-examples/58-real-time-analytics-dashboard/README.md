# Real-Time Analytics Dashboard

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Ingest events, aggregate dimensions/windows, query fresh results, correct late data, and serve dashboards.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Immutable Event(id,tenant,event_time,dimensions,measures); materialized Cube(window,dimensions,aggregates,version); raw archive.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
events -> durable log -> stream aggregates -> real-time store; batch correction -> merged historical store -> query/cache
```

Partition by tenant/key, pre-aggregate common dimensions, use approximate sketches for cardinality/quantiles, roll up old windows, and cache dashboard queries.

## Failure, security, and observability

Deduplicate IDs, watermark late data, replay to rebuild, enforce dimension quotas, and monitor freshness, correction volume, query latency, and estimate error.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Pre-aggregation gives fast cheap queries but fixes dimensions early; raw scans stay flexible but cost more and respond slower.
