# Search Autocomplete

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Return safe, ranked prefix suggestions using popularity, freshness, locale, and optional personalization.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Suggestion(term, normalized, locale, score, updated_at); a versioned compact trie/FST is the serving artifact; events feed aggregation.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
query events -> stream aggregation/filtering -> index builder -> versioned trie -> memory serving fleet
```

Serve prefixes from memory, shard by locale/prefix, cache hot prefixes, keep top K per node, and atomically swap index versions.

## Failure, security, and observability

Remove sensitive/abusive terms before publication, fall back to the previous index, and monitor lookup p99, zero-result rate, index age, and trend churn.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Frequent incremental updates improve trend freshness; immutable batch indexes are simpler, compact, and safer to roll back.
