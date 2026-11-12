# URL Shortener

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Create short links, redirect readers, support custom aliases and expiry; exclude analytics dashboards.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

POST /links creates an alias; GET /{alias} returns a 302/307 redirect; DELETE /links/{alias} disables it.

Link(alias PK, destination, owner_id, created_at, expires_at, status). Keep alias lookups in a distributed cache backed by a sharded key-value store.

## High-level design

```text
client -> edge -> redirect service -> cache -> link store
```

Generate Base62 aliases from random 64-bit values and retry on collision. Cache popular links, use negative caching briefly, and partition by alias hash.

## Reliability, security, and operations

Use idempotency keys on creation, protect redirect resolution from loops and unsafe schemes, rate-limit creation, and replicate link data across zones.

Measure redirect p95/p99, cache hit ratio, creation collisions, hot keys, and invalid destinations.

## Key trade-off

Random IDs avoid predictability but need collision checks; counter-based IDs are compact but require coordination and obfuscation.
