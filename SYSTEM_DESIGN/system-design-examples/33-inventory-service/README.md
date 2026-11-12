# Inventory Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Track on-hand, available, reserved, and sold units by SKU/location with expiring checkout reservations.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Stock(sku,location,on_hand,version); Reservation(id,sku,location,qty,expires_at,state); immutable adjustments support audit.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
checkout -> inventory command shard -> reservation/stock store -> expiry queue; warehouse events -> adjustments
```

Serialize changes per SKU/location, shard by that key, use atomic conditional updates, spread hot SKU demand, and reconcile against warehouse truth.

## Failure, security, and observability

Idempotent commands and fencing prevent duplicate release/commit; durable expiry and repair jobs handle crashes. Monitor reservation conflicts, oversell, expiry lag, and drift.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Strong reservation consistency prevents oversell but can reject during partitions; accepting backorders favors availability with business consequences.
