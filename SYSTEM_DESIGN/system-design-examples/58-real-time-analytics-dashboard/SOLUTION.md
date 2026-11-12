# Worked Solution: Real-Time Analytics Dashboard

[Design brief](README.md) | [All examples](../README.md)

## Requirements and guarantees

Ingest immutable events, compute event-time aggregates, correct late data, and serve tenant-isolated dashboards with explicit freshness and approximation. Target one million events/s, 5x bursts, p99 durable acknowledgment below 500 ms, 99.9% query availability, recent results within 10 seconds, and p95 dashboard load below 2 seconds. Accepted means durably logged; materialized results are eventually consistent to a published watermark.

## Capacity estimation

At one million 500-byte events/s, input is 500 MB/s or 43.2 TB/day before replication/compression. Keep seven hot raw days and archive compressed raw events for replay. Pre-aggregate common dimensions because arbitrary combinations grow exponentially. Exact distinct sets are unbounded, so use mergeable HLL sketches; use mergeable quantile sketches rather than storing all values.

## Data model and invariants

```text
Event(tenant, event_id, schema_version, event_time, ingestion_time,
      dimensions, measures)
Cube(tenant, metric_version, window_start, window_end, dimension_key,
     count, sum, min, max, hll, quantile_sketch, revision, final)
```

Identity is `(tenant,event_id)`. Events are immutable and schema-versioned. Cube windows are half-open. A cube update is an absolute versioned value, not a non-idempotent increment. Metric definitions specify allowed dimensions, filters, measure type, window, lateness, and approximation error.

## APIs

```http
POST /v1/events
POST /v1/query {metric, group_by, filters, start, end, granularity}
GET  /v1/dashboards/{id}/stream?since_revision=
PUT  /v1/metrics/{id} If-Match: <version>
```

Queries return data plus metric version, watermark, scanned interval, approximation bounds, revision, and `complete`. Tenant and authorization come from credentials, never event fields.

## Architecture

```text
producers -> gateways -> partitioned durable log -> stream processors/checkpoints
                         |                         |
                         v                         v
                    raw object lake          real-time OLAP cubes
                         |                         ^
                  batch replay/correction --------+
dashboard -> semantic query service -> cache -> OLAP/raw bounded fallback
                     |
                update fan-out/SSE
```

Partition by tenant plus aggregation key, with salted heavy keys where aggregates are mergeable. Gateways validate schemas, dimensions, IDs, quotas, and event-time bounds. Stream state is checkpointed to durable storage; sink commits and consumed offsets participate in exactly-once checkpoints or use idempotent revision upserts.

## Main stream logic

```text
on_event(e):
  validate_schema_and_tenant(e)
  if dedupe.seen(e.tenant, e.event_id): return DUPLICATE
  assign event to every configured half-open window
  for metric in matching_metric_versions(e):
    key = canonical_dimensions(e, metric.group_by)
    state = windows[(metric.id, metric.version, window(e.time), key)]
    state.count += 1; state.sum += measure(e)
    state.min/max = update(state.min/max, measure(e))
    state.hll.add(metric.distinct_field(e))
    state.quantiles.add(measure(e))
    emit_absolute_upsert(state, next_revision())

watermark(partition) = max_event_time_seen - allowed_out_of_orderness
global_watermark = min(non_idle_partition_watermarks)
```

Dedupe state is retained through maximum lateness plus retry horizon; older duplicate risk is repaired from raw data. Idle partitions are excluded only after a declared idle timeout. A late event before finalization revises the cube. After finalization it enters a correction log; batch recomputation publishes a higher revision. Beyond correction retention it is archived and counted, not silently included inconsistently.

## Query logic

The semantic layer resolves one metric version for each time segment, validates allowed groupings, estimates rows, and rejects excessive scans. It splits ranges into finalized historical windows and mutable recent windows, avoiding boundary overlap, then merges only compatible aggregate states.

```text
query(q):
  plan = compile_metric_semantics(q)
  enforce_tenant_row_byte_time_budget(plan)
  parts = split_by_version_resolution_and_watermark(plan)
  rows = parallel_read(parts)
  merged = merge(count/sum/min/max/sketches, rows)
  return finalize_average_and_quantiles(merged), min_watermark(parts)
```

Averages derive from total sum/count; percentiles derive from merged sketches, never averaged percentiles. Cache keys contain tenant, normalized query, metric versions, interval, resolution, and cube generations. Mutable-window cache entries are short-lived or invalidated by revision.

## Step-by-step workflow

1. A gateway authenticates, validates schema/time/dimensions, applies quotas, and appends the event durably.
2. The log assigns a stable partition and raw archiver stores replayable immutable events.
3. A processor deduplicates IDs and updates every applicable event-time window.
4. A checkpoint atomically captures offsets, dedupe/window state, and sink revision progress.
5. The OLAP sink upserts absolute cube values only when the incoming revision is newer.
6. The query layer merges finalized history with the mutable recent region and reports its watermark.
7. Dashboard fan-out sends revision hints; clients refetch affected panels and discard stale revisions.
8. Late corrections recompute from raw truth, publish higher revisions, and invalidate cache generations.

## Dashboard delivery and backpressure

One browser subscription represents a dashboard, not one stream per tile. Fan-out messages contain dashboard/panel IDs and revisions, not entire datasets. Clients coalesce refreshes, use `since_revision`, and fall back to polling after reconnect. Slow consumers receive a reset marker and refetch; servers never hold unbounded queues. Expensive panels have concurrency and refresh-frequency limits.

## Failure handling

- **Processor crash:** restore checkpoint and replay; dedupe plus revision upserts prevent double count.
- **Sink unavailable:** log retains input, processors backpressure, and freshness watermark visibly stalls.
- **Poison event:** quarantine with reason after schema validation; never block a partition forever.
- **Hot key/tenant:** quotas, salted mergeable partials, and fair query queues isolate load.
- **Late surge:** bounded state and correction queues protect current processing; correction lag is exposed.
- **Bad metric version:** immutable versions and raw replay permit corrected backfill into a new generation.
- **Partial query:** fail unless explicit best effort; return missing partitions and completeness.
- **Region loss:** replicated log/raw lake recover; new processors fence old epochs before publishing.

## Security and governance

Use mTLS, short-lived identities, tenant-scoped RBAC, encryption, audited metric/dashboard changes, and regional retention. Allowlist dimensions and cap their cardinality/value size. Redact or tokenize sensitive fields at ingestion. Protect raw export and drill-down separately, sign cursors, sandbox expressions, and enforce CPU/row/byte/time budgets.

## Observability and SLOs

Track accepted/rejected/duplicate events, log and checkpoint lag, watermark by partition, idle partitions, active windows/state bytes, late/corrected/dropped events, sink revision conflicts, cube/raw reconciliation error, query scanned rows/latency/cache hit, SSE backlog/resets, and displayed freshness.

Canary events with known duplicates, late arrivals, sums, distinct counts, and quantiles verify ingestion-to-dashboard correctness. Page on durability, watermark, correctness, or query error-budget burn.

## Implementation path

1. Define versioned event/metric schemas and build raw ingestion plus batch aggregates.
2. Add streaming windows, durable checkpoints, dedupe, and revisioned idempotent cube upserts.
3. Add semantic query planning, strict interval boundaries, budgets, and generation-aware caching.
4. Add watermarks, late revisions, correction jobs, and raw-versus-cube reconciliation.
5. Add sketches with documented error, dashboard fan-out/backpressure, quotas, and audit.
6. Rehearse replay, sink loss, hot keys, late floods, bad metric versions, and regional recovery.

## Final design

The immutable log and raw archive are replayable truth; revisioned cubes are disposable serving materializations. Event-time watermarks make freshness and finality measurable. Mergeable aggregates preserve correct cross-window math, while metric schemas and budgets prevent combinatorial dimension cost. Dashboards expose watermark, revision, and approximation instead of presenting provisional data as exact.
