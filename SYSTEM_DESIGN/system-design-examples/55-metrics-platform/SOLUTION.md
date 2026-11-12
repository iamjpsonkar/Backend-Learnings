# Worked Solution: Metrics Platform

[Design brief](README.md) | [All examples](../README.md)

## Requirements and guarantees

The platform accepts counters, gauges, and histograms from many tenants, retains labeled time series, evaluates rules, and serves dashboard and ad-hoc range queries. It supports pull-scraped and remote-written samples, label queries, aggregation, alert/recording rules, downsampling, retention, and deletion.

Targets: 99.99% durable acknowledged samples, 99.9% ingest/query availability, p99 write acknowledgment below 500 ms, recent samples queryable within 10 seconds, and p95 dashboard queries below 2 seconds. Acknowledgment means a sample is durable in a write quorum's WAL. Read-after-write is eventually consistent, and partial query results are never silently called complete.

## Capacity estimation

Assume 10 million active series, a 15-second interval, 3x peak, and 30 raw days:

- average ingest: `10,000,000 / 15 = 667,000 samples/s`; peak about 2 million/s;
- at an effective 300 GB/day including chunks, indexes, metadata, and margin, raw retention is 9 TB logical;
- replication and temporary compaction require several times that capacity;
- mutable series, chunks, indexes, and WAL require tens of GB per ingester.

Cardinality is the primary limit. Every tenant has budgets for active series, newly created series/minute, labels/series, label length, samples/s, and query work. Labels such as `request_id` and `user_id` are rejected or removed at collection.

## Data model and invariants

```text
SeriesKey = tenant_id + metric_name + sorted(label_name, label_value)*
fingerprint = hash128(SeriesKey)
Sample = {event_timestamp_ms, float64_value, ingestion_timestamp_ms}
Block = {id, tenant, min_time, max_time, resolution, sources, checksum}
```

The hash accelerates lookup but is not identity: collisions compare the full canonical key. Label names are unique and sorted. An exact `(series, timestamp, value)` retry is idempotent; a different value at the same timestamp is a conflict.

Counters normally increase but can reset; gauges move arbitrarily. Classic histograms use cumulative bucket, sum, and count series. Native histograms store mergeable bucket spans, sum, and count. Blocks cover half-open intervals `[min_time,max_time)`.

## API contracts

```http
POST /v1/write                   # compressed WriteRequest{series:[labels,samples]}
GET  /v1/query_range?query=&start=&end=&step=
GET  /v1/series?match[]=&start=&end=
GET  /v1/labels/{name}/values?start=&end=
PUT  /v1/rule-groups/{id}        # If-Match: version
DELETE /v1/series?match[]=&start=&end=
```

Authentication supplies the tenant; clients cannot choose it as a label. Writes return accepted, duplicate, and rejected counts with stable reason codes. Query responses contain `complete`, warnings, searched range, and shard errors. Best-effort partial results require an explicit request.

## Architecture

```text
targets -> agents -> distributors -> zone-aware ingester replicas -> WAL/head
                                      |                         |
                                      +-------------------------+-> object blocks
query frontend -> fair scheduler -> ingesters + store gateways -> block indexes/chunks
       |                                                    ^
       +-> result cache        ruler -> recorded samples    |
object blocks -> compactor/downsampler ---------------------+
control plane -> tenant limits, ring, rules, deletion marks
```

Distributors authenticate, validate, limit, and route. A consistent-hash ring maps each series to three zones. Ingesters own mutable state, WAL, and head chunks. Immutable TSDB blocks contain compressed chunks, symbols, per-label postings, series records, and checksums. Store gateways cache indexes; the frontend plans, splits, schedules, caches, and merges. Compactors merge blocks, apply tombstones, and create rollups. Rulers use the normal query and write paths.

## Main ingestion logic

```text
ingest(tenant, batch):
  authorize(tenant, "metrics.write")
  limits = versioned_limits(tenant)
  for stream in batch:
    labels = canonicalize(stream.labels)
    if invalid(labels) or exceeds_label_limits(labels): reject(INVALID_LABELS); continue
    key = encode(tenant, labels); fp = hash128(key)
    if is_new(fp, key) and !series_creation_budget.take(tenant):
      reject(CARDINALITY_LIMIT); continue
    if !sample_budget.take(tenant, len(stream.samples)):
      reject(INGEST_RATE_LIMIT); continue
    replicas = ring.owners(fp, count=3, distinct_zones=true)
    replies = parallel_append(replicas, fp, key, stream.samples)
    if durable_successes(replies) >= 2: accept()
    else: return_retryable_error()
```

Each ingester serializes one series:

```text
append(series, samples):
  state = find_by_fingerprint_then_full_key(series)
  for s in sort_and_remove_exact_duplicates(samples):
    if s.time == state.latest_time:
      if bit_equal(s.value, state.latest_value): count_duplicate(); continue
      reject(TIMESTAMP_VALUE_CONFLICT); continue
    if s.time > now + max_future_skew: reject(FUTURE_SAMPLE); continue
    if s.time < state.latest_time - out_of_order_window: reject(TOO_OLD); continue
    WAL.append_with_length_and_checksum(series, s)
    if s.time < state.latest_time: state.bounded_ooo_buffer.insert(s)
    else: state.head_chunk.append(s); state.latest = s
  WAL.group_fsync()
  acknowledge_only_after_durable_offset()
```

Late samples become small patch blocks rather than rewriting large history. If two replicas cannot durably append, the distributor fails the stream. Agents retry with jitter and a bounded disk queue; queue overflow is observable.

## Storage, flushing, and compaction

Head chunks use delta-of-delta timestamps and XOR-style float compression. An ingester cuts blocks by time/size, uploads all objects, verifies checksums, then publishes metadata. Readers ignore incomplete uploads.

Compaction selects blocks of one tenant and resolution, merge-sorts series, removes exact duplicates, applies tombstones, writes a new immutable block, and atomically publishes it. Output records source IDs, making retry idempotent. Old blocks get deletion marks and are removed after a reader grace period. If a crash leaves overlaps, reads deduplicate `(full series key,timestamp)` and compaction repairs them.

## Step-by-step workflow

1. An agent scrapes a target, attaches approved external labels, and batches event-timestamped samples.
2. A distributor authenticates, canonicalizes labels, rejects unsafe cardinality, and charges budgets.
3. It hashes the collision-checked series identity and sends it to three zone-separated ingesters.
4. Ingesters validate time ordering, append WAL records, group-fsync, and update their head chunks.
5. The distributor acknowledges after two durable replicas; failed streams are safely retried.
6. Ingesters publish complete immutable blocks; compactors merge them and apply tombstones.
7. Query planning reads ingesters for recent time and object blocks for older time.
8. Merge logic removes HA-replica and block-overlap duplicates before expression evaluation.

## Query planning and execution

```text
execute_range(expr, start, end, step):
  ast = parse_and_typecheck(expr)
  require_bounded_range_and_authorize_matchers(ast)
  resolution = choose_semantically_valid_resolution(step, ast)
  slices = split_at_cache_and_block_boundaries(start, end)
  plans = postings_intersections(ast, slices, resolution)
  reject_if_estimated_series_chunks_or_bytes_exceed_budget(plans)
  shards = fair_scheduler.run(plans, tenant_concurrency_limit)
  if missing(shards) and !explicit_best_effort: fail(QUERY_INCOMPLETE)
  data = merge_sort_and_dedupe(shards)
  return evaluate(ast, data, step, lookback_delta), completeness_metadata
```

Exact postings are intersected before bounded regex matchers. Negative matchers cannot trigger an unlimited scan. Cache keys include tenant, normalized expression, time slice, step, resolution, block generation, and semantic version. At an evaluation time, instant selectors use the newest non-stale sample inside the lookback interval; range selectors use `(evaluation-range,evaluation]` everywhere.

## Correct metric math

```text
counter_increase(samples):
  total = 0
  for previous,current in adjacent(samples):
    if current >= previous: total += current - previous
    else: total += current          # reset: new counter began at zero
  return bounded_boundary_extrapolation(total, samples)

rate = counter_increase(samples) / requested_range_seconds
```

Gauge functions never use reset logic. For classic histograms, sum corresponding cumulative buckets across instances and then interpolate the quantile; never average per-instance p95 values. Native histograms merge only compatible schemas. Exemplars are separately sampled and bounded so trace IDs do not create metric series.

## Downsampling and retention

Gauge rollups keep `count,sum,min,max,first,last`; counter rollups keep first, last, reset-adjusted increase, and reset count; histogram rollups keep mergeable buckets, sum, and count. An average alone cannot reconstruct min/max or a counter rate.

Keep raw for 30 days, five-minute rollups for 180 days, and one-hour rollups for two years. The planner selects a resolution smaller than the query step only when required semantics can be reconstructed. It splits at retention boundaries without counting a boundary twice. Lifecycle deletion begins only after rollup verification.

## HA deduplication and rules

HA agents attach stable `cluster` and unique `replica` labels. The distributor elects one replica per `(tenant,cluster)`, tracks a timestamp watermark, and strips only `replica`. After lease expiry another replica wins; overlap is timestamp-deduplicated. Conflicting values are surfaced.

Rule groups run at stable scheduled timestamps. Rules within a group run in order; groups can run independently. Output identity plus evaluation timestamp makes retries idempotent. Recording rules write through normal ingestion. Alert state persists as `inactive -> pending -> firing`; notifications use stable fingerprints. Every evaluation records the rule version and query completeness, and incomplete input cannot silently resolve an alert.

## Failure handling

- **Ingester crash:** remaining replicas accept quorum writes; replacement replays its WAL and repair restores replication.
- **Zone loss:** zone-aware placement retains a quorum and load shedding protects writes.
- **Retry storm:** storage idempotency collapses duplicates; budgets and jitter prevent amplification.
- **Object-store outage:** local sealed data is retained to a deadline and ingestion backpressures before disk exhaustion.
- **Partial upload/compactor crash:** unpublished blocks are invisible; immutable inputs and source IDs make retry safe.
- **Hot tenant:** token budgets, per-tenant queues, shuffle sharding, and concurrency limits contain impact.
- **Worker loss:** idempotent shards retry; completeness remains explicit.
- **Clock skew:** far-future samples are rejected and NTP health is alerted.
- **Control-plane outage:** cached versioned policy works for a bounded time; unknown tenants fail closed.

## Security and isolation

Use mTLS, short-lived credentials, per-operation authorization, encryption, and audited rule/limit/deletion changes. Scope every object, cache entry, index, metadata API, exemplar, and error to the verified tenant. Cap compressed and decompressed request size, regex complexity, CPU, memory, series, bytes, and query wall time. Sensitive deletions require approval and an immutable audit trail.

## Observability and SLOs

Track accepted/rejected/duplicate/conflicting samples, active/new series and top label cardinality, quorum and WAL fsync latency, disk headroom/replay time, sample freshness, block upload/overlap/compaction/deletion lag, query queues/scanned bytes/cache hits/incomplete shards, and rule delay/failures/state divergence.

Synthetic canaries write known counters, gauges, and histograms and query expected results end to end. Alert on durability risk, freshness breach, and error-budget burn rather than raw CPU alone.

## Implementation path

1. Build a single-node WAL/head/block engine and semantic tests for counter and histogram math.
2. Add authenticated remote write, quotas, duplicate decisions, and bounded agent retries.
3. Partition by series, replicate across zones, acknowledge quorum durability, and implement repair.
4. Add object blocks, indexes, compaction, tombstones, backups, and restore drills.
5. Add costed queries, fair scheduling, splitting, generation-aware caching, and completeness metadata.
6. Add HA scrape deduplication and persistent recording/alert rule execution.
7. Add semantically correct rollups and prove raw-versus-rollup equivalence.
8. Load-test cardinality spikes, hot series, out-of-order writes, zone loss, storage loss, and adversarial queries.

## Final design

The durable unit is a quorum-WAL sample; the economical long-term unit is an immutable block. Collision-checked canonical identities drive zone-aware partitioning. Explicit cardinality and query budgets make multitenancy predictable. Counter resets, histogram merging, interval boundaries, replica deduplication, and completeness have identical semantics across live data, blocks, caches, rules, and rollups.
