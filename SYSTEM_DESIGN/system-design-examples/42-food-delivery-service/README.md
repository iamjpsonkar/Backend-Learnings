# Food-Delivery Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Manage menus, carts, restaurant acceptance, courier dispatch, pickup, delivery, payment, and live status.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Order(id,state,restaurant,courier,version); MenuItem(version); DeliveryTask; event history is authoritative for workflow recovery.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
client -> order saga -> restaurant -> prep estimate -> dispatch -> courier tracking -> delivery/payment
```

Partition orders by ID and dispatch by zone, cache versioned menus, combine prep and travel ETA, and use durable timers for each stage.

## Failure, security, and observability

Idempotent commands, compensations/refunds, courier reassignment, restaurant/courier offline handling, and reconciliation recover partial workflows.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Track acceptance, prep error, assignment time, ETA error, stage age, cancellations, payment unknowns, and location freshness.
