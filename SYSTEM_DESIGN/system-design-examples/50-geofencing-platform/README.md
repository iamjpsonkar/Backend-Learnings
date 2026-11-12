# Geofencing Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Register circles/polygons, ingest positions, detect enter/exit/dwell transitions, and deliver idempotent actions.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Fence(id,tenant,geometry,rule,version); DeviceState(device,fence,last_relation,since); Transition(id,device,fence,type,time).

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
position stream -> spatial candidate lookup -> exact geometry/state machine -> transition log -> action/webhook
```

Index fences by spatial cells, partition positions by device, use hysteresis and accuracy radius, checkpoint device state, and expire inactive sessions.

## Failure, security, and observability

Deduplicate position sequence, sign callbacks, isolate tenants, replay from checkpoints, and monitor evaluation lag, candidates/point, transition rate, jitter suppression, and action failures.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Tighter boundaries improve spatial precision but cause GPS jitter; hysteresis and dwell delays improve stability at the cost of responsiveness.
