# Hotel Reservation

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Search properties/rates, check allocation, hold/book rooms, cancel, and synchronize partner inventory.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Inventory(property,room_type,date,available,version); RatePlan; Hold; Reservation; partner messages carry source/version.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
search -> denormalized index -> availability service -> hold -> payment -> reservation; partner feeds -> reconciliation
```

Partition inventory by property/date range, cache broad search but revalidate before hold, use atomic decrements, and isolate partner adapters.

## Failure, security, and observability

Idempotent partner messages, expiring holds, compensations, overbooking policy, and reconciliation handle stale allocations and ambiguous replies.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Preallocated partner inventory enables local strong decisions; live partner calls improve freshness but add latency and dependency risk.
