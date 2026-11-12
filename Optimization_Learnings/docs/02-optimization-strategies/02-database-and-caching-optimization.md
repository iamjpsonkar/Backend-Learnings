# Database and Caching Optimization

Database performance depends on access patterns, data distribution, indexes,
query plans, transactions, connection management, and storage behavior. Treat
the query plan as evidence rather than guessing from SQL text.

## Query workflow

1. Capture the actual slow query and representative parameters.
2. Measure frequency, latency distribution, rows returned, and rows examined.
3. Inspect the execution plan.
4. Check table statistics and data distribution.
5. Change the query, index, schema, or access pattern.
6. Measure read improvement and write/storage cost.
7. Verify behavior with production-scale data.

For PostgreSQL, use `EXPLAIN` to inspect the chosen plan. `EXPLAIN ANALYZE`
executes the query, so use it carefully with writes and production workloads.

## Index strategy

Indexes can reduce reads but add storage, memory pressure, and write maintenance.

Good index candidates often include:

- Selective equality and range predicates
- Join keys
- Frequently used ordering that avoids a large sort
- Composite access patterns with a stable leading-column order
- Covering access patterns when index-only scans are valuable

Avoid creating an index for every column. Check whether real queries use each
index and remove redundant indexes only after verifying constraints and workload.

Run the in-memory SQLite demonstration:

```sh
python optimization_examples/sqlite_index.py
```

It prints the query plan and repeated-query timing before and after an email
index. Exact timing varies, but the plan changes from a table scan to an index
search.

## Common query problems

- **N+1 queries:** Load related data in batches, joins, or a bounded prefetch.
- **Over-fetching:** Select only needed columns and rows.
- **Deep offset pagination:** Prefer a stable cursor or keyset for large offsets.
- **Unbounded queries:** Require limits and protect expensive filters.
- **Functions on indexed columns:** They may prevent ordinary index use.
- **Long transactions:** They hold locks and retain database resources.
- **Missing statistics:** The optimizer may estimate cardinality poorly.
- **Hot rows:** Frequent updates to one row serialize otherwise parallel work.

## Connection pools

A connection pool avoids connection setup per request, but a larger pool is not
always faster. Too many active queries increase contention and can overwhelm the
database.

Set pool size using database capacity, application instance count, query time,
and expected concurrency. Define acquisition timeouts and measure pool wait time.

## Caching decision

Cache when all of these are understood:

- The data is expensive or frequent enough to justify caching.
- A key maps unambiguously to the value.
- Acceptable staleness is defined.
- Invalidation ownership is clear.
- Memory is bounded and eviction is observable.
- Failure behavior is defined for cache and source outages.

Run the deterministic TTL example:

```sh
python optimization_examples/ttl_cache.py
```

## Cache patterns

- **Cache-aside:** Read cache, load on miss, then populate.
- **Read-through:** Cache layer loads missing values.
- **Write-through:** Update cache and backing store together.
- **Write-behind:** Buffer writes before persistence; higher risk and complexity.
- **Refresh-ahead:** Refresh popular entries before expiry.

## Cache risks

- **Stampede:** Many callers rebuild the same expired key. Use request coalescing,
  locks, early refresh, or jittered TTLs.
- **Stale data:** Define TTLs and event-driven invalidation from consistency needs.
- **Hot keys:** Replicate, shard, or redesign concentrated access.
- **Unbounded cardinality:** Enforce size limits and reject unsafe keys.
- **Negative-result storms:** Cache safe not-found results briefly when useful.
- **Cache dependency:** Decide whether to fail open, fail closed, or bypass.

A high hit ratio can still hide poor performance if misses are extremely slow.
Measure hit latency, miss latency, source load, evictions, memory, and stampede
events together.

## Data correctness first

Never trade away constraints, transaction correctness, authorization, or durable
state merely to improve a benchmark. Document any relaxed consistency model and
test read-after-write, concurrent updates, failure recovery, and cache
invalidation explicitly.
