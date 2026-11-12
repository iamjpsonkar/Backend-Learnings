# Log Aggregation Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Collect, buffer, parse, index, retain, search, and control high-cardinality application logs.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Raw log envelope(tenant,source,time,body); parsed fields; time-partitioned index segments; archive objects and retention policy.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
agents -> regional buffers/log -> parse/redact -> hot index + object archive -> query broker
```

Batch/compress agents, enforce tenant quotas, separate raw archive from expensive indexes, shard by tenant/time, and tier or sample low-value data.

## Failure, security, and observability

Spool locally during outages, redact secrets before indexing, restrict queries, and monitor dropped bytes, ingest lag, parse errors, index age, query p99, and cost.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Indexing every field improves exploration but drives cost/cardinality; selective schemas plus raw archive preserve flexibility.
