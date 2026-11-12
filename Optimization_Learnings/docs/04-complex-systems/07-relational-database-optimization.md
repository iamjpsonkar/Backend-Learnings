# Relational Database Optimization at Scale

Database performance is the result of schema, queries, statistics, indexes,
transactions, concurrency, maintenance, memory, storage, and topology. Tune the
workload and plan before increasing database capacity.

## Workload inventory

Classify operations by frequency, latency contribution, rows examined and
returned, bytes, lock time, temporary spill, and business importance. Separate
point reads, range reads, joins, writes, analytical scans, and maintenance.

## Schema and access patterns

- Model around invariants and dominant access paths.
- Choose compact types and avoid oversized generic fields.
- Normalize to protect integrity; selectively denormalize measured read paths.
- Keep frequently updated rows narrow to reduce write amplification.
- Separate large cold values when hot queries do not need them.
- Use generated, summary, or materialized data for expensive stable derivations.

## Query optimization

- Select only required columns and rows.
- Eliminate N+1 access with joins, batching, or prefetching.
- Make predicates sargable; avoid transformations that hide indexed columns.
- Replace deep offset pagination with keyset pagination.
- Use set-based operations instead of per-row application loops.
- Bound result sets and analytical scans.
- Inspect actual plans with representative parameters and data skew.
- Update statistics when estimates diverge from actual cardinality.

## Index design

- Order composite keys around equality, range, ordering, and selectivity.
- Use covering or included columns for important read paths where supported.
- Use partial indexes for selective stable predicates.
- Index foreign keys used in joins and cascading operations.
- Remove redundant and unused indexes after a complete workload cycle.
- Measure write, memory, storage, vacuum, and replication cost of every index.

An index is not automatically useful. Low selectivity, stale statistics, type
mismatches, small tables, or queries returning much of a table can favor scans.

## Transaction and lock optimization

- Keep transactions short and never wait on remote calls while holding locks.
- Access rows in a consistent order to reduce deadlocks.
- Select the weakest isolation level that still preserves the invariant.
- Retry serialization failures with limits, backoff, and idempotency.
- Avoid hot counters and rows; shard or aggregate them when semantics allow.
- Monitor lock waits, deadlocks, long transactions, and old snapshots.

## Connections and admission control

Connection pools should bound database concurrency, not maximize it. Size from
measured active work, query latency, server parallelism, and memory per session.
Use queue timeouts, acquire deadlines, leak detection, and separate pools for
latency-sensitive and bulk traffic.

## Partitioning and lifecycle

Partition very large data by predicates, maintenance, lifecycle, or tenancy.
Ensure queries prune partitions and avoid excessive partition counts. Attach or
detach partitions for bulk retention changes rather than deleting row by row.

## Replication and topology

- Route stale-tolerant reads to replicas with explicit lag limits.
- Preserve read-your-writes when the product requires it.
- Distribute geographically only when latency, sovereignty, or resilience
  justifies consistency and operational complexity.
- Test failover capacity, replica catch-up, and connection reconvergence.

## Maintenance

Schedule and observe vacuum, compaction, statistics, checkpointing, backup,
index rebuild, and retention. Maintenance debt eventually becomes request-path
latency or availability risk.

## Sources

- [PostgreSQL EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [PostgreSQL index examination](https://www.postgresql.org/docs/current/indexes-examine.html)
- [PostgreSQL table partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
