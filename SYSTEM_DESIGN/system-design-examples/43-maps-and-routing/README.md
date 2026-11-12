# Maps and Routing

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Store road topology, ingest edits/traffic/closures, compute alternative routes, and return distance and ETA.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Road nodes/edges with geometry and access rules; versioned geographic tiles; dynamic edge-cost overlays for traffic/incidents.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
map sources -> validation/tile/graph build -> versioned graph; request -> route service -> graph partitions/cache -> ETA model
```

Use hierarchical routing such as contraction hierarchies or A*, geographic partitions with border metadata, precomputed landmarks, and short-lived route caches.

## Failure, security, and observability

Atomically roll graph versions, fall back to historical speeds, invalidate affected overlays, and monitor route latency, unreachable rate, map freshness, ETA error, and hot regions.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Heavy preprocessing speeds queries but delays map updates; dynamic overlays preserve freshness without rebuilding the base graph for every incident.
