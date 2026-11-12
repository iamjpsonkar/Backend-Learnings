# API Gateway

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Route external API traffic while applying authentication, quotas, transformations, policy, and observability.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

Match requests to versioned routes; validate identity and schema; proxy within a deadline; return consistent errors.

RouteConfig(host, path, method, upstream, auth_policy, quota, timeout, version). Store no business state in the data plane.

## High-level design

```text
client -> edge/WAF -> gateway -> service; control plane -> signed route snapshot -> gateway fleet
```

Keep gateways stateless, cache keys and policies, reuse upstream connections, isolate tenant budgets, and scale on concurrency and CPU.

## Reliability, security, and operations

Use circuit breakers, load shedding, last-known-good config, request IDs, and idempotency-aware retries. Never retry streaming or non-idempotent bodies blindly.

Track per-route traffic, auth failures, throttles, upstream latency, retry amplification, config age, and gateway saturation.

## Key trade-off

Central policy simplifies governance but increases coupling; service-owned policy is flexible but risks inconsistency and duplicated controls.
