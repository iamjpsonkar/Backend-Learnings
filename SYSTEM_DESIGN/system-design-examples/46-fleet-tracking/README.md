# Fleet Tracking

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Ingest vehicle telemetry, show current state, retain trips, detect geofences, and alert operators.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Telemetry(vehicle,device_seq,event_time,location,speed); LatestVehicle; Trip segments in time-series/object storage; Geofence definitions versioned.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
devices -> authenticated ingest -> partitioned log -> latest/trip/geofence processors -> dashboard/alerts
```

Partition by vehicle, batch/compress uploads, separate latest-state from history, downsample old data, and process by event time with watermarks.

## Failure, security, and observability

Deduplicate device sequence, quarantine impossible jumps, buffer offline devices, encrypt identifiers, and monitor ingest lag, out-of-order rate, device silence, and geofence delay.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Long reorder windows improve historical correctness but delay alerts; short windows favor operations with later correction.
