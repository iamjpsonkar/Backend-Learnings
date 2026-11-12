# Concurrency, Scheduling, and Backpressure

Concurrency improves utilization when work can overlap, but unbounded
concurrency converts variable demand into queueing, memory growth, contention,
and collapse. Treat every concurrency boundary as a resource budget.

## Choose the execution model

| Workload | Useful model |
| --- | --- |
| CPU-bound independent work | Fixed process or thread pool near available cores |
| High-concurrency I/O | Async I/O, event loop, lightweight or virtual threads |
| Long blocking operations | Bounded dedicated pool or asynchronous interface |
| Ordered stateful events | Partitioned single-writer loops |
| Large batch computation | Data-parallel workers with locality-aware scheduling |

The best model depends on runtime, libraries, cancellation support, debugging,
and workload. Async does not make CPU work faster, and more threads do not
create more CPU.

## Bound every resource

Set explicit limits for:

- In-flight requests per instance, endpoint, tenant, and dependency
- Worker, thread, process, coroutine, and task counts
- Database, cache, HTTP, and RPC connection pools
- Queue count, depth, bytes, and maximum age
- Fan-out width and nested parallelism
- Request and response bytes, batch size, and execution time

A bounded system can reject or defer work. An unbounded system eventually lets
memory or latency choose the limit.

## Backpressure strategies

- Stop reading when downstream capacity is exhausted.
- Use bounded queues with explicit full behavior.
- Propagate demand or credits from consumer to producer.
- Reduce producer rate with adaptive concurrency or rate control.
- Spill durable asynchronous work to an external log or queue.
- Coalesce redundant updates or keep only the newest value where valid.
- Drop low-value or stale work before expensive processing.

Backpressure must cross service boundaries. A bounded local queue is ineffective
if upstream retries immediately or another buffer grows without limit.

## Scheduling strategies

- Separate latency-sensitive and bulk workloads.
- Use priority queues with aging to prevent starvation.
- Apply weighted fair sharing between tenants and work classes.
- Reserve capacity for control-plane, health, and recovery operations.
- Schedule by cost, deadline, or shortest remaining work when the semantics
  allow it.
- Place work near its data and avoid synchronized global barriers.
- Limit nested parallel libraries to prevent worker multiplication.

## Contention reduction

- Partition mutable state and use single-writer ownership.
- Reduce critical-section size and move I/O outside locks.
- Prefer immutable snapshots or copy-on-write for read-heavy state.
- Use sharded counters and aggregate periodically.
- Replace global queues and allocators with per-core or per-worker structures.
- Batch coordination and acknowledgements.
- Measure lock wait, scheduler delay, run-queue depth, and context switches.

Lock-free structures can move complexity into retries, memory ordering, and
reclamation. Use them only when contention evidence justifies that cost.

## Cancellation and deadlines

Propagate deadlines through every call and stop work when results are no longer
useful. Cancellation must release locks, pool slots, memory, and downstream
work. Avoid launching speculative or fan-out work that outlives its parent.

## Failure modes

- Thread-pool starvation from mixing blocking and nonblocking tasks
- Deadlock, livelock, priority inversion, and starvation
- Queue growth that hides overload until latency is unrecoverable
- Excess tasks increasing cache misses and context switching
- Backpressure applied after costly parsing, authentication, or allocation
- Autoscaling consumers without respecting downstream capacity

## Sources

- [Azure queue-based load leveling](https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling)
- [Java virtual threads](https://docs.oracle.com/en/java/javase/26/core/virtual-threads.html)
- [gRPC deadlines](https://grpc.io/docs/guides/deadlines/)
