# Digital Wallet

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Fund wallets, transfer balances, enforce limits/risk, withdraw, and expose statements backed by a ledger.

Define peak traffic, latency/availability targets, retention, and consistency before sizing the design.

## Data and interfaces

Wallet(id,user,currency,status); Transfer(id,source,destination,amount,state); ledger transaction/postings remain financial truth.

Expose idempotent commands for writes, cursor-based reads, and versioned events for asynchronous consumers.

## Architecture

```text
client -> wallet API -> auth/risk/limits -> transfer state machine -> ledger -> notifications/reconciliation
```

Partition commands by wallet, serialize conflicting debits, reserve funds for external withdrawals, and use sagas around providers while keeping ledger postings atomic.

## Failure, security, and observability

Idempotency keys, immutable audit, KYC/AML controls, encryption, step-up auth, and provider reconciliation handle retries and ambiguous outcomes.

Apply least privilege, encryption, quotas, audit logging, dashboards, and alerts appropriate to the data and abuse risk.

## Key trade-off

Available-balance reservations improve safety for slow providers but complicate balance semantics and expiration.
