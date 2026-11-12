# Distributed Cache

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Provide get/set/delete, TTL, eviction, replication, and horizontal rebalancing for ephemeral data.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

GET/SET/DELETE support optional TTL and compare-and-set; multi-key atomicity is out of scope.

Entry(key, value, version, expires_at). A routing ring maps key hashes to a primary and replicas; metadata has membership epochs.

## High-level design

```text
client -> routing library/proxy -> primary cache node -> replica nodes
```

Use consistent hashing with virtual nodes, segmented LRU/LFU eviction, TTL jitter, request coalescing, and gradual data movement during rebalance.

## Reliability, security, and operations

Acknowledge after the selected replication level, fence stale primaries with epochs, cap item size, and serve misses rather than unsafe stale values.

Measure hit ratio, eviction rate, memory fragmentation, hot keys, replication lag, rebalance traffic, and tail latency.

## Key trade-off

Client-side routing is fast but hard to upgrade; a proxy centralizes policy but adds a hop. Strong replication costs latency for disposable data.
