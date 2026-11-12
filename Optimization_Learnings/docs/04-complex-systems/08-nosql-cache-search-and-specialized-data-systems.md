# NoSQL, Cache, Search, and Specialized Data Systems

Choose a data system from access patterns, consistency, durability, scale,
query shape, and operational constraints—not category labels. Every specialized
store makes some operations efficient by constraining or moving other costs.

## Key-value and document stores

- Design partition keys for even traffic and storage distribution.
- Add key entropy when monotonic keys create a single hot partition.
- Duplicate data deliberately to satisfy bounded query patterns.
- Keep documents below practical transfer and update sizes.
- Use conditional writes, versions, or compare-and-swap for concurrency.
- Avoid unbounded secondary-index fan-out and cross-partition scans.
- Monitor hot keys, throttling, item size, partition count, and rebalancing.

## Wide-column and time-series stores

- Partition by entity plus bounded time window.
- Choose clustering order for the exact range queries required.
- Downsample and aggregate older time-series data.
- Control label or tag cardinality.
- Batch adjacent writes without creating oversized partitions.
- Define retention, compaction, tombstone, and late-data behavior.

## Caching strategies

| Pattern | Best fit | Main risk |
| --- | --- | --- |
| Cache-aside | Read-heavy data loaded on demand | Stale data, miss storms |
| Read-through | Centralized loading behavior | Cache becomes hard dependency |
| Write-through | Read-after-write cache consistency | Added write latency |
| Write-behind | High write throughput | Loss and ordering complexity |
| Refresh-ahead | Predictable hot data | Wasted refresh work |
| Request coalescing | Concurrent misses for same key | Leader failure, long waits |
| Negative caching | Repeated absent lookups | Hides newly created data |

Use TTL jitter, single-flight loading, stale-while-revalidate, bounded retries,
and origin admission control to prevent stampedes. Size by bytes and working set,
choose eviction deliberately, and test complete cache loss.

## Search systems

- Map only fields that need search, aggregation, sorting, or retrieval.
- Normalize analysis and tokenization to product semantics.
- Route related documents to reduce scatter-gather.
- Refresh and merge less frequently for indexing throughput when freshness
  permits.
- Use filters and cached bitsets for exact predicates.
- Prefer search-after or point-in-time cursors over deep offsets.
- Bound wildcard, fuzzy, script, and high-cardinality aggregation work.
- Measure shard skew, segment count, merge pressure, and query fan-out.

## Graph and vector systems

- Bound graph traversal depth, breadth, and result count.
- Precompute common neighborhoods or path summaries.
- Partition around locality while recognizing cross-partition edge cost.
- For vector search, tune index type, candidate count, dimensions, precision,
  and recall together.
- Quantize embeddings when measured quality allows it.
- Apply metadata filters early without destroying index effectiveness.
- Batch embedding generation and retrieval requests.

## Cache and replica correctness

Write down required semantics: strong consistency, monotonic reads,
read-your-writes, bounded staleness, or eventual convergence. Include versions
in cache entries and events. Make invalidation idempotent and observable.

## Sources

- [Redis optimization documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/)
- [Redis pipelining](https://redis.io/docs/latest/develop/using-commands/pipelining/)
- [Redis latency diagnosis](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/)
