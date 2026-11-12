# Backend and Runtime Optimization

Backend performance is shaped by work per request, algorithms, memory behavior,
I/O, serialization, queues, and downstream dependencies. Profile before choosing
a technique.

## Algorithms and data structures

Changing complexity usually beats micro-optimizing syntax:

- Replace repeated list membership with a set or dictionary lookup.
- Avoid nested scans when data can be indexed by key.
- Use heaps for repeated minimum or maximum selection.
- Stream large inputs instead of loading all data into memory.
- Maintain aggregates incrementally instead of recomputing them.

Run the algorithm demonstration:

```sh
python optimization_examples/algorithmic_complexity.py
```

The two implementations return identical results, but one builds a set for
near-constant-time membership checks.

## Benchmarking code changes

A useful microbenchmark:

- Verifies equivalent output first.
- Uses representative input sizes and distributions.
- Repeats enough times to see normal variation.
- Reports a median or distribution, not only the fastest run.
- Avoids unrelated setup inside the timed region.
- Does not claim end-to-end impact without system measurement.

Run the benchmarking example:

```sh
python optimization_examples/benchmarking.py
```

For whole-program CPU profiling, use:

```sh
python -m cProfile -s cumulative your_program.py
```

Use an allocation or heap profiler when memory growth, garbage collection, or
retained objects are the concern.

## Reduce work per request

- Validate and normalize data once at the boundary.
- Avoid repeated parsing, regular-expression compilation, and configuration
  loading.
- Select only required fields from databases and downstream APIs.
- Paginate or stream unbounded collections.
- Precompute stable derived values.
- Reuse HTTP and database connections through bounded pools.
- Avoid logging large payloads on normal success paths.

## I/O and concurrency

Concurrency helps when work waits on independent I/O. It does not make CPU work
free and can overload databases or downstream APIs.

Before increasing concurrency, define:

- Maximum in-flight work
- Queue length and timeout
- Per-dependency concurrency limits
- Retry budget and backoff
- Cancellation behavior
- Overload response

Use bounded concurrency and backpressure. An unbounded queue converts a traffic
spike into high memory use and extreme latency.

## Batching

Batching reduces network round trips, transaction overhead, and per-call setup.
It trades lower overhead for additional waiting and larger failure units.

```sh
python optimization_examples/batching.py
```

Choose a batch size using payload limits, latency budget, memory, and downstream
capacity. Flush on either size or time so low traffic does not wait forever.

## API optimization

- Keep payloads purpose-specific and compress sufficiently large responses.
- Use conditional requests or version tokens when clients can reuse data.
- Avoid chatty client workflows that require many serial round trips.
- Provide bulk APIs for legitimate bulk operations.
- Use stable pagination; keyset pagination often scales better than deep offsets.
- Set explicit timeouts for every network call.
- Retry only transient failures and only when the operation is safe or
  idempotent.

Retries multiply load during incidents. Apply exponential backoff, jitter, retry
limits, and a total deadline.

## Memory optimization

- Measure retained memory and allocation rate separately.
- Use iterators for streaming transformations.
- Bound caches, queues, buffers, and per-request accumulation.
- Release references to large objects when their lifetime ends.
- Avoid copying large byte or string payloads unnecessarily.
- Investigate leaks by comparing heap snapshots over time.

Lower allocation rate can improve CPU and tail latency by reducing garbage
collection pressure even when peak memory is unchanged.

## Off-critical-path work

Move nonessential email, analytics, indexing, thumbnails, and enrichment to
background processing when the user does not need the result synchronously.

An asynchronous design still needs:

- Durable delivery requirements
- Idempotent handlers
- Retry and dead-letter behavior
- Queue-age and failure monitoring
- Backpressure and admission control
- A user-visible consistency model

Moving work to a queue changes latency and failure semantics; it does not remove
the work.
