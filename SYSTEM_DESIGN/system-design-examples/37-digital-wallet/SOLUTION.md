# Complete Solution: Digital Wallet

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Users open currency-specific wallets, fund through external rails, transfer internally,
pay merchants, withdraw, view booked/pending/available balances and statements, and
receive notifications. The platform enforces identity/KYC, sanctions, AML, fraud,
velocity, balance, and product limits and supports account freeze/review/refund.

Targets: internal transfer p99 below 500 ms, balance read p99 below 150 ms, 99.99%
reads and 99.95% money commands, no duplicate/deleted money effect, and statement lag
below seconds. Internal transfers use a strongly consistent balanced ledger. External
rail operations are sagas: timeout means `UNKNOWN`, with funds held until authenticated
evidence/reconciliation resolves it.

## 2. Capacity estimation

Assume 50 million wallets, 100 million transfer/funding/withdrawal operations/day,
four ledger postings/operation, ten balance reads/operation, and 10x peaks.

- Money commands average 1,160/s and peak near 12,000/s.
- Ledger postings average 4,600/s and peak near 46,000/s.
- Balance/statement reads average 11,600/s and peak near 120,000/s.
- At 5 KB workflow/audit/ledger metadata per operation, hot growth is 500 GB/day
  before indexes/replicas and mandated archives.
- Partition by legal entity/book and wallet ownership while keeping each balanced
  internal transfer in one atomic ledger boundary.

## 3. Financial model and invariants

Wallets are customer-liability ledger accounts: a positive amount owed to a user is
normally a credit balance under accounting convention. Product APIs can expose it as
a positive user balance while ledger postings retain debit/credit semantics.

```text
bookedBalance    = ledger balance of wallet account
activeHolds      = withdrawal/purchase reservations not settled/released
availableBalance = booked spendable amount - activeHolds - compliance locks
```

Invariants:

- every final money movement is one immutable balanced journal per currency;
- available balance cannot go below allowed overdraft (normally zero);
- one business operation/generation maps to at most one ledger transaction;
- holds plus captured amount never exceed the requested operation amount;
- currencies never mix in one balance; FX has explicit quote and balanced currency legs;
- freeze prevents configured outgoing operations but never erases booked funds.

## 4. APIs

```text
POST /v1/wallets                           Idempotency-Key
GET  /v1/wallets/{id}/balance
GET  /v1/wallets/{id}/statement?from=&to=&cursor=
POST /v1/transfers                         {source,destination,amount,currency} Idempotency-Key
GET  /v1/transfers/{id}
POST /v1/funding-intents                   Idempotency-Key
POST /v1/withdrawals                       Idempotency-Key
POST /v1/withdrawals/{id}/cancel           Idempotency-Key
POST /v1/payment-method-tokens
```

Money is integer minor units plus explicit currency. Commands use user-scoped
idempotency and include device/session context, never client-calculated balance.
Bound amount, recipients/day, velocity, beneficiaries, page size, and request cost.

## 5. Data model

```text
Wallet(id, user_id, legal_book_id, currency, state, ledger_account_id,
       product_tier, version, created_at)
Transfer(id, source_wallet_id, destination_wallet_id, amount, currency,
         type, state, risk_decision_id, ledger_tx_id, version, created_at)
ExternalOperation(id, wallet_id, type, amount, fee, currency, state,
                  provider, external_request_id, external_ref, hold_id,
                  ledger_tx_id, attempt, version)
Beneficiary(id, user_id, tokenized_destination, type, state, verified_at)
LimitUsage(subject_id, limit_type, window, amount, count, version)
RiskDecision(id, operation_id, model_rule_versions, action, reasons)
Inbox(provider, event_id, payload_hash, processed_at)
Outbox(id, aggregate_id, sequence, event_type, payload, published_at)
ReconciliationCase(id, external_ref, internal_ref, type, amount, state, evidence)
```

Ledger owns accounts, holds, immutable transactions/postings, and authoritative
control balance. Wallet service owns user-facing workflow. Statements are read
projections joined to safe business descriptions, not a second money source.

## 6. Architecture

```text
client -> API/auth/device -> wallet command service -> transfer/external state DB
             |                       |                    |
        identity/KYC            risk/limits           durable workflow/outbox
                                     |                    |
                                     +-> double-entry ledger
                                     +-> payment/bank/rail adapters -> providers

provider callbacks -> signature/raw inbox -> state machine
ledger/outbox -> balance/statement projections -> notifications
provider/bank/ledger reports -> reconciliation/control totals
```

The ledger and wallet may share a transactional cell for internal transfers, or the
ledger exposes an idempotent atomic `post` API. A wallet operation is not successful
until its ledger transaction is committed and linked.

## 7. Step-by-step workflow

### Internal transfer

1. Authenticate sender and device, validate wallet/currency/recipient/amount and
   idempotency, then evaluate KYC status, sanctions, risk, velocity, daily/monthly limits,
   and step-up authentication.
2. Create transfer `PENDING` or execute within the ledger command. Lock source/
   destination controls in deterministic order, recheck available balance, and append
   balanced debit/credit journal under unique transfer reference.
3. Atomically mark transfer `COMPLETED` with ledger ID (same DB) or conditionally link
   the idempotent ledger response. Return committed status.
4. Events update statements/limits/notifications; duplicates use source version.

### External withdrawal

1. Validate/verify beneficiary, risk and limits; create operation and active ledger
   hold atomically/idempotently.
2. Persist stable provider request/reference, then send through adapter.
3. Definitive provider acceptance/success progresses state. Timeout becomes `UNKNOWN`;
   keep hold and query/reconcile rather than resend/reroute blindly.
4. Proven settlement captures hold into a balanced withdrawal/fee journal. Definitive
   rejection/cancel releases it. Bank/provider files reconcile final movement.

## 8. Core internal transfer logic

```text
function transfer(actor, command, key):
    require command.amount > 0 and validCurrencyScale(command)
    requestHash = canonicalHash(command)

    risk = riskAndCompliance.evaluate(actor, command)
    require risk.action == ALLOW or completeStepUp(risk)

    transaction SERIALIZABLE in ledger cell:
        prior = idempotency.get(actor.id, "transfer", key)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response

        source = wallets.getForUpdate(command.sourceWallet)
        destination = wallets.getForUpdate(command.destinationWallet)
        require source.userId == actor.id
        require both ACTIVE and same currency == command.currency
        require transferPolicyAllows(source, destination, actor, risk)
        reserveLimitUsageConditionally(actor, command.amount)

        accounts = ledger.lockAccountsSorted(source.accountId, destination.accountId)
        require ledger.available(source.accountId) >= command.amount
        transfer = transfers.insert(command, risk.id, state=PENDING)
        journal = ledger.postWithinTransaction(
          externalReference="wallet-transfer:" + transfer.id,
          entries=[debitCustomerLiability(source.accountId, command.amount),
                   creditCustomerLiability(destination.accountId, command.amount)])
        transfer.state = COMPLETED
        transfer.ledgerTxId = journal.id; transfer.version += 1
        append transfer event/outbox and idempotency response
    return transfer
```

Debit/credit helper signs depend on the chart of accounts, but entries sum to zero.
Lock accounts by ID, not source/destination order, to prevent transfer deadlocks. Limit
usage and money commit together or have a conservative reservation/repair protocol.

## 9. Cross-cell internal transfer

Prefer assigning wallets in the same legal book to a ledger cell capable of atomic
multi-account journals. If source/destination live in separate books/cells, do not
write one unbalanced half in each. Use independently balanced clearing journals:

1. atomically debit source customer and credit source inter-book payable/clearing;
2. durable workflow sends stable transfer reference to destination book;
3. destination atomically debits inter-book receivable/clearing and credits customer;
4. reconcile clearing accounts and compensate/refund source if destination cannot
   accept under the transfer contract.

This saga exposes `PROCESSING`; it is not instant atomic balance movement. Centralizing
the regulated wallet ledger is often simpler until scale/legal boundaries require it.

## 10. External operation and ambiguity logic

```text
function startWithdrawal(actor, command, key):
    transaction locking wallet/account:
        return prior if idempotency key exists
        validate beneficiary, risk, limits, wallet state
        hold = ledger.createHold(wallet.accountId,
                                 command.amount + maxFee, expiry, stableHoldKey)
        operation = externalOps.insert(WITHDRAWAL, hold.id, state=CREATED,
                                       externalRequestId=stableId(newOperationId))
        append outbox/idempotency
    workflow.enqueue(operation.id)

function sendWithdrawal(operation):
    mark SENT durably before network call
    result = adapter.send(operation, idempotency=operation.externalRequestId)
    if result.definitive: applyVerifiedResult(result)
    else:
        transition SENT -> UNKNOWN
        schedule status query/reconciliation

function settleWithdrawal(operation, evidence):
    transaction/state command:
        require verifiedEvidenceMatches(operation, evidence)
        ledger.captureHoldIdempotently(operation.holdId,
           balancedWithdrawalAndFeeJournal(operation), settlementKey)
        mark operation SUCCEEDED and link ledger transaction
```

Unknown funds remain unavailable until resolved or a tightly controlled maximum-risk
policy. Releasing merely because a timeout elapsed can let both user and provider
spend the same money.

## 11. Funding flow

Funding creates a processor/bank intent tied to wallet, exact amount/currency, and
stable reference. Never credit spendable wallet balance from an unverified browser
redirect or unauthenticated callback. Depending rail risk, credit only after final
settlement, or credit provisionally to a restricted pending account and later move
to customer liability. Chargeback/return reverses through explicit balanced journals
and may create a debt/locked wallet; never edit the top-up posting.

Provider fee and platform revenue/expense are separate accounts. Reconcile processor
payment, ledger receivable, settlement, fees, cash bank statement, and wallet credit.

## 12. Limits, risk, and compliance

Limits include per-transaction, rolling day/month amount/count, balance, recipients,
cash-in/out, and product/KYC tier. Use event-time windows with strongly consistent
reserved usage for hard limits; streaming aggregates alone may lag and allow bypass.
On terminal failure, release reserved limit usage idempotently if regulation/product
definition permits.

Risk combines account/device/network/beneficiary/velocity/history signals. Actions are
allow, step-up, delay/review, or deny. AML monitoring builds cases across transactions;
sanctions screening covers users/beneficiaries and refreshes. Compliance holds freeze
configured outgoing paths while preserving ledger/audit access and controlled inbound
handling.

## 13. Balance and statement reads

Strong balance reads use ledger control state and active holds. Regional/cache reads
return `(booked,pending,available,as_of_sequence)` and must be labeled if stale. Never
authorize spend from an eventual projection.

Statement projection consumes ordered transfer/ledger events, maps entries to user-safe
descriptions and counterparty masking, and applies each ledger/account sequence once.
Cursor uses `(effective_at, ledger_transaction_id, posting_id)`. If a gap appears,
fetch missing ledger entries before advancing. Users can retrieve older tiered history
under bounded range/export workflow.

## 14. Multi-currency and FX

Create one wallet/account per currency. A user cannot transfer USD directly into EUR
without an explicit FX quote containing source/target integer amounts, rate ID, fees,
expiry, and rounding policy. Execution posts separately balanced legs per currency
against FX position/clearing accounts. Quote expiry or insufficient source balance
fails without partial customer credit. Reconcile provider hedge/settlement and manage
currency exposure separately.

## 15. Notifications and receipts

Notifications consume committed outbox events and may be delayed/duplicated; they do
not determine money state. Use stable notification IDs, hide full recipient/account
data, and tell clients to fetch current transfer. Receipts reference immutable transfer/
ledger IDs, amount/currency/time/status, but protect PII and do not expose internal
account/chart details.

## 16. Reconciliation

Perform independent control chains:

```text
wallet operation <-> ledger transaction/hold <-> provider operation
<-> settlement report/fee <-> bank movement
```

Also recompute wallet balances from postings, compare hold control totals to active
hold rows, limit reservations to operations, statements to ledger sequences, and
customer-liability totals to safeguarding/settlement accounts according to finance
policy. Classify mismatches, attach immutable evidence, apply safe idempotent repair,
and require dual approval for manual money journals.

## 17. Partitioning and resilience

Partition operational workflows by wallet/transfer ID and ledger by legal book/cell.
Maintain user-to-wallet directory and read projections separately. One fenced leader
owns a book/account control state; do not accept outgoing money writes when quorum/
fresh ownership is uncertain. Adapters, callback ingress, reconciliation, risk, and
notifications have isolated pools and queues. Degrade statements/notifications before
money correctness or hard compliance controls.

## 18. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client repeats transfer | Same key/hash returns same transfer and ledger effect |
| Concurrent debits | Locked/serializable available balance lets only valid set commit |
| Process dies after ledger commit | Idempotent reference returns journal; workflow links/reconciles |
| Provider withdrawal times out | Keep hold, mark UNKNOWN, query same reference |
| Provider callback duplicates | Verified inbox event ID/hash applies once |
| Risk soft model fails | Documented conservative fallback/step-up; hard controls fail closed |
| Statement projection gaps | Stop at sequence gap and repair from ledger |
| Notification fails | Money state unaffected; retry delivery |
| Region partitions | Fence writer and reject unsafe money commands |

## 19. Security and privacy

Require strong authentication, device binding, risk-based step-up, beneficiary cooling
periods, transaction signing for high risk, session/credential rotation, and customer
alerts. Tokenize bank/card credentials in compliant vaults; never log secrets. Use
mTLS/service roles, HSM/KMS encryption, signed callbacks, replay windows, rate limits,
tamper-evident audit, dual control, and protected support tools.

Prevent account takeover, SIM swap/social engineering, credential stuffing, bot cash-
out, mule rings, beneficiary tampering, IDOR, amount/currency overflow, refund/top-up
fraud, and insider abuse. Apply KYC/AML/sanctions, safeguarding, financial retention,
privacy minimization/deletion where permitted, residency, legal hold, suspicious-
activity reporting, incident response, and tested key/backup recovery.

## 20. Observability

Track command/balance/statement latency/errors, operations/value by type/state/currency,
authorization/step-up/denial, concurrent-debit conflicts, insufficient funds, limit
utilization/reservations, active hold age, UNKNOWN operations/time-to-resolution,
provider success/latency/callback validity, ledger posting/link lag, projection gaps,
notifications, account freezes, fraud/AML case flow, reconciliation mismatch count/
value/age, liability/control totals, and fenced-leader events.

Model/property tests generate concurrent transfers, duplicate/reordered callbacks,
hold capture/release races, FX rounding, and failures around every commit and assert
balance/no-duplicate invariants. Adapter contracts use provider sandboxes. Load-test
hot wallets and coordinated cash-out. Chaos tests kill workers/providers/leaders;
daily independent control totals compare operations, ledger, provider, and bank evidence.

## 21. Implementation path

1. **MVP:** one currency/internal transfers, compliant identity, atomic ledger,
   idempotency, strong available balance, statements, and manual operations.
2. **External rails:** holds, funding/withdrawal state machines, token vault/adapters,
   verified callbacks, UNKNOWN reconciliation, limits/risk, and notifications.
3. **Product scale:** book/cell partitioning, beneficiaries, merchant payments, returns/
   chargebacks, multi-currency FX, automated reconciliation, and compliance cases.
4. **Hardening:** fenced regional recovery, security/AML/privacy controls, property/
   model/load/chaos tests, control totals, restore/key drills, runbooks, and SLOs.

## 22. Final design

Make the double-entry ledger the only financial truth and the wallet service an
idempotent workflow/policy layer. Internal transfers lock and validate available
balance and post source/destination entries atomically. External operations first
reserve funds, persist a stable provider reference, and only capture/release from
authenticated evidence; ambiguous outcomes remain held and reconciled. Strong limit/
compliance controls, sequence-based statements, explicit FX legs, and end-to-end
control totals keep user money correct across retries, fraud, outages, and years of audit.
