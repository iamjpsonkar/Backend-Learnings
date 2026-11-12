# Service Discovery

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Register service instances and let clients resolve healthy endpoints with rapid convergence and zone awareness.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

Agents register leases and health; clients watch or query service names and receive endpoints plus metadata.

Service(name); Instance(id, address, zone, metadata, lease_expiry, health, revision). Store authoritative state in a consensus-backed registry.

## High-level design

```text
instance agent -> registry quorum; registry -> watch stream/cache -> clients
```

Use leases and heartbeats, monotonic revisions, long-lived watches, client-side caching, and jittered reconnects to avoid thundering herds.

## Reliability, security, and operations

Keep serving last-known endpoints during brief control-plane failure, mark results stale, and require multiple failures before eviction to reduce flapping.

Measure registration/watch latency, stale clients, lease expirations, watch fan-out, registry quorum health, and endpoints per service.

## Key trade-off

Push watches converge quickly but consume connections; DNS-based discovery is universal and cacheable but has weaker freshness semantics.
