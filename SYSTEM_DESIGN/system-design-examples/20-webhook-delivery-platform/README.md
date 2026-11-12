# Webhook Delivery Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Deliver signed tenant events to external endpoints with filters, retries, quotas, and an audit trail.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

Publish internal event IDs; subscribers manage URLs/secrets/filters; delivery records expose attempts and replay controls.

Subscription(id, tenant, endpoint, secret_version, filter, status); Event(id, type, payload_ref); Delivery(event, subscription, attempt, next_at, status).

## High-level design

```text
producer -> event log -> subscription matcher -> tenant queues -> delivery workers -> endpoint -> result store
```

Partition by subscription, cap per-destination concurrency, use exponential backoff with jitter, store payloads once, and apply retention limits.

## Reliability, security, and operations

Sign timestamped payloads, prevent SSRF with egress controls, deduplicate event IDs, dead-letter permanent failures, and disable persistently failing endpoints.

Measure success latency, queue age, endpoint status/latency, retry volume, disabled subscriptions, and per-tenant backlog.

## Key trade-off

Ordered delivery simplifies consumers but lets one failed event block a subscription; parallel delivery improves throughput and requires consumer idempotency.
