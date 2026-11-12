# Worked Solution: Distributed Tracing Platform

[Design brief](README.md) | [All examples](../README.md)

## Requirements and guarantees

The system propagates trace context, ingests spans, retains valuable traces, searches selected attributes, and renders a service graph and waterfall. It must tolerate duplicates, late/missing spans, skewed clocks, and tenant overload. Acknowledged spans are durably buffered; search is eventually consistent. A returned trace declares whether it is complete, timed out, or still assembling.

Targets: 10 million peak spans/s, p99 collector acknowledgment below 300 ms, retained traces searchable within 60 seconds, trace-by-ID p95 below 2 seconds, attribute search p95 below 5 seconds, and 30-day retention.

## Capacity estimation

At 10 million spans/s and 500 compressed bytes/span, raw ingress is 5 GB/s or 432 TB/day. Keeping everything is impractical. Assume deterministic head sampling keeps 10%, tail policy retains 10% of that normally plus all bounded error/slow candidates: roughly 1–3% long-term, or 4.3–13 TB/day before indexes and replication. The durable bus must cover peak input during the tail-sampling decision window. Index only approved attributes; indexing arbitrary values recreates the cardinality problem.

## Data model and invariants

```text
TraceContext(trace_id[16], parent_span_id[8], trace_flags, tracestate)
Span(tenant, trace_id, span_id, parent_id?, service, operation,
     start_ns, duration_ns, status, kind, attributes, events, links, resource)
TraceSummary(trace_id, min_start, max_end, root_service, services,
             error_count, span_count, duration, indexed_attributes, completeness)
```

Identity is `(tenant,trace_id,span_id)`. Identical retries are duplicates; conflicting versions use a deterministic winner (highest valid update sequence, otherwise first accepted) and emit a conflict metric. Trace IDs are random 128-bit values generated at the request edge. Parent IDs define a graph, not necessarily a tree, because spans can have links and malformed instrumentation.

Propagate W3C `traceparent` and bounded `tracestate`; never trust baggage as authorization. SDK clocks record start/duration using a monotonic clock where possible and attach wall-clock time only for cross-host placement.

## API contracts

```http
POST /v1/traces                 # OTLP protobuf batches; tenant from mTLS/token
GET  /v1/traces/{trace_id}
POST /v1/search                 # bounded time range + approved predicates + cursor
GET  /v1/services/{service}/operations
PUT  /v1/sampling-policies/{id} # optimistic version
```

Ingest returns accepted/rejected counts and retryable status. Search cursors encode the normalized query, last sort key, tenant, and index generation; they are signed and expire. Responses include completeness, sampling policy/version, warnings, and searched interval.

## Architecture

```text
instrumented apps -> local/edge collectors -> durable span log (trace-id partition)
                                              |
                                      trace assemblers
                                      /             \
                              tail policy       live trace cache
                                  |                    |
                         object trace blocks     query by ID
                                  |
                     selective columnar search index
                                  |
UI/API -> query frontend -> index scan -> trace block fetch -> graph/waterfall

control plane -> schemas, redaction, quotas, sampling policies, retention
```

Collectors batch, compress, normalize, redact, apply cheap head decisions, and spool briefly to disk. The log partitions by `(tenant,trace_id)` so one assembler sees a trace. Assemblers keep bounded trace state until a root-end grace period or hard timeout. Tail policy chooses keep/drop. Kept traces are written into immutable time blocks in object storage and summaries into a selective columnar index. Trace ID has a direct locator index. Query workers fetch only matching trace blobs.

## Main propagation and sampling logic

At the first trusted edge:

```text
start_request(incoming_context, tenant):
  ctx = validate_traceparent(incoming_context) or new_random_context()
  policy = cached_policy(tenant)
  head_keep = hash(ctx.trace_id) < policy.head_probability_threshold
  ctx.trace_flags.sampled = head_keep
  return ctx
```

Hash sampling is deterministic across services. SDKs always create minimal propagation context, but may omit span recording when definitely dropped. Important tenants can use a higher bounded probability. Collectors reject oversized spans, truncate configured strings, redact keys/values, and never accept a client-supplied tenant.

Tail assembly and selection:

```text
on_span(span):
  validate_and_redact(span)
  key = (tenant, trace_id)
  state = trace_cache.get_or_create(key)
  state.upsert_by_span_id(span)
  state.min_start = min(state.min_start, span.start)
  state.max_end = max(state.max_end, span.end)
  state.features.update(error, latency, service, route)
  if state.bytes > per_trace_limit: state.truncated = true; evict_low_value_spans()
  if root_finished_and_grace_elapsed(state) or hard_timeout_elapsed(state): finalize(state)

finalize(trace):
  policy = policy_at(trace.first_seen)
  decision = KEEP if policy.always_keep_error(trace)
          else KEEP if policy.keep_slow(trace)
          else KEEP if deterministic_hash(trace.id, policy.version) < policy.rate
          else DROP
  persist_decision(trace.id, policy.version, decision)
  if KEEP: atomically_write_trace_and_summary(trace)
```

Decision persistence makes replay deterministic. Policy priority is explicit, and every rule has a per-tenant rate budget; “keep all errors” degrades to deterministic reservoir sampling during an error storm rather than exhausting storage.

## Step-by-step workflow

1. The trusted ingress validates or creates trace context and makes a deterministic head decision.
2. Services create child spans, propagate only bounded context, and export batches asynchronously.
3. Local collectors redact, validate, compress, and durably forward batches; applications never block on the backend.
4. The span log partitions every span for a trace to one assembler ownership group.
5. The assembler idempotently builds trace state until root grace or hard timeout.
6. Versioned tail policy keeps errors, slow traces, and a representative deterministic sample within budgets.
7. A kept trace blob and searchable summary are committed; direct-ID and attribute indexes become visible.
8. Query workers locate candidate IDs, fetch blobs, correct presentation skew, construct the graph, and declare completeness.

## Storage and indexing

Trace blocks are immutable, tenant/time-partitioned, compressed columnar objects. A block footer maps trace ID to byte ranges. The primary locator maps `(tenant,trace_id)` to block ID and offset. The search index contains time, duration, status, service, operation, and an allowlist of normalized attributes. Large payloads and arbitrary baggage are never indexed.

Commit the trace block first, verify checksum, then publish its locator and summary in one index generation. Queries ignore unpublished objects. Compaction combines small blocks, records source IDs, and retires sources after a grace period. Retention removes index entries before inaccessible blocks and uses lifecycle cleanup afterward.

## Query and critical-path logic

Search requires a bounded time range. The planner intersects selective columns, estimates candidates/bytes, enforces tenant budgets, and returns stable `(start_time,trace_id)` pagination. It fetches trace blobs only after selecting IDs.

For a waterfall, build nodes keyed by span ID. Missing parents attach to a synthetic “missing parent” node; cycles are detected and broken for display. Clock correction may shift a child within its parent's plausible interval using collector/resource offset estimates, but preserves original timestamps for audit.

Critical path is not the sum of all spans. For each span, merge overlapping child intervals, identify the child chain that determines the parent's latest completion, and add uncovered self-time. Async linked work is shown separately unless it blocks an explicit join. The response reports uncertainty for missing parents or truncated traces.

Service graphs aggregate sampled edges by `(source,destination,operation,time_bucket)` with count, error count, and latency sketches. Counts are weighted by the known sampling probability; policy-biased samples are marked and must not be naively extrapolated.

## Late spans and partial traces

The assembler accepts late spans for a bounded reopen window. If a finalized trace was kept, it writes a patch object and advances the locator generation; reads merge base plus patches by span ID. If it was dropped, the persisted decision prevents a late span from resurrecting it unless a specifically versioned policy permits that behavior. After the window, late spans are counted and discarded or stored in a diagnostic quarantine.

Completeness values are `ASSEMBLING`, `COMPLETE_ROOT_OBSERVED`, `TIMED_OUT_PARTIAL`, and `TRUNCATED`. “Root observed” is evidence, not proof that every span arrived.

## Failure handling

- **SDK/collector unavailable:** bounded local queues protect applications; low-priority spans drop first and loss is counted.
- **Log outage:** collectors spool to bounded disk and backpressure exporters, never request handlers.
- **Assembler crash/rebalance:** replay the partition from its committed offset; span upsert and persisted decisions make it safe.
- **Hot trace:** per-trace span/byte limits truncate it and retain root/error/long spans preferentially.
- **Error storm:** policy-specific reservoirs and tenant byte budgets prevent “keep all errors” overload.
- **Object/index partial failure:** unpublished blocks are invisible; reconciliation republishes or deletes orphans.
- **Index lag:** trace-by-ID can use the recent cache; search reports its indexed-through watermark.
- **Tenant overload:** admission quotas, fair partitions, and query concurrency isolate neighbors.
- **Malformed graph/clock:** retain original data, render a safe partial graph, and expose warnings.

## Security and privacy

Use mTLS, short-lived identities, tenant-scoped authorization, encryption, and audited access. Redact secrets at the closest collector using versioned policies, then scan server-side as defense in depth. Bound baggage, events, links, attribute count, and string size. Trace search can expose customer data, so apply field-level access, purpose logging, regional residency, deletion workflows, and short retention for sensitive attributes.

## Observability and SLOs

Track spans generated/accepted/rejected/dropped by reason, collector queue/disk age, log lag, assembly memory and timeout rate, duplicate/conflict/late spans, sampling by rule and actual bytes retained, index freshness, orphan blocks, query candidate/fetch bytes, incomplete traces, and tenant throttling.

Canary services emit known nested, error, slow, duplicate, late, and skewed traces and verify ID lookup, search, graph shape, and retention. Page on sustained ingest durability, index freshness, or query SLO error-budget burn.

## Implementation path

1. Implement standards-compliant propagation, SDK batching, collector validation/redaction, and direct trace-ID storage.
2. Add a durable trace-partitioned log, idempotent assemblers, completion states, and replay tests.
3. Add deterministic head sampling and budgeted versioned tail policies.
4. Add immutable trace blocks, direct locators, selective search indexes, compaction, and retention.
5. Add bounded query planning, waterfall/graph construction, critical-path semantics, and signed cursors.
6. Add late-span patches, service graphs with sampling metadata, tenant isolation, and restore drills.
7. Chaos-test collector loss, replay, hot traces, error storms, index lag, zone loss, and privacy deletion.

## Final design

Trace context is cheap and ubiquitous; recorded spans are buffered durably and partitioned by trace ID. Deterministic head sampling controls source cost, while budgeted tail sampling preserves diagnostically useful traces. Immutable blobs remain separate from a deliberately small search index. Every query exposes sampling, freshness, and completeness so a partial or biased trace cannot masquerade as ground truth.
