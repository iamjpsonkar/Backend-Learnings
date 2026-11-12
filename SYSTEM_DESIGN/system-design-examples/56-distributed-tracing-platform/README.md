# Distributed Tracing Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Propagate trace context, sample, ingest spans, reconstruct traces, search, and enforce retention.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Span(trace_id,span_id,parent,start,duration,status,attributes); trace blobs and a selective search index are stored separately.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
SDK/collector -> sampling/buffer -> trace partition -> object/column store + index -> query service
```

Partition by trace ID, batch/compress, tail-sample after assembling traces, index only chosen attributes, and apply per-tenant budgets.

## Failure, security, and observability

Handle missing/late spans, preserve clock metadata, redact secrets, restrict trace access, and monitor accepted/dropped spans, assembly delay, sampling, and query latency.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Head sampling is cheap but misses rare failures; tail sampling retains interesting traces but requires buffering and more infrastructure.
