# Measurement-First Optimization Strategy

Optimization is the disciplined process of improving a measured outcome without
breaking correctness, reliability, security, or maintainability. The fastest
code change is not necessarily the best system change.

## The optimization loop

1. **Define the outcome.** Choose a user-visible or business-relevant target.
2. **Set a budget.** Examples include p95 latency, CPU per request, memory,
   database load, bundle size, cost per transaction, or energy use.
3. **Measure a baseline.** Record workload, data, environment, revision, and
   measurement method.
4. **Find the bottleneck.** Use profiles, traces, query plans, metrics, and
   controlled experiments.
5. **Form one hypothesis.** State what consumes time or resources and why a
   proposed change should improve it.
6. **Change one important thing.** Keep the experiment attributable and
   reversible.
7. **Verify the result.** Re-run the same workload and compare distributions,
   not isolated best cases.
8. **Check trade-offs.** Verify correctness, tail latency, resource use,
   reliability, and behavior under failure.
9. **Prevent regression.** Add a benchmark, performance test, metric, or budget
   to detect loss of the improvement.

Skipping measurement turns optimization into guesswork. Optimizing a component
that contributes 2% of total latency cannot deliver a 50% end-to-end reduction.

## Start with the largest source of work

Prefer optimization in this order:

1. **Remove work.** Avoid unnecessary requests, queries, parsing, rendering, or
   recomputation.
2. **Do work less often.** Cache, debounce, coalesce, precompute, or reuse.
3. **Make each unit cheaper.** Improve algorithms, data layout, query plans, and
   serialization.
4. **Move work.** Shift work off critical paths or to background processing.
5. **Parallelize safely.** Use concurrency when tasks are independent and the
   downstream system has capacity.
6. **Scale resources.** Scale vertically or horizontally after reducing waste.

Adding hardware first can hide inefficient work and increase cost without fixing
tail latency or contention.

## Select the right measurement

| Question | Measurement |
| --- | --- |
| Where does one process spend CPU time? | CPU profile |
| Which allocations retain memory? | Heap or allocation profile |
| Why is one request slow? | Distributed trace |
| Which query operation is expensive? | Query plan and database metrics |
| What do users experience? | Field latency and frontend metrics |
| What happens under concurrency? | Load test plus server telemetry |
| Did one implementation get faster? | Controlled benchmark |

Use `cProfile` to locate Python hot paths and `timeit` for controlled
microbenchmarks. A profiler answers “where is time spent?”; a benchmark answers
“which implementation is faster under this workload?”

```sh
python -m cProfile -s cumulative your_program.py
python -m timeit -s "values = list(range(1000))" "sum(values)"
```

## Latency is a distribution

Track median, p95, p99, maximum, throughput, and failures together. An average
can improve while the slowest requests become worse. Compare warm and cold
states separately because caches, connection pools, JITs, and storage caches can
change results dramatically.

For multi-service requests, end-to-end latency includes queueing, network,
application, database, cache, and downstream time. Optimize the critical path,
not the sum of every parallel branch.

## Optimization budgets

Budgets convert vague goals into engineering constraints:

- API p95 latency under expected load
- Maximum error rate at peak traffic
- CPU and memory per instance
- Database queries per transaction
- Maximum response and frontend asset sizes
- Cache hit ratio and acceptable staleness
- Cost per thousand operations
- Recovery time after a traffic spike

Budgets should be derived from user needs and service objectives. A budget is
useful only when it is measured in a representative environment.

## Common failure modes

- Measuring debug builds or unrepresentative toy data
- Timing one run instead of a distribution of repeated runs
- Comparing different workloads or environments
- Ignoring correctness differences between implementations
- Optimizing throughput while making tail latency or failures worse
- Adding caches without ownership, invalidation, or memory limits
- Adding concurrency without backpressure or downstream capacity
- Creating indexes without measuring write and storage cost
- Treating load-generator saturation as server saturation
- Keeping an optimization whose complexity exceeds its measured value

## Decision record

For each material optimization, record:

```text
Problem:
User or business impact:
Baseline workload and environment:
Baseline measurements:
Bottleneck evidence:
Proposed change:
Expected improvement:
Correctness and reliability risks:
Result:
Regression guard:
Rollback plan:
```

This record makes later regressions and trade-offs easier to understand.

## Track guides

- [Backend and runtime optimization](../02-optimization-strategies/01-backend-and-runtime-optimization.md)
- [Database and caching optimization](../02-optimization-strategies/02-database-and-caching-optimization.md)
- [Frontend and network optimization](../02-optimization-strategies/03-frontend-and-network-optimization.md)
- [Observability and capacity planning](../02-optimization-strategies/04-observability-and-capacity-planning.md)
- [Performance testing with Locust](../03-locust/01-locust-fundamentals.md)
- [Complex-systems optimization landscape](../04-complex-systems/01-optimization-landscape-and-system-laws.md)
- [Optimization decision matrix and playbooks](../04-complex-systems/19-decision-matrix-and-optimization-playbooks.md)

The runnable examples in `optimization_examples/` use only the Python standard
library and can be executed offline.
