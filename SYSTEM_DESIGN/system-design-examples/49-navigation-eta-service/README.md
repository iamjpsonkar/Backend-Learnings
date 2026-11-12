# Navigation ETA Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Predict arrival times from route geometry, current traffic, incidents, weather, and historical patterns.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Route edges and features; SpeedObservation(edge,event_time,value); versioned ETA model; Prediction(route,model,generated_at).

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
telemetry/incidents -> stream aggregation/feature store -> model training; route -> online features -> ETA inference
```

Aggregate speeds by road/time bucket, use robust sampling, cache route features, degrade to historical baselines, and batch inference where possible.

## Failure, security, and observability

Reject spoofed/outlier data, version and canary models, preserve feature timestamps, and monitor ETA absolute/percentile error by region/time plus feature freshness.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

More live features react quickly but are noisy and outage-prone; historical priors are stable but slow to reflect incidents.
