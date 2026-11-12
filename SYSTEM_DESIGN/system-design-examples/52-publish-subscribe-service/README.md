# Publish-Subscribe Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Match published events to independent subscriptions with filtering, retention, retry, and dead-letter handling.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Topic/Event(id,key,schema,payload); Subscription(id,filter,delivery,ack_deadline); Cursor and DeliveryAttempt.

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
publisher -> durable topic partitions -> filter/fan-out -> subscription backlog -> pull/push consumer -> retry/DLQ
```

Store payload once, maintain per-subscription cursors or references, shard subscriptions, cap backlog, and isolate slow consumers with quotas.

## Failure, security, and observability

At-least-once delivery plus event IDs, lease-based ACKs, signed push, schema validation, and monitoring of oldest age, retries, DLQ, and storage growth.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

Per-subscription copies simplify independent retention but amplify storage; shared logs are efficient but slow consumers pin shared data.
