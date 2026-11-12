# Resilience, Overload, and Tail Latency

Performance under failure matters more than peak benchmark throughput. A robust
system completes the most valuable useful work, rejects excess demand cheaply,
and recovers without waiting for all traffic to disappear.

## Overload control order

1. Know the tested safe operating envelope.
2. Detect the actual saturating resource with low-latency signals.
3. Reject excess work before expensive parsing, allocation, or fan-out.
4. Protect dependencies with concurrency and rate limits.
5. Prefer important work with fairness and priority.
6. Degrade optional features and response fidelity.
7. Shed enough load for the reduced healthy capacity to recover.
8. Add capacity without forwarding overload to the next dependency.

## Timeouts and deadlines

- Set a total user-visible deadline.
- Allocate budgets across hops while preserving time for response and cleanup.
- Propagate remaining time rather than resetting a full timeout per hop.
- Cancel downstream work when the result is no longer useful.
- Use shorter connect timeouts than complete-operation deadlines.
- Measure false timeout rate and work completed after caller abandonment.

## Retry discipline

- Retry only transient, idempotent or safely deduplicated operations.
- Use exponential backoff with jitter.
- Limit attempts and total elapsed time.
- Enforce a retry budget across the client or service.
- Retry at one responsible layer, not every layer.
- Honor server retry guidance and stop retrying overload blindly.
- Monitor attempts per original request.

Three extra attempts at three layers can multiply one operation into dozens of
dependency calls. Retries consume the capacity needed for recovery.

## Circuit breaking and isolation

- Open circuits based on meaningful recent failure and latency signals.
- Probe recovery with limited half-open traffic.
- Separate pools by dependency, tenant, and work class.
- Do not let one slow backend consume every worker or connection.
- Keep circuit state scoped enough to avoid global overreaction.
- Use fallback only when it is cheaper and semantically acceptable.

## Tail controls

- Remove serial dependencies and reduce fan-out.
- Hedge only idempotent requests after a percentile-based delay and under a
  strict extra-load budget.
- Use quorum responses when not every replica result is required.
- Rebalance hotspots and slow partitions.
- Apply request cost limits to adversarial or pathological inputs.
- Warm code, connections, caches, and replicas gradually.

## Graceful degradation

Predefine levels such as:

- Skip recommendations, enrichment, or secondary lookups.
- Serve stale or cached data with visible freshness semantics.
- Reduce search breadth, model size, media quality, or result count.
- Disable expensive writes, exports, or background recomputation.
- Preserve login, checkout, control, and recovery paths.

Feature flags must work during incidents without a normal deployment.

## Resilience testing

Test overload, dependency slowness, partial packet loss, cache loss, replica lag,
retry storms, rolling restart, zone loss, cold recovery, queue backlog, and
traffic restoration. Verify recovery time and useful throughput, not only that
errors were produced.

## Sources

- [Google SRE: addressing cascading failures](https://sre.google/sre-book/addressing-cascading-failures/)
- [Google SRE service best practices](https://sre.google/sre-book/service-best-practices/)
- [Azure throttling pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/throttling)
- [gRPC retry guidance](https://grpc.io/docs/guides/retry/)
