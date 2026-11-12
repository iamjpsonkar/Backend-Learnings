# Service Architecture and Workload Shaping

Architecture determines how often work crosses ownership, process, network, and
consistency boundaries. Optimize boundaries around independent change and scale,
not fashion.

## Monolith, modules, and services

A well-structured monolith often has lower call latency, simpler transactions,
and easier profiling. Services can scale and deploy independently but add RPC,
serialization, partial failure, observability, and data ownership cost.

Split when there is a stable ownership boundary, independent scaling profile,
security boundary, failure-isolation need, or technology requirement. Recombine
chatty services or move work into the same process when those benefits vanish.

## Critical-path design

- Draw the complete dependency graph for each important journey.
- Remove sequential calls that can be eliminated, cached, or safely overlapped.
- Move analytics, notifications, indexing, and audit enrichment off the path
  when product semantics allow it.
- Replace repeated request-time joins with owned read models.
- Bound fan-out and aggregate close to the data.
- Return partial or progressive results when useful.
- Avoid synchronous calls whose only purpose is duplicating state.

## Workload shaping

- Admission control based on the resource that saturates first
- Per-tenant quotas and weighted fair sharing
- Token bucket or leaky bucket rate controls
- Concurrency limits for expensive fan-out
- Queue-based load leveling for deferrable work
- Priority classes and reserved capacity
- Request coalescing and duplicate suppression
- Batch windows with explicit maximum delay
- Graceful degradation and feature shedding

## Read and write models

- Use command-query separation when reads and writes need distinct models.
- Build materialized views asynchronously with freshness SLOs.
- Keep authoritative state and derived serving state clearly identified.
- Use event sourcing only when audit and temporal reconstruction justify its
  replay, schema evolution, and operational costs.
- Reconcile derived state and make rebuild procedures routine.

## Serverless and functions

- Keep deployment units small enough for startup goals.
- Reuse initialized clients and connections across invocations.
- Control concurrency per instance to match downstream pools.
- Provision or pre-warm capacity only when cold latency justifies the cost.
- Move large dependencies and initialization out of the request path.
- Make retry-triggered functions idempotent.

## Multi-tenancy

- Attribute resource consumption to tenant and operation.
- Prevent noisy neighbors with quotas, concurrency, pools, and partitions.
- Give exceptional tenants dedicated resources when isolation is cheaper than
  complex fairness controls.
- Normalize cost because requests can consume very different resources.
- Preserve a control path that remains available during tenant overload.

## Architecture review questions

1. Which boundary adds the most latency, bytes, failure modes, or cost?
2. Which state or call is duplicated?
3. Which component must scale independently?
4. What becomes the bottleneck after the proposed change?
5. How does the system reject, defer, or degrade excess work?
6. Can it recover while traffic continues?

## Sources

- [Azure asynchronous request-reply](https://learn.microsoft.com/en-us/azure/architecture/patterns/async-request-reply)
- [Azure performance design patterns](https://learn.microsoft.com/en-us/azure/well-architected/performance-efficiency/design-patterns)
- [Google Cloud Well-Architected Framework](https://docs.cloud.google.com/architecture/framework)
