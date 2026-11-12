# Metrics Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Ingest labeled time series, aggregate, retain, query ranges, render dashboards, and support rules.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Series fingerprint(metric,labels); Sample(series,event_time,value); chunks, inverted label index, downsampled blocks, and retention tiers.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
agents -> distributors -> partitioned ingesters/WAL -> block store; query frontend -> cache/index/store
```

Shard by series hash, batch/compress chunks, reject excessive labels, downsample old samples, split/cache queries, and use recording rules.

## Failure, security, and observability

Replicate ingesters, replay WAL, deduplicate replicas, enforce tenant limits, and monitor active series, samples/sec, out-of-order rejects, query fan-out, and compaction.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

High-cardinality labels aid diagnosis but create unbounded series cost; quotas and pre-aggregation intentionally limit flexibility.
