# Measurement, Profiling, and Experimentation

Optimization begins with a reproducible workload and ends with evidence that a
user or business outcome improved. Measurements without workload, environment,
revision, and uncertainty are anecdotes.

## Define the objective

Create a performance contract containing:

- Critical user journey or background job
- Traffic mix, arrival process, concurrency, and data distribution
- Latency percentiles, throughput, errors, and freshness targets
- Resource and cost budgets per successful unit of work
- Expected peak, burst, failover, and recovery behavior
- Correctness and quality invariants that cannot be traded away

Do not optimize averages alone. Report p50, p90, p95, p99, maximum or extreme
quantiles where meaningful, and the number of observations.

## Measurement layers

| Question | Evidence |
| --- | --- |
| Did users improve? | Real-user monitoring, journey latency, outcomes |
| Which service dominates? | Distributed traces and service metrics |
| Which resource saturates? | CPU, run queue, memory, I/O, network, pools |
| Which code consumes it? | CPU, allocation, lock, I/O, and wall profiles |
| Which query or plan is slow? | Query statistics and execution plans |
| Does the change generalize? | Replay, load test, canary, controlled experiment |

## Profiling modes

- **CPU sampling:** Finds on-CPU hot paths with lower distortion than tracing
  every call.
- **Wall-clock profiling:** Includes waiting, blocking, sleep, and I/O time.
- **Allocation and heap profiling:** Finds churn, retained memory, and leaks.
- **Lock and contention profiling:** Finds serialization and oversubscription.
- **I/O profiling:** Connects latency to files, storage, sockets, and syscalls.
- **Runtime tracing:** Explains scheduling, garbage collection, and pauses.
- **Continuous profiling:** Samples production over time to expose workload and
  version-specific regressions.

Measure profiler overhead. Collect the least intrusive signal that can answer
the question, and protect sensitive payloads and symbols.

## Benchmark design

Separate three scopes:

1. **Microbenchmark:** Isolates an operation and supports fast iteration.
2. **Component benchmark:** Includes realistic dependencies and data sizes.
3. **End-to-end test:** Captures queues, network, storage, fan-out, and clients.

Control warm-up, JIT compilation, caches, CPU frequency, background work, input
distribution, affinity, and environment. Randomize trial order when drift might
bias results. Compare distributions and confidence intervals, not best runs.

## Coordinated omission and open workloads

A closed test that waits for each response can generate less traffic when the
system slows, hiding overload. For services driven by external arrivals, use an
open or controlled-arrival workload and record the intended request schedule.
Include queueing delay in the user-visible latency.

## Production experiments

- Shadow or replay representative traffic without duplicating side effects.
- Canary by instance, tenant, region, or request cohort.
- Use feature flags and immediate rollback criteria.
- Compare equivalent cohorts and account for seasonality.
- Watch downstream work, retries, cache hit rate, and resource cost.
- Continue through steady state; cold starts can misrepresent the result.

## Performance regression gates

Use layered gates rather than one fragile number:

- Stable microbenchmarks for important primitives
- Component budgets for critical endpoints and queries
- Scenario load tests for saturation and overload behavior
- Canary SLO and resource comparisons
- Post-deployment observation across representative traffic cycles

Never block delivery on noisy measurements without reruns, tolerance bands, and
a named owner who can diagnose the result.

## Optimization record

Record baseline, hypothesis, intervention, exact workload, measurement method,
result, uncertainty, trade-offs, rollback plan, and follow-up guardrail. This
turns performance work into cumulative engineering knowledge.

## Sources

- [Python profilers](https://docs.python.org/3/library/profile.html)
- [Go diagnostics](https://go.dev/doc/diagnostics)
- [OpenTelemetry performance benchmark guidance](https://opentelemetry.io/docs/specs/otel/performance-benchmark/)
