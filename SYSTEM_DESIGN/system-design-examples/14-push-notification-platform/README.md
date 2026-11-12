# Push Notification Platform

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Accept notification intents, honor preferences, select mobile/web providers, retry transient failures, and record outcomes.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

POST /notifications accepts recipients, template, variables, priority, and idempotency key; status APIs expose aggregate outcomes.

Notification(id, tenant, template, state); Delivery(notification, recipient, device_token, provider, attempt, status); Preference(user, channel, topic).

## High-level design

```text
producer -> API -> durable queue -> preference/template -> provider workers -> APNs/FCM/Web Push -> callbacks
```

Partition by recipient or tenant, batch provider calls, enforce tenant quotas, cache preferences, and separate transactional from bulk priority queues.

## Reliability, security, and operations

Deduplicate intents, rotate invalid tokens, retry only transient errors, dead-letter poison messages, encrypt tokens, and redact payloads from logs.

Track enqueue-to-provider latency, provider errors, invalid tokens, retries, queue age, delivery callbacks, and tenant throttles.

## Key trade-off

Provider acceptance is not device receipt; honest status semantics are preferable to claiming end-to-end delivery.
