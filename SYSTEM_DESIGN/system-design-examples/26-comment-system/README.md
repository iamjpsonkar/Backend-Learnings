# Comment System

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Create threaded comments, edit/delete, vote, moderate, rank, and paginate stable views.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Comment(id, object_id, parent_id, author, body, state, created_at); Vote(comment,user,value); counters/ranks are derived.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
client -> comment API -> transactional store -> event log -> moderation/ranking/cache
```

Partition by parent object, cap nesting or materialize paths, update counters asynchronously, and use rank-plus-ID cursor pagination.

## Failure, security, and observability

Deduplicate votes with a unique key, preserve tombstones, sanitize content, audit moderation, and monitor write/read latency, hot threads, moderation age, and rank lag.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Synchronous counters are exact but contend on hot threads; asynchronous counters scale with temporary staleness.
