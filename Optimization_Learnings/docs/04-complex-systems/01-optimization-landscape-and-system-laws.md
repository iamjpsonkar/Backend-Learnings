# Optimization Landscape and System Laws

Large-system optimization is the search for the best end-to-end outcome under
constraints. The target may be latency, throughput, freshness, availability,
cost, energy, or a weighted combination. A local speedup is useful only when it
improves the system objective without violating correctness or another budget.

## The complete lever set

Nearly every useful optimization applies one or more of these levers:

| Lever | Meaning | Examples |
| --- | --- | --- |
| Eliminate | Stop doing unnecessary work | Dead code, duplicate queries |
| Reduce | Process less data or fewer instructions | Projection, pruning |
| Reuse | Avoid repeating completed work | Cache, memoization, pooling |
| Precompute | Move work before the critical path | Materialized view, index |
| Defer | Move nonessential work after the response | Async audit, lazy load |
| Batch | Amortize setup and round-trip costs | Bulk writes, vectorization |
| Parallelize | Use independent resources concurrently | Workers, partitions |
| Pipeline | Overlap stages instead of waiting serially | Streaming, prefetching |
| Localize | Move computation closer to data or users | Data locality, edge cache |
| Compress | Trade compute for fewer stored/transferred bytes | Zstandard, images |
| Specialize | Match hardware or service to the workload | GPU, column store |
| Partition | Split work or state into independently scalable units | Shards |
| Replicate | Add read capacity and locality | Read replicas, CDN |
| Bound | Prevent unbounded resource growth | Queues, pools, deadlines |
| Shed | Reject excess or low-value work | Admission control |
| Degrade | Serve a cheaper acceptable result | Reduced fidelity |
| Scale | Change available capacity | Vertical, horizontal, elastic |

## Fundamental laws

### Amdahl's law

If fraction `P` of work can be accelerated by factor `S`, total speedup is:

```text
speedup = 1 / ((1 - P) + P / S)
```

Optimizing a small fraction has a hard ceiling. Profile end to end and target
the dominant contribution rather than the most visible function.

### Little's law

For a stable system:

```text
concurrency = throughput × average time in system
```

At 2,000 requests per second and 100 ms average latency, about 200 requests are
in flight. This connects latency to connection pools, memory, queue capacity,
and downstream concurrency.

### Utilization and queueing

Latency rises nonlinearly as utilization approaches saturation. Operating a
critical resource at its theoretical maximum leaves no room for variance,
bursts, failover, maintenance, or imperfect load balancing. Capacity targets
need explicit headroom and an overload mode.

### Tail latency amplification

Fan-out makes the slowest dependency matter. A request that waits for many
parallel calls has a higher chance of encountering a slow call. Reduce fan-out,
bound it, use deadlines, avoid synchronized work, and measure end-to-end tails.

### Coordination has a cost

Parallel speedup is limited by serialization, locks, communication, skew, and
barriers. More workers can reduce throughput when contention and coordination
grow faster than useful work.

## Optimization hierarchy

Use the highest-leverage safe layer first:

1. Remove unnecessary product or business work.
2. Improve algorithms, data models, and access patterns.
3. Remove cross-service and storage round trips.
4. Bound concurrency, queues, retries, and fan-out.
5. Improve locality, batching, caching, and serialization.
6. Tune runtimes, databases, kernels, and infrastructure.
7. Add capacity only after the workload and bottleneck are understood.
8. Apply micro-optimizations to measured hot paths last.

## Constraints to preserve

For every change record its effect on:

- Correctness, consistency, durability, and data loss risk
- Security, privacy, isolation, and abuse resistance
- Availability, recoverability, and operational complexity
- Median and tail latency, throughput, and freshness
- CPU, memory, storage, network, and accelerator utilization
- Unit economics, energy per unit of work, and team maintenance cost

## Sources

- [Google SRE: addressing cascading failures](https://sre.google/sre-book/addressing-cascading-failures/)
- [AWS Performance Efficiency Pillar](https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html)
- [Azure performance design patterns](https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/design-patterns)
