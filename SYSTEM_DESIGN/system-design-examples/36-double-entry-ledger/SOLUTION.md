# Complete Solution: Double-Entry Ledger

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Record immutable balanced financial transactions, expose current/as-of balances and
statements, support holds/reservations, reversals/corrections, period close, audit,
and reconciliation with upstream processors/banks. Multiple tenants/books, account
types, and currencies are supported without silently converting money.

Targets: posting p99 below 300 ms, balance read p99 below 100 ms, 99.99% reads and
99.95% posting availability, no acknowledged transaction lost or duplicated, and
every committed journal balanced in each currency. Prefer rejection during uncertain
partitions over split-brain money writes.

## 2. Accounting convention and invariants

Represent each posting as signed integer minor units: debit positive and credit
negative (the reverse convention is also valid if used everywhere). For every journal:

```text
for each currency C: sum(posting.signed_amount where currency == C) == 0
```

Additional invariants:

- every account has exactly one currency and book/tenant;
- every posting references an open/allowed account and immutable transaction;
- a business effect key creates at most one journal transaction;
- entries, effective time, and reference never update after posting;
- corrections append a full/partial reversing transaction linked to the original;
- synchronous control balances and immutable postings commit atomically;
- money is integer/fixed precision with explicit currency scale, never float.

Debits/credits do not inherently mean plus/minus to the customer. Account type defines
normal balance. For example, an asset debit raises the asset; a liability credit
raises the amount owed to a customer.

## 3. Capacity estimation

Assume one billion postings/day, four postings/transaction average, 500 bytes/posting
including indexes/audit, five balance reads/transaction, and 10x peak.

- Postings average about 11,600/s and peak near 120,000/s.
- Transactions average about 2,900/s and peak near 30,000/s.
- Balance reads average about 14,500/s and peak near 150,000/s.
- Raw posting growth is roughly 500 GB/day before replication and archives—about
  1.3 PB over seven years before compression/tiering.
- Partition by legal book/journal ownership and time for storage, while preserving
  one atomic boundary for all entries in a transaction.

## 4. APIs

```text
POST /v1/ledger-transactions             Idempotency-Key / externalReference
GET  /v1/ledger-transactions/{id}
POST /v1/ledger-transactions/{id}/reversals Idempotency-Key
GET  /v1/accounts/{id}/balance?asOf=&consistency=
GET  /v1/accounts/{id}/postings?from=&to=&cursor=
POST /v1/holds                           Idempotency-Key
POST /v1/holds/{id}/capture              Idempotency-Key
POST /v1/holds/{id}/release              Idempotency-Key
POST /v1/books/{id}/close-period         Idempotency-Key
```

Only trusted internal financial services post. Validate maximum entries, allowed
account pairs/journal types, money ranges, currency scales, effective periods, and
caller permissions. Cursor binds account, interval, filters, and last `(sequence,id)`.

## 5. Data model

```text
Book(id, tenant_id, base_reporting_currency, state, current_period, version)
Account(id, book_id, currency, type, purpose, state, allow_negative,
        control_balance, control_version, created_at)
LedgerTransaction(id, book_id, journal_type, external_reference,
                  effective_at, recorded_at, status, sequence, reversal_of,
                  metadata_hash, created_by)
Posting(id, transaction_id, line_number, account_id, currency,
        signed_amount_minor, description, account_sequence)
Hold(id, account_id, amount_minor, currency, state, expires_at,
     captured_amount, version, external_reference)
Idempotency(book_id, caller_id, endpoint, key, request_hash,
            resource_id, response_ref, expires_at)
Period(book_id, period_id, start_at, end_at, state, closing_sequence)
Outbox(id, book_id, transaction_sequence, event_type, payload, published_at)
BalanceCheckpoint(account_id, account_sequence, posted_balance,
                  held_amount, calculated_at)
```

Unique `(book_id, external_reference)` and idempotency constraints prevent duplicated
effects. Posting unique `(transaction_id,line_number)` preserves deterministic order.
Metadata is allowlisted; unbounded mutable business data does not belong in ledger.

## 6. Architecture

```text
business service -> auth/schema/idempotency -> ledger command service
                                                |
                                      serializable ledger database
                                      /      |       |          \
                               transactions postings accounts   outbox
                                                                     |
                                           ordered event log -> balance/read projections
                                                               -> statements/reports

holds/timers -> same account control store
upstream + bank/provider files -> independent reconciliation/control totals
cold immutable archive <- sealed posting partitions/checkpoints
```

The command database, not the event bus, is the financial source of truth. A
transactional outbox publishes committed sequence events. Derived balances/reports
are rebuildable, but spend authorization uses synchronous control state when required.

## 7. Step-by-step workflow

1. Caller submits journal type, stable external reference/idempotency key, effective
   time, and complete entries.
2. Gateway authenticates service/book scope and canonicalizes request; rule engine
   validates accounts, currency scale, allowed pairings, amount limits, period state,
   and per-currency zero sum.
3. Transaction locks affected account control rows in sorted account-ID order, rechecks
   constraints/available balances, inserts transaction/postings, updates synchronous
   control balances/sequences, and appends outbox atomically.
4. Return committed transaction ID/sequence. Duplicate key/reference returns the same
   result after matching request hash.
5. Outbox consumers update read balances/statements/reporting by monotonically applying
   sequences. Periodic calculation from immutable postings verifies them.
6. External reconciliation matches source business effect, ledger journal, provider/
   bank movement, and settlement; discrepancies create reviewed corrective workflows.

## 8. Core posting algorithm

```text
function postJournal(caller, command, key):
    request = canonicalize(command)
    require entries.size between 2 and MAX_ENTRIES
    require every amount is nonzero integer minor units
    require groupByCurrency(entries).every(sum(signedAmount) == 0)
    requestHash = hash(request)

    transaction SERIALIZABLE on book shard:
        prior = idempotency.get(command.bookId, caller.id, "post", key)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response
        byReference = transactions.getByExternalReference(command.bookId,
                                                           command.externalReference)
        if byReference exists:
            require byReference.requestHash == requestHash
            return publicView(byReference)

        book = books.getForShare(command.bookId)
        require book.state == OPEN
        accounts = lockAccountsSorted(uniqueAccountIds(entries))
        validateAccountsRulesPeriodAndLimits(caller, book, accounts, entries)
        require controlBalancesAllow(accounts, entries)

        sequence = books.nextTransactionSequence(command.bookId)
        tx = transactions.insert(command, sequence, requestHash, POSTED)
        for (lineNo, entry) in enumerate(entries):
            accountSequence = accounts[entry.accountId].controlVersion + 1
            postings.insert(tx.id, lineNo, entry, accountSequence)
            accounts[entry.accountId].controlBalance += entry.signedAmount
            accounts[entry.accountId].controlVersion = accountSequence
        assertControlRules(accounts)
        outbox.insert(LedgerTransactionPosted(tx.id, sequence))
        response = publicView(tx)
        idempotency.insert(command.bookId, caller.id, key, requestHash, response)
    return response
```

Database constraints/triggers should independently enforce immutable rows, valid
currencies/accounts, and zero-sum journal totals where practical. Application checks
alone are insufficient defense in depth.

## 9. Example journal

A wallet top-up of INR 1,000 with a INR 20 processor fee could create:

```text
Debit  Processor receivable (asset)       +102000 paise
Credit Customer wallet liability          -100000 paise
Credit Processor fee payable/liability      -2000 paise
---------------------------------------------------------
Sum                                                0
```

When cash settles, debit bank cash and credit processor receivable. If the processor
withholds its fee, use the precise contract/accounting journal. Do not infer accounting
policy from this illustrative entry; finance defines the chart and journal templates.

## 10. Journal templates and authorization

Versioned templates define required roles, account-purpose pairs, currencies, entry
count, amount relationships, metadata, and negative-balance policy for each business
event. For example, a wallet transfer may debit one customer-liability subaccount and
credit another within the same book/currency plus fee entries.

```text
template.validate(entries):
    require exactly one SOURCE_CUSTOMER and one DESTINATION_CUSTOMER
    require source.currency == destination.currency
    require source.amount == -destination.amount minus explicit fee relationship
    require caller owns authorized product/tenant scope
```

Templates reduce arbitrary-account posting risk, but the ledger still checks global
balance/invariants. High-value/manual journals require dual approval and separation
of duties.

## 11. Holds versus posted money

A card/wallet authorization hold is not final accounting and should not be faked by
editing a ledger balance. Maintain a strongly consistent hold subledger:

```text
availableBalance = postedSpendableBalance - sum(activeHolds)

function createHold(account, amount, expiry, key):
    transaction locking account:
        return prior if key exists
        expire/reconcile known due holds as policy permits
        require availableBalance(account) >= amount
        insert ACTIVE hold; increment held control amount/version

function captureHold(hold, amount, key):
    transaction locking hold/account:
        require ACTIVE and remaining >= amount
        post or atomically stage linked balanced journal for captured amount
        decrement held amount; increment captured; close if fully captured
```

Release/expiry changes hold state/held control exactly once. The final capture is a
normal immutable balanced journal, linked to the hold. Queue/timer delivery can repeat;
state/version prevents double release.

## 12. Reversals and corrections

Never update/delete a posted transaction. A full reversal copies each original entry
with negated signed amount, current recorded time, explicit effective-time policy, and
`reversal_of`. Unique reversal reference prevents duplicates. Partial correction posts
the necessary balanced adjustment and references original/reason/approval.

```text
function reverse(originalId, reason, key):
    original = requirePosted(originalId)
    require reversalPolicyAllows(original, caller, currentPeriod)
    entries = original.postings.map(p => Entry(p.accountId, -p.amount, p.currency))
    return postJournal(caller,
        Journal(type=REVERSAL, reversalOf=original.id,
                externalReference=stableReversalReference(key), entries=entries), key)
```

If a period is closed, book correction in the current permitted period with finance-
defined prior-period adjustment treatment; do not reopen silently.

## 13. Balance reads and rebuild

Synchronous `control_balance` is updated with postings for limits and current balance.
Read projections can offer richer booked/pending/available/as-of views:

```text
balanceAt(account, targetSequence) = checkpoint.balance
    + sum(postings after checkpoint.sequence through targetSequence)
```

Projection consumer conditionally applies `(account_id, account_sequence)` and rejects
gaps/duplicates, fetching missing postings before advance. Daily checkpoints are
checksummed against posting sums. An as-of request uses effective-time/reporting rules
and bitemporal distinction: effective time states when business event applies;
recorded time states when ledger learned it.

## 14. Currency and foreign exchange

Never sum different currencies. Each currency group within a journal balances to zero.
An FX trade is represented using per-currency clearing/position accounts and an
explicit rate/quote, for example balanced USD entries and separately balanced EUR
entries. Rounding differences go to a designated rounding account under policy. Store
source/target integer amounts, currency scales, quote/rate ID and timestamp—not only
a floating rate.

## 15. Partitioning strategy

All entries in a journal must share one atomic database boundary. Practical choices:

- shard by tenant/legal book and keep transfers within a book;
- assign books to cells with serializable databases and migrate whole books;
- for a cross-book movement, post two independently balanced journals through a
  clearing workflow and reconcile clearing accounts, rather than an unbalanced cross-
  shard transaction;
- keep high-contention omnibus accounts partitioned by purpose/time/tenant only if
  accounting policy allows multiple subaccounts whose aggregate is reported later.

Lock accounts deterministically to prevent deadlocks. Consensus/fencing ensures one
writer leader per book shard. Availability is intentionally sacrificed when atomicity
cannot be guaranteed.

## 16. Period close and archive

Close workflow stops or fences backdated writes, waits for projections/imports,
reconciles subledgers/control accounts, computes trial balance, stores signed report
and closing sequence/checksums, then changes period to CLOSED under dual approval.
Late items post to an allowed adjustment period.

Move old immutable partitions to write-once/tiered archive only after checksums,
index/catalog, restore test, and legal retention policy. Online account statements
span hot projections plus archive transparently with bounded cursors. Encryption-key
retention must match required financial retention.

## 17. Reconciliation and control totals

Run independent checks:

- every journal balances per currency and postings count matches header;
- control/read balances equal recomputation from postings/checkpoints;
- every source business effect maps to exactly one ledger reference and vice versa;
- provider settlement/bank statement matches receivable/cash/fee journals;
- clearing and suspense accounts age toward zero under their contracts;
- outbox sequence has no gaps and every committed journal reaches required consumers.

Discrepancies create cases with amount/currency/evidence/owner/SLA. Repairs append
approved transactions; they never rewrite history.

## 18. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Caller retries after timeout | Same key/reference and request hash return same journal |
| Process dies during posting | Database atomically commits all entries/control/outbox or none |
| Outbox publishes twice | Consumer sequence/idempotency applies projection once |
| Projection misses event | Detect account-sequence gap and fetch/replay postings |
| Hold expiry races capture | Locked state/version allows one transition/delta |
| Reversal repeats | Unique reversal business reference returns original reversal |
| Book leader partitions | Fencing rejects old leader; no split-brain money writes |
| Archive unavailable | Recent balances work; historical request fails explicitly, not partially |
| Corruption/checksum mismatch | Quarantine shard/partition and restore/replay verified data |

## 19. Security, audit, and tamper evidence

Use service identities, journal-template permissions, book/account scope, dual control,
field encryption, HSM/KMS keys, immutable admin/audit logs, and strict production data
access. Prevent arbitrary accounts/amounts, overflow, currency-scale errors, backdating,
reference reuse, IDOR, SQL/report injection, and insider manipulation. Never store raw
payment credentials.

Hash-chain transaction batches and sign sealed period roots into external write-once
storage for tamper evidence, but do not treat hashes as a substitute for access control,
replication, reconciliation, or backups. Apply financial retention, privacy
minimization/erasure where legally permitted, residency, legal hold, incident response,
and regular restore/key-recovery drills.

## 20. Observability

Track posting/read latency/errors, transaction/posting volume/value by currency/book,
idempotency replay/hash mismatch, serializable retries/deadlocks, hot accounts/books,
rejected template/insufficient balance/closed-period commands, per-currency imbalance
(must remain zero), control/projection lag and gaps, hold age/expiry/capture races,
reversal/adjustment volume, reconciliation/control-total mismatches and value, clearing/
suspense age, outbox gaps, archive restore checks, and leader/fencing events.

Property/model tests generate randomized balanced journals, duplicate/reordered events,
concurrent holds/captures/releases, reversals, and close races and prove invariants.
Load-test hot omnibus accounts and multi-entry journals. Chaos tests kill writers/
leaders/projectors at every commit boundary. Independently recompute trial balances
from immutable postings on a recurring schedule.

## 21. Implementation path

1. **MVP:** one serializable database, chart/accounts, balanced immutable journals,
   idempotency/reference uniqueness, synchronous balances, reversals, and audit.
2. **Operational reliability:** outbox, statements/projections with sequences,
   holds/expiry, templates/roles, reconciliation/control totals, and checkpoints.
3. **Scale/lifecycle:** book-based cells, read replicas, period close, signed archives,
   cross-book clearing workflow, tiered history, and migration tooling.
4. **Hardening:** dual control/security/compliance, property/model/load/chaos tests,
   independent recomputation, restore/key drills, dashboards, runbooks, and SLOs.

## 22. Final design

Make one immutable journal transaction the atomic unit and require its signed integer
postings to sum to zero separately in every currency. In the same serializable commit,
deduplicate the business reference, lock/update control balances, append postings, and
write the outbox. Holds are a distinct strongly consistent reservation subledger;
captures become normal journals. Corrections reverse rather than edit. Book-aligned
partitioning, sequence-based rebuildable reads, period close, tamper evidence, and
independent reconciliation preserve financial truth over years of retries and failures.
