# Product Catalog

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Manage products, variants, flexible attributes, categories, media, and seller updates for read-heavy traffic.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Product(id,seller,category,version,status); Variant(id,product,attributes,price_ref); typed category schemas validate attributes.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
admin/seller -> catalog write DB -> change log -> search/cache/read models -> clients
```

Partition writes by product/seller, build denormalized read documents, version media, and update search asynchronously with reconciliation.

## Failure, security, and observability

Authorize sellers, moderate content, validate schemas, preserve history, and monitor write-to-read/search lag, schema failures, cache hits, and missing media.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

A flexible document model accelerates category growth; typed schemas and normalized core fields improve validation and query consistency.
