# Messaging, Streaming, and Data Pipeline Optimization

Asynchronous systems trade immediate coupling for queues, lag, ordering, and
delivery complexity. Optimize useful event throughput while bounding latency,
state, reprocessing, and downstream pressure.

## Producer optimization

- Batch by record count, bytes, and maximum wait.
- Compress batches rather than individual small messages.
- Reuse producers and connections.
- Choose acknowledgement and durability settings from loss tolerance.
- Use idempotent production where duplicate writes violate semantics.
- Partition by the narrowest key that requires order.
- Bound producer buffers and block, spill, or reject explicitly when full.

Larger batches improve throughput and compression but add latency and memory.
Use time and size bounds together.

## Partition strategy

- Create enough partitions for target parallelism and future growth.
- Avoid excessive partitions that increase metadata, recovery, and file cost.
- Measure byte and processing skew by key.
- Salt hot keys only when downstream aggregation can restore semantics.
- Keep stateful processing and its state store aligned to the same key.
- Repartition deliberately; every shuffle adds network, serialization, and disk.

## Consumer optimization

- Process batches and use bulk downstream operations.
- Scale consumers only until partitions or dependencies become limiting.
- Tune fetch size and wait to balance throughput against latency.
- Commit progress after the defined processing guarantee.
- Pause partitions when downstream capacity is unavailable.
- Isolate poison records in a bounded dead-letter workflow.
- Monitor lag in records, bytes, and estimated time to catch up.

## Delivery semantics

At-most-once, at-least-once, and effectively-once behavior each require an
explicit failure model. Exactly-once infrastructure does not make external side
effects atomic. Use idempotency, deduplication, transactional state updates, or
outbox/inbox patterns at the business boundary.

## Stream processing

- Use event time and watermarks when arrival can be late or reordered.
- Bound windows, joins, and state with retention.
- Pre-aggregate before shuffles.
- Use incremental algorithms instead of recomputing complete windows.
- Checkpoint at a frequency that balances overhead and replay time.
- Compact state and control tombstone accumulation.
- Treat backfills as a separate workload with explicit capacity limits.

## Batch analytics

- Push filters and projections into data readers.
- Choose partition sizes large enough to amortize scheduling but small enough
  for parallelism and failure recovery.
- Broadcast genuinely small reference data rather than shuffling large facts.
- Detect and split skewed shuffle partitions.
- Use columnar formats and vectorized execution.
- Cache only reused datasets whose recomputation cost exceeds storage pressure.
- Compact tiny files and avoid producing a single huge output partition.

## Pipeline operations

Measure input rate, output rate, processing time, queue age, retries, drops,
rebalances, checkpoint duration, state size, spill, skew, and downstream errors.
Define backlog recovery objectives in addition to steady-state throughput.

## Sources

- [Kafka introduction and partition model](https://kafka.apache.org/42/getting-started/introduction/)
- [Spark tuning](https://spark.apache.org/docs/latest/tuning.html)
- [Spark SQL performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning)
