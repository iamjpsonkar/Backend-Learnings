# Package Tracking

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Ingest carrier scans, normalize shipment state, build a customer timeline, estimate delivery, and notify changes.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Shipment(id,carrier,tracking,version); RawEvent(source,id,time,payload); NormalizedEvent(shipment,type,event_time,location); Projection.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
carrier polls/webhooks -> dedupe log -> normalization/order -> shipment state -> ETA/notifications/API
```

Partition by shipment, retain raw events for replay, use carrier-specific adapters, order by event time with rules, and rebuild projections deterministically.

## Failure, security, and observability

Idempotent source IDs, signature verification, poison-event quarantine, stale-carrier indicators, and monitor ingest lag, normalization failures, state regressions, and ETA error.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

A universal state model simplifies clients but can erase carrier nuance; retaining raw events preserves audit and future remapping.
