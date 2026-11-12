# Double-Entry Ledger

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Record immutable balanced postings, derive balances, support reversals, and provide complete auditability.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Transaction(id,reference,effective_at); Posting(transaction,account,amount,currency); Account(id,currency); sum of postings per currency must be zero.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
business command -> ledger transaction -> append postings/outbox -> balance projections/reports
```

Commit all postings atomically, partition accounts carefully, lock in deterministic order, maintain derived balances with sequence checkpoints, and archive cold history.

## Failure, security, and observability

Unique references deduplicate effects; corrections use reversing entries. Strict authorization, tamper-evident audit, and reconciliation are mandatory.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Synchronous balances are current but constrain partitioning; asynchronous projections scale reads while requiring lag-aware consumers.
