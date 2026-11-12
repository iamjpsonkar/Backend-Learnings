# Nearby-Place Search

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Search geographic entities by radius/viewport, attributes, open status, text relevance, and distance.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Place(id,location,category,attributes,hours,version); geospatial/text index documents are derived from authoritative place records.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
writes -> place DB/change log -> geo/text indexes; query -> cell cover -> filter/rank -> stable cursor
```

Index with S2/H3/geohash cells at multiple resolutions, query covering cells, oversample then exact-distance filter, and cache common map tiles.

## Failure, security, and observability

Version index updates, tolerate partial shards, moderate place data, and monitor freshness, candidate counts, dense-cell latency, empty results, and relevance.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Small cells reduce candidates but increase fan-out; larger cells reduce fan-out while scanning more irrelevant places.
