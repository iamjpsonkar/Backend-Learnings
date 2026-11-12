# Order Management System

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Coordinate checkout, payment, inventory, fulfillment, cancellation, returns, and customer-visible status.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Order(id,user,state,version,total); OrderLine; immutable OrderEvent; command IDs and external references enforce idempotency.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
checkout -> order transaction/outbox -> saga orchestrator -> payment/inventory/fulfillment -> event log/read models
```

Keep the order state machine authoritative, use transactional outbox, partition by order ID, and execute compensations for failed saga steps.

## Failure, security, and observability

Reject invalid transitions, deduplicate callbacks, reconcile external systems, encrypt PII, audit actions, and monitor stuck states, compensation rate, and age by stage.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Orchestration makes workflow explicit and observable; choreography reduces central coupling but obscures state and failure handling.
