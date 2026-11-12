# Web Crawler

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Continuously fetch allowed pages with politeness, canonicalization, deduplication, priority, and recrawl.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

URLRecord(canonical_url, host, status, next_fetch, content_hash); per-host queues and robots/cache state drive the frontier.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
seeds/links -> URL normalizer -> distributed frontier -> fetchers -> parser/deduper -> document store/new links
```

Partition by host to enforce delay, schedule from per-host queues into a global ready set, use conditional requests, and prioritize importance/change rate.

## Failure, security, and observability

Prevent private-network access and crawler traps, cap depth/variants, checkpoint the frontier, and monitor fetch success, bytes, duplicate rate, queue age, and host fairness.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Aggressive recrawl improves freshness but wastes bandwidth and harms sites; adaptive schedules favor pages that matter and change.
