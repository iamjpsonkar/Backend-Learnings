# Warehouse Fulfillment

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Allocate inventory, create pick waves, route work, scan items, pack, label, and hand off shipments.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

FulfillmentOrder, Task(id,type,location,state,assignee,version), Container, ScanEvent, inventory adjustments and shipment references.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
orders -> allocator -> wave planner -> task queues -> worker/device -> pack/ship stations -> carrier
```

Partition by warehouse, prioritize deadlines, batch picks by zone, lease tasks, update inventory on scans, and keep devices usable during short disconnections.

## Failure, security, and observability

Fence reassigned leases, deduplicate scans, reconcile containers/inventory, require worker authorization, and monitor task age, pick rate/errors, blocked stations, and backlog.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Large waves improve travel efficiency but delay urgent orders; dynamic smaller waves respond faster with more coordination.
