# Algorithms, CPU, and Compiler Optimization

The fastest instruction is the one the system does not execute. Improve work
complexity and representation before tuning syntax or processor details.

## Algorithmic strategies

- Replace repeated scans with hash, tree, bitmap, trie, or spatial indexes.
- Use heaps for repeated top-k and priority operations.
- Sort once when it replaces many expensive searches or comparisons.
- Maintain incremental aggregates instead of recomputing full results.
- Use dynamic programming or memoization for overlapping subproblems.
- Approximate with sketches, sampling, Bloom filters, or quantiles when the
  accuracy contract allows it.
- Use branch-and-bound, pruning, and early termination to avoid useless work.
- Stream external-memory algorithms when the working set exceeds memory.
- Exploit sparsity rather than processing absent or zero values.

Analyze time, space, I/O, communication, and worst-case behavior. An algorithm
with better asymptotic complexity can still lose on small inputs or poor
locality, so benchmark the real distribution.

## Representation and data layout

- Prefer contiguous arrays for scans and vector operations.
- Choose structure-of-arrays when operations touch a few fields across many
  records; choose array-of-structures when each operation needs one full record.
- Pack booleans and low-cardinality values where decoding cost is acceptable.
- Replace pointer-heavy objects with compact values in memory-bound hot paths.
- Normalize or intern repeated strings carefully to reduce duplication.
- Align data and avoid false sharing between frequently written fields.

## CPU pipeline strategies

- Reduce unpredictable branches in hot loops.
- Hoist invariants and remove repeated bounds, parsing, and conversion work.
- Combine passes over the same data when it improves cache locality.
- Vectorize independent operations with SIMD-capable libraries.
- Use blocked or tiled algorithms so active data fits in cache.
- Prefetch only after evidence shows predictable memory stalls.
- Avoid oversubscription when libraries create their own worker threads.

Instruction count alone is insufficient. Measure cycles, instructions per
cycle, branch misses, cache misses, context switches, and stalled time.

## Compilation strategies

- Use optimized release builds and disable debug assertions in production.
- Enable link-time optimization where build time and debuggability allow it.
- Use profile-guided optimization with representative production profiles.
- Verify vectorization and inlining reports instead of assuming they occurred.
- Remove accidental dynamic dispatch or boxing only on demonstrated hot paths.
- Re-evaluate hand tuning after compiler or runtime upgrades.

## Runtime-specific considerations

- Warm up JIT-compiled code before measuring steady state.
- Separate startup, cold execution, and steady-state goals.
- Track deoptimization, code-cache pressure, and tiered compilation where
  supported.
- In interpreted runtimes, move proven hot loops to optimized built-ins,
  vectorized libraries, native extensions, or a compiled service only when the
  operational trade-off is justified.

## Approximation and quality trade-offs

Approximation can dominate exact optimization:

- Sample large populations.
- Return top-k rather than a fully sorted result.
- Use bounded-error sketches for counts and percentiles.
- Reduce model, image, audio, or search fidelity under tight budgets.
- Stop iterative solvers when marginal quality improvement is small.

Define an explicit error or quality budget and test adversarial distributions.

## Common mistakes

- Changing algorithms without preserving ordering or numerical behavior
- Applying SIMD to data dominated by memory transfer
- Parallelizing work whose coordination cost exceeds its compute cost
- Trusting synthetic uniform inputs that omit skew and adversarial cases
- Trading readable code for an unmeasured micro-optimization

## Sources

- [Go profile-guided optimization](https://go.dev/doc/pgo)
- [Linux perf documentation](https://docs.kernel.org/admin-guide/perf-security.html)
- [Python timeit](https://docs.python.org/3/library/timeit.html)
