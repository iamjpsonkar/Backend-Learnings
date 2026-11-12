# Observability and Capacity Planning

Optimization requires evidence across the request path. Observability combines
metrics, traces, logs, profiles, and context so engineers can explain system
behavior rather than only notice that it is slow.

## Signals

- **Metrics:** Aggregated numeric measurements over time.
- **Traces:** The path and timing of work across components.
- **Logs:** Timestamped events with diagnostic context.
- **Profiles:** Code-level CPU, allocation, lock, or resource usage.

Correlate signals with service, environment, version, region, route, and trace
identifiers. Avoid unbounded metric labels such as raw user IDs or request IDs.

## Service indicators

Start with user-visible indicators:

- Request rate
- Error rate
- Latency distribution
- Availability or successful outcome rate
- Queue age for asynchronous workflows
- Data freshness where staleness matters

An SLI is a measured indicator. An SLO is the objective for that indicator.
Alerts should identify meaningful risk to objectives rather than every noisy
internal fluctuation.

## Resource and saturation signals

For each constrained resource, observe utilization, saturation, and errors:

- CPU utilization, throttling, and run queue
- Memory working set, allocation, garbage collection, and out-of-memory events
- Disk latency, throughput, queue depth, and capacity
- Network throughput, retransmission, connection errors, and limits
- Thread, process, connection-pool, and file-descriptor usage
- Database locks, active sessions, buffer/cache behavior, and replication lag
- Queue depth, oldest-message age, processing rate, and retries

High utilization is not automatically a problem. Saturation means demand is
waiting because a resource cannot immediately serve it.

## Dashboard design

A useful service dashboard answers:

1. Is the user-visible service healthy?
2. Which routes, tenants, versions, or regions are affected?
3. Is demand abnormal?
4. Which resource or dependency is saturated?
5. Did a deploy or configuration change coincide with the regression?

Pair rates with denominators. “100 failures” means little without total requests
and time window.

## Capacity model

Record capacity using a defined workload and acceptance criteria:

```text
Software revision and configuration
Instance shape and count
Database/cache/dependency configuration
Dataset size and distribution
User journeys and task ratios
Steady-state request rate
Peak request rate
Latency percentiles and error rate
CPU, memory, network, and pool utilization
Headroom and failure point
```

Capacity is workload-specific. A service may handle many cached reads but far
fewer write-heavy transactions.

## Headroom and scaling

Plan headroom for traffic variation, instance failure, deployments, background
jobs, dependency slowdown, and scaling delay. Autoscaling reacts after a signal
changes and therefore cannot replace capacity planning.

When scaling horizontally, verify:

- Load distribution is balanced.
- Shared databases and caches can absorb the increased demand.
- Connection counts do not grow beyond downstream limits.
- Stateful sessions and local caches behave correctly.
- Scale-down drains work safely.
- Startup and warm-up time fit the response objective.

## Queueing and overload

As utilization approaches a constrained resource's capacity, queueing delay can
grow sharply. Protect the system with:

- Bounded queues
- Admission control and rate limits
- Deadlines and timeouts
- Load shedding for noncritical work
- Per-tenant fairness
- Circuit breakers for unhealthy dependencies
- Retry budgets with exponential backoff and jitter

Rejecting excess work quickly can preserve useful service for accepted requests.

## Experiment and rollout safety

- Establish baseline telemetry before the change.
- Use a canary or controlled cohort.
- Compare equivalent traffic and data.
- Watch correctness, failures, tail latency, and resource cost.
- Define automatic rollback conditions.
- Continue monitoring after caches and traffic patterns stabilize.

## Connecting observability to Locust

During a Locust run, align test timestamps with server telemetry. Annotate the
dashboard with ramp stages and deploy versions. Correlate Locust latency and
failures with traces, database plans, pool waits, queue depth, and host metrics.

Locust shows the client-observed outcome. It cannot by itself explain which
internal component caused that outcome.

See the OpenTelemetry documentation for
[signals](https://opentelemetry.io/docs/concepts/signals/) and the
[observability primer](https://opentelemetry.io/docs/concepts/observability-primer/).
