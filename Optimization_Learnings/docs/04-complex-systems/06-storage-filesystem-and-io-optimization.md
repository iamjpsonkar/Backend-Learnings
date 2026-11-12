# Storage, Filesystem, and I/O Optimization

Storage optimization aligns access patterns, durability, latency, throughput,
and cost with the physical system. Measure operations, bytes, queue depth,
service time, wait time, cache hit rate, and tail latency separately.

## Reduce I/O first

- Read only needed rows, columns, ranges, and fields.
- Cache or precompute frequently reused derived data.
- Deduplicate content and avoid rewriting unchanged blocks.
- Compact many tiny records into appropriately sized segments.
- Compress when saved I/O outweighs CPU and latency cost.
- Use delta, columnar, or sparse representations for suitable workloads.
- Retain and tier data according to actual access and recovery requirements.

## Access-pattern strategies

- Prefer sequential access and large contiguous transfers for bulk throughput.
- Use indexes for selective random access.
- Batch small reads and writes while bounding latency and memory.
- Pipeline or use asynchronous I/O to maintain useful device queue depth.
- Avoid read-modify-write amplification with aligned update sizes.
- Separate latency-sensitive traffic from compaction, backup, and scans.
- Choose block, file, object, or local ephemeral storage by semantics.

## Buffering and caching

Understand all layers: application buffers, database cache, filesystem page
cache, device controller, and remote service. Duplicate caches can waste memory
and distort benchmarks. Direct I/O can provide control for specialized systems
but transfers cache and alignment responsibility to the application.

## Write-path optimization

- Append sequentially and compact later for write-heavy workloads.
- Group commits when durability latency permits.
- Batch metadata and acknowledgement operations.
- Use write-ahead logging to separate durable sequential writes from data
  placement.
- Tune flush and synchronization frequency to the accepted loss window.
- Make compaction, checkpoint, and garbage collection incremental.
- Apply backpressure before device queues and dirty pages become excessive.

Never disable durability mechanisms without an explicit data-loss contract and
tested recovery procedure.

## File and object organization

- Avoid tiny-file explosions and oversized indivisible objects.
- Partition by access, lifecycle, and deletion pattern.
- Choose segment size to balance listing, parallelism, retries, and overhead.
- Store checksums and validate data at boundaries.
- Use multipart and resumable transfers for large remote objects.
- Co-locate compute with data and minimize cross-region transfers.

## Data formats

- Row formats suit point operations needing most fields.
- Column formats suit scans, projections, aggregation, and compression.
- Binary formats reduce size and parse work but require schema discipline.
- Splittable formats enable parallel range processing.
- Compression should be selected by ratio, encode/decode speed, memory, and
  random-access requirements.

## Diagnose saturation

Correlate application latency with device utilization, IOPS, throughput, queue
depth, average request size, read/write mix, cache misses, flushes, compaction,
and throttling. A device at low bandwidth can still be saturated by small random
I/O or durability operations.

## Sources

- [Linux block I/O documentation](https://docs.kernel.org/block/index.html)
- [PostgreSQL write-ahead logging](https://www.postgresql.org/docs/current/wal-intro.html)
- [Spark tuning and data locality](https://spark.apache.org/docs/latest/tuning.html)
