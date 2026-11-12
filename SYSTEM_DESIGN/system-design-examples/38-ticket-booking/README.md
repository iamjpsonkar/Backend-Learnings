# Ticket Booking

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Search events, select seats, create expiring holds, pay, and issue verifiable tickets.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Seat(event,seat,state,version); Hold(id,user,expires_at,state); Booking(id,hold,payment,state); ticket tokens reference bookings.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
client -> availability read model -> seat partition -> hold store/expiry -> payment -> booking/ticket
```

Serialize commands per event/section, atomically hold seats, use countdown TTLs, queue extreme onsales, and keep search/availability views explicitly stale.

## Failure, security, and observability

Idempotent hold/booking transitions, payment reconciliation, signed tickets, bot controls, and audit prevent duplicates and fraud.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Pessimistic holds prevent double sale but reduce utilization when users abandon; shorter TTLs improve turnover but hurt checkout completion.
