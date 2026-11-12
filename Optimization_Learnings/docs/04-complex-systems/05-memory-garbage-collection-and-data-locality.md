# Memory, Garbage Collection, and Data Locality

Memory performance is governed by allocation rate, live-set size, object layout,
cache and NUMA locality, reclamation, and paging. Optimize physical working-set
behavior rather than one headline heap number.

## Diagnose the memory problem

Distinguish:

- **Leak:** Retained objects grow without a valid owner.
- **Churn:** High allocation rate creates allocator or GC work.
- **Bloat:** Representation uses far more bytes than the underlying data.
- **Fragmentation:** Free memory exists but cannot satisfy or return pages.
- **Working-set excess:** Active data does not fit available physical memory.
- **Poor locality:** Useful data causes excessive cache, TLB, or NUMA misses.
- **Unbounded buffering:** Queues, caches, or fan-out retain growing state.

Use allocation profiles, heap snapshots, retained-object graphs, RSS, page
faults, swap activity, cache misses, and GC telemetry together.

## Reduce allocation and retention

- Avoid temporary collections, strings, and serialization copies.
- Stream and incrementally parse large payloads.
- Reuse buffers only with strict ownership and bounded pools.
- Store compact primitive values instead of many wrapper objects.
- Clear references held by registries, callbacks, thread locals, and caches.
- Bound caches by bytes as well as entry count.
- Use weak references only when their nondeterministic lifetime is acceptable.
- Release large buffers before long waits and across asynchronous boundaries.

Pooling can retain peak memory, increase contention, and expose stale data.
Benchmark it against the runtime allocator before adopting it.

## Improve locality

- Keep hot fields and values contiguous.
- Separate hot and cold fields when most operations use only a subset.
- Process data in tiles that fit cache.
- Partition workers and memory by NUMA node where cross-node access is costly.
- Avoid false sharing by separating independently written counters.
- Prefer sequential access and compact indexes over pointer chasing.
- Co-locate compute and data instead of copying large working sets.

## Garbage-collected runtimes

Tune in this order:

1. Confirm GC is material to latency or CPU.
2. Reduce allocation rate and live-set size.
3. Remove accidental retention and oversized caches.
4. Choose a collector matching pause, throughput, and footprint goals.
5. Size heap and memory limits with native and container overhead included.
6. Tune collector controls using representative load.
7. Re-check tail latency, throughput, and out-of-memory behavior.

Larger heaps can reduce collection frequency but increase footprint and some
pause or recovery costs. Low-pause collectors can spend more concurrent CPU.

## Native memory

Track heap plus stacks, code, mapped files, direct buffers, allocator arenas,
GPU memory, shared memory, and kernel buffers. Use sanitizers and lifetime tools
for corruption and leaks. Consider allocator selection only after profiles show
allocator contention or fragmentation.

## Operating-system controls

- Prevent swapping for strict-latency in-memory services when appropriate.
- Configure container requests and limits from measured working sets.
- Leave headroom for page cache and kernel memory.
- Evaluate huge pages for large stable mappings; measure TLB benefit and
  allocation side effects.
- Avoid memory limits that trigger repeated reclaim before termination.

## Sources

- [Go garbage collector guide](https://go.dev/doc/gc-guide)
- [Java garbage collection tuning](https://docs.oracle.com/en/java/javase/21/gctuning/introduction-garbage-collection-tuning.html)
- [Python tracemalloc](https://docs.python.org/3/library/tracemalloc.html)
