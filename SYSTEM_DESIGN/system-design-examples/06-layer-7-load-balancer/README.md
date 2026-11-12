# Layer 7 Load Balancer

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Terminate HTTP/TLS, select healthy upstreams, reuse connections, and apply routing and retry policy.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

Listeners map host/path/header rules to pools; health checks and weighted rollout configuration are dynamically distributed.

Config snapshots contain listeners, routes, clusters, endpoints, weights, timeouts, and versions; request data remains stateless.

## High-level design

```text
client -> edge LB -> selected backend; control plane -> validated config snapshot -> LB fleet
```

Use least-loaded or power-of-two-choices selection, locality preferences, connection pooling, circuit breakers, and bounded retry budgets.

## Reliability, security, and operations

Run active and passive health checks, preserve the last-known-good config, drain connections on removal, and retry only idempotent requests within a deadline.

Track requests, backend errors, retries, ejections, active connections, config age, TLS failures, and per-route p99 latency.

## Key trade-off

Aggressive health checks react quickly but can cause flapping; retries hide transient faults but amplify overload unless budgeted.
