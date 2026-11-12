# Paste Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Create and retrieve immutable text with optional expiry and visibility; exclude collaborative editing.

Target multi-zone availability, explicit latency SLOs, capacity estimates, and a
documented consistency model before selecting infrastructure.

## APIs and data model

POST /pastes creates content; GET /pastes/{id} reads it; DELETE marks an owned paste unavailable.

Paste(id PK, owner_id, blob_key, language, visibility, expires_at, content_hash). Store large bodies in object storage.

## High-level design

```text
client -> API -> metadata store; API -> object storage; reads -> CDN/cache
```

Use random IDs, content hashing for optional deduplication, lifecycle rules for expiry, and CDN caching only for public immutable content.

## Reliability, security, and operations

Scan size/type, cap payloads, encrypt private pastes, authorize every private read, and run deletion/expiry reconciliation.

Track create/read errors, object-store latency, expired-object backlog, abuse reports, and bytes retained.

## Key trade-off

Inline database text simplifies small pastes; object storage lowers cost and supports large bodies but adds a second consistency boundary.
