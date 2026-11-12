# Distributed Rate Limiter

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Enforce user, tenant, IP, and endpoint quotas with burst support across many gateway instances.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

The gateway calls check(key, policy, cost) and receives allowed, remaining, and retry_after; policy updates are versioned.

Policy(scope, limit, window, burst); Counter(key, bucket, count, expires_at). Keep counters in an atomic in-memory store.

## High-level design

```text
request -> gateway -> local policy cache -> regional counter cluster -> allow or reject
```

Use token bucket for bursts or sliding-window counters for accuracy. Shard counters by hashed identity and batch low-risk usage locally.

## Reliability, security, and operations

Fail open only for low-risk endpoints; fail closed for sensitive operations. Bound clock skew, replicate counters, and attach policy versions to decisions.

Measure decision latency, reject rate, counter-store saturation, policy staleness, and fail-open decisions per tenant.

## Key trade-off

Strict global quotas require cross-region coordination; regional budgets reduce latency and remain available but can overshoot the global limit.
