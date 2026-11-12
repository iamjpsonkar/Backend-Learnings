# Email Delivery Service

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Send transactional and bulk email with templates, domain reputation, suppression, bounces, and provider feedback.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

POST /email accepts template/version, recipients, variables, class, schedule, and idempotency key; event webhooks report outcomes.

Message(id, tenant, class, template_version, state); Recipient(message, address_hash, status); Suppression(address_hash, reason, expires_at).

## High-level design

```text
producer -> admission/quota -> durable queues -> renderer -> MTA/provider pools -> feedback processor
```

Separate traffic classes and tenant pools, batch safely, warm sending domains/IPs, and store immutable rendered artifacts for audit when policy permits.

## Reliability, security, and operations

Honor suppression before enqueue and send, authenticate domains, sign mail, retry temporary SMTP failures, and quarantine abusive tenants.

Measure queue age, accepted/delivered/bounced/complaint rates, provider latency, reputation signals, and suppression hits.

## Key trade-off

Dedicated sending pools isolate reputation but cost more; shared pools improve utilization while coupling tenants' behavior.
