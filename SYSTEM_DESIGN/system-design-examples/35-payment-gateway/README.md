# Payment Gateway

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Tokenize methods, authorize, capture, refund, route processors, and resolve asynchronous callbacks safely.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

PaymentIntent(id,merchant,amount,currency,state,idempotency_key); Attempt(intent,provider,external_id,state); ledger references finalized effects.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
merchant -> gateway -> risk/vault -> processor adapter -> provider; callbacks -> verifier -> state machine/outbox
```

Partition by merchant/intent, isolate processor adapters, use timeouts/circuit breakers, route by capability/health, and never infer failure from a timeout.

## Failure, security, and observability

Use idempotency and provider reconciliation for ambiguous results, encrypt/tokenize data, minimize PCI scope, and monitor auth rate, latency, unknown states, and duplicates.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Multi-provider routing raises availability and negotiation power but complicates reconciliation, behavior parity, and compliance.
