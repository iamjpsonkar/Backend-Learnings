# Alerting System

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Evaluate metric/log rules, create incidents, group/deduplicate, route notifications, silence, and resolve.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Rule(id,query,interval,for,labels); AlertInstance(rule,key,state,since); Incident; Silence; NotificationAttempt.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
scheduler -> rule evaluators -> alert state -> grouping/dedupe -> routing -> notification providers
```

Shard rules, jitter evaluations, persist state, group by stable labels, inhibit dependent alerts, and use separate high-priority notification queues.

## Failure, security, and observability

Require sustained conditions, survive evaluator failover from checkpoints, audit silences, and monitor evaluation delay/errors, firing count, notification latency, and provider failure.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Fast sensitive rules detect early but create noise; duration, grouping, and inhibition reduce storms while delaying notification.
