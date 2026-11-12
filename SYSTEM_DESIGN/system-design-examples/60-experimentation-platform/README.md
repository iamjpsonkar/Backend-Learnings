# Experimentation Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Assign users consistently, record exposure, compute guarded metrics, and detect invalid experiments.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Experiment(id,variants,allocation,eligibility,version); Assignment(subject,experiment,variant); Exposure; Outcome events and metric definitions.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
config -> assignment SDK/service -> exposure log; events -> validation/join/aggregation -> statistical results/guardrails
```

Hash stable subject IDs into allocation ranges, freeze version semantics, deduplicate exposures, partition event processing, and recompute from immutable raw data.

## Failure, security, and observability

Audit changes, minimize identity data, detect sample-ratio mismatch and missing joins, and monitor exposure lag, allocation balance, metric freshness, and guardrail breaches.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Client assignment is low latency but easier to tamper with; server assignment centralizes control but can become a critical dependency.
