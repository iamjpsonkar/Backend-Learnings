# Observability, Capacity, and Continuous Optimization

Optimization at scale is a control system: observe demand and service behavior,
compare them with objectives, change one lever, and retain enough history to
detect regressions and drift.

## Signal design

- Metrics describe rates, distributions, saturation, and trends.
- Traces attribute end-to-end latency and critical-path fan-out.
- Logs explain discrete state changes and failures.
- Profiles attribute CPU, allocation, lock, and resource cost to code.
- Business signals show whether technical improvements create value.

Correlate service, version, region, route, tenant class, and trace context while
controlling cardinality. Never put raw user IDs, request IDs, or unbounded error
strings in metric labels.

## Golden signals and resources

Track request or work rate, successful throughput, latency distribution, errors,
and saturation. Add CPU steal and throttling, run queue, allocation, GC, RSS,
page faults, storage queue, network retransmits, connection wait, queue age,
replication lag, and cache hit or eviction where relevant.

## Critical-path tracing

- Instrument logical operations rather than every internal function.
- Propagate context through queues and asynchronous boundaries.
- Record request size, result size, retry count, and outcome with bounded values.
- Use span links for fan-in, batches, and causal asynchronous work.
- Sample enough errors and slow traces to diagnose tails.
- Use tail sampling when decisions require the complete trace.

Sampling controls telemetry overhead but can bias analysis. Document sampler
behavior and preserve aggregate metrics for unsampled traffic.

## Continuous profiling

- Sample representative instances rather than profiling the entire fleet at
  high intensity.
- Collect CPU, allocation, lock, and wall profiles separately when their
  mechanisms interfere.
- Compare profiles by release, route, and workload class.
- Retain build identifiers so symbols match deployed binaries.
- Connect profile samples to trace context where supported.
- Measure collector overhead and secure profile data.

## Capacity model

For each constrained resource define:

```text
demand = arrival rate × resource cost per operation
required capacity = demand / target utilization
```

Model each operation class separately, include redundancy and failover, and use
measured service demand rather than raw utilization alone. Forecast seasonal,
launch, organic, and tenant-specific growth with confidence ranges.

## Headroom policy

Headroom must cover burst variance, autoscaling delay, deployments, maintenance,
imbalance, dependency degradation, and failure-domain loss. Define separate
normal, peak, degraded, and recovery envelopes.

## Performance ownership

- Assign owners to SLOs, budgets, dashboards, benchmarks, and capacity models.
- Review the top resource and latency contributors on a regular cadence.
- Make performance changes visible in release and architecture reviews.
- Track improvements as cost or resource per successful business unit.
- Maintain a backlog ranked by expected system impact and evidence strength.

## Sources

- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
- [OpenTelemetry tracing sampling](https://opentelemetry.io/docs/specs/otel/trace/sdk/)
- [OpenTelemetry profiles](https://opentelemetry.io/docs/specs/otel/profiles/)
