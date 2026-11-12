# Complete Solution: Inventory Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and correctness contract

Track physical on-hand, safety stock, active reservations, order allocations, and
available-to-promise by SKU/location. Checkout creates expiring holds; payment/order
commits them; cancellation/expiry releases them; warehouse receipts, shipments,
returns, damage, and counts adjust physical stock with a complete audit trail.

Default policy is no oversell: a successful reservation is strongly consistent for
each SKU/location and the service may reject during an unsafe partition. Backorder/
oversell is a separate explicit product policy, never an accidental fallback.

Targets: reserve/commit p99 below 200 ms normally, 99.99% reads and 99.9% commands,
expiry release within 30 seconds of due time, and zero invariant violations. Cached
availability is indicative; only a successful reservation promises stock.

## 2. Capacity estimation

Assume 100 million SKU-location rows, 50,000 normal reserve operations/s, one million
requests/s for a flash SKU, five locations/SKU, 300-byte stock row, and 15-minute holds.

- Core rows are roughly 30 GB before indexes/replication/audit log.
- At 50,000 reservations/s and 15 minutes, up to 45 million active holds exist if
  every request succeeds.
- Reservation/audit metadata at 500 bytes and 100 million changes/day adds 50 GB/day
  before replication.
- Aggregate capacity is not enough for one flash key: admission, fairness, batching,
  or safely allocated stock buckets are required.

## 3. Inventory accounting model

Use this invariant for each SKU/location:

```text
availableToPromise = max(0,
    onHand - safetyStock - activeReserved - allocatedNotShipped)
```

Reservation moves quantity from available to `activeReserved` without changing
physical `onHand`. Commit moves it from reserved to `allocatedNotShipped`. Shipment
decreases both `allocatedNotShipped` and `onHand`. Release decreases reserved. A
warehouse count sets/reconciles on-hand through an adjustment, never by silently
overwriting history.

If the business uses `sold` as the committed bucket, define whether it means allocated
or shipped and keep the same conservation invariant. Mixing meanings causes drift.

## 4. APIs

```text
POST /v1/reservations                 {lines[], expiresAt} Idempotency-Key
GET  /v1/reservations/{id}
POST /v1/reservations/{id}/commit     {orderId} Idempotency-Key
POST /v1/reservations/{id}/release    {reason} Idempotency-Key
POST /v1/shipments/{shipmentId}       {orderId, lines[]} Idempotency-Key
POST /v1/adjustments                  {sku, location, delta, reason, sourceRef} Idempotency-Key
GET  /v1/availability?sku=&market=&quantity=
GET  /v1/stock/{sku}/locations?cursor=
```

Bound lines/reservation, quantities, hold duration, lookup fan-out, and caller rate.
Only trusted order/warehouse systems may mutate. Every command has caller-scoped
idempotency and immutable source reference.

## 5. Data model

```text
Stock(sku, location_id, on_hand, safety_stock, active_reserved,
      allocated, version, updated_at)
Reservation(id, owner_or_checkout_id, state, expires_at, version,
            order_id, created_at, committed_at, released_at)
ReservationLine(reservation_id, sku, location_id, quantity, line_state)
Adjustment(id, sku, location_id, delta_on_hand, delta_reserved,
           delta_allocated, reason, source_type, source_ref,
           stock_version, created_at)
CommandResult(caller_id, idempotency_key, request_hash, response, expires_at)
ExpiryEntry(bucket, expires_at, reservation_id, reservation_version)
Outbox(id, aggregate_id, event_type, source_version, payload, published_at)
```

Constraints require all counters nonnegative and
`safety_stock + active_reserved + allocated <= on_hand` under no-backorder policy.
Adjustment rows are immutable. Unique `(source_type, source_ref, sku, location)` and
command keys prevent warehouse/order duplicates.

## 6. Architecture

```text
checkout/order -> inventory API -> command router -> strong SKU-location shards
                                            |          |          |
                                      reservation   adjustment   outbox
                                            |                     |
                                      expiry buckets        read projections/events

warehouse/WMS -> adjustment/ship commands               availability cache/read API
                         |
physical snapshots -> reconciliation engine -> reviewed corrective adjustments

flash-sale gateway -> fair admission queue/token buckets -> command router
```

Use a consensus-replicated SQL/KV shard or single-writer log per logical stock key.
Reservation headers may span keys; per-line correctness remains atomic at each key,
with a saga for multi-line all-or-nothing semantics.

## 7. Step-by-step workflow

### Reserve

1. Authenticate checkout, validate quantities/expiry/idempotency, choose fulfillment
   locations using an indicative read model, and order stock keys deterministically.
2. For a single shard, transactionally condition each stock row on sufficient
   available quantity, increment reserved, insert reservation/lines/adjustments,
   expiry entry, and outbox.
3. For multiple shards, coordinator creates a durable intent, reserves lines in
   deterministic order with stable subcommand IDs, and releases acquired lines if
   any line fails. Return success only after all lines are held.
4. Payment/order success commits the reservation. Cancel, failure, or expiry releases it.

### Physical lifecycle

1. WMS receipt/damage/return/count commands carry immutable source IDs.
2. Inventory applies one adjustment conditionally and emits a new stock version.
3. Shipment consumes an order's allocated quantities exactly once.
4. Reconciliation compares inventory accounting with WMS snapshots/events and emits
   alerts or approved compensating adjustments—never rewrites audit history.

## 8. Core atomic reserve logic

```text
function reserveLine(caller, reservationId, line, expiresAt, commandKey):
    require line.quantity > 0 and expiresAt in allowedWindow
    requestHash = hash(reservationId, line, expiresAt)

    transaction on shard(line.sku, line.location):
        prior = commandResults.get(caller.id, commandKey)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response

        stock = stocks.getForUpdate(line.sku, line.location)
        available = stock.onHand - stock.safetyStock
                    - stock.activeReserved - stock.allocated
        if available < line.quantity:
            result = REJECTED_INSUFFICIENT_STOCK
        else:
            stock.activeReserved += line.quantity
            stock.version += 1
            reservationLines.insertUnique(reservationId, line,
                                           state=HELD, stock.version)
            adjustments.insert(deltaReserved=+line.quantity,
                               reason=RESERVE, sourceRef=commandKey)
            expiryIndex.insert(expiresAt, reservationId, line.key)
            outbox.insert(StockChanged(line.key, stock.version))
            result = HELD(stock.version)
        commandResults.insert(caller.id, commandKey, requestHash, result)
    return result
```

The availability check and reserved increment occur under the same serializable/
conditional transaction. A prior cache read cannot authorize reservation.

## 9. Commit, release, and shipment state machine

```text
HELD -> COMMITTED -> SHIPPED
  \-> RELEASED
  \-> EXPIRED
COMMITTED -> CANCELLED_BEFORE_SHIP (moves allocated back or releases by policy)
```

```text
function transitionLine(lineId, target, commandKey):
    transaction on line stock shard:
        return prior result if commandKey exists
        line = reservationLines.getForUpdate(lineId)
        stock = stocks.getForUpdate(line.stockKey)

        if target == COMMITTED and line.state == HELD:
            stock.activeReserved -= line.quantity
            stock.allocated += line.quantity
        else if target in [RELEASED, EXPIRED] and line.state == HELD:
            stock.activeReserved -= line.quantity
        else if target == SHIPPED and line.state == COMMITTED:
            stock.allocated -= line.quantity
            stock.onHand -= line.quantity
        else if line.state == target: return existingSuccess
        else: rejectInvalidTransition()

        assertStockInvariant(stock)
        line.state = target; stock.version += 1
        insert adjustment, command result, and outbox atomically
```

State transition plus counter deltas is one transaction. This is what prevents a
duplicated expiry from releasing a committed order or a duplicated shipment from
subtracting physical stock twice.

## 10. Multi-line reservation saga

```text
function reserveBasket(request):
    intent = intents.createIdempotent(request.id, state=RESERVING)
    held = []
    for line in sortByStockKey(request.lines):
        result = reserveLine(intent.id, line, subkey(intent.id, line))
        if result.failed:
            for prior in reverse(held):
                releaseLine(prior, subkey(intent.id, "compensate", prior))
            intents.mark(intent.id, FAILED)
            return failure(line)
        held.add(line)
    intents.mark(intent.id, HELD)
    return reservation(intent.id)
```

This prevents oversell but not intermediate partial holds; they are hidden by intent
state and bounded by lease/expiry. For small baskets colocated in one database,
deterministic row locks and one transaction are simpler. Do not use distributed
two-phase commit unless the availability/operational trade-off is justified.

## 11. Durable expiration logic

Place reservation/version in coarse minute buckets plus durable database `expires_at`.
Workers scan current/past buckets, claim with leases, and run the same conditional
release transition. A periodic sweep queries overdue HELD rows to recover lost queue
notifications.

```text
function expire(reservationLineId, expectedReservationVersion):
    line = read(lineId)
    if line.state != HELD or line.expiresAt > now: return
    transitionLine(line.id, EXPIRED,
                   commandKey="expiry:" + line.id + ":" + expectedVersion)
```

The transaction rechecks state/time. Expiry delivery can be arbitrarily duplicated
or delayed without double release. Checkout should renew only under bounded policy
and a versioned command, not indefinitely.

## 12. Availability reads and fulfillment selection

Publish stock-version events into regional read models/caches. Return exact by-location
or aggregated buckets such as `AVAILABLE`, `LOW`, `OUT`, with observed version/time.
Fulfillment selection considers shipping cost/SLA, split shipments, location capacity,
and indicative stock, then the reservation command proves availability.

Never expose raw exact stock broadly if it enables abuse. A stale read may cause a
failed reserve but cannot oversell. After reservation failure, retry a different
location with a stable new line subcommand under the same basket intent.

## 13. Hot SKU and flash-sale handling

One linearizable stock key has finite write throughput. Use:

- per-user/device/bot admission and a fair virtual waiting room before inventory;
- bounded queue with stable request IDs and explicit position/expiry;
- batch processing on the single stock owner when latency permits;
- preallocated **escrow buckets** only through a strongly consistent transfer that
  subtracts stock from the central bucket before regional sellers spend it;
- small safety stock and stop-sell when reconciliation/replica certainty is low.

Escrow allows parallel regional reservations because the sum of bucket rights never
exceeds stock. Unused rights require an audited transfer back; do not merely salt a
counter, which would lose the global no-oversell invariant.

## 14. Warehouse reconciliation

Consume WMS events idempotently, but also ingest periodic signed physical snapshots.
For each key compare expected on-hand and WMS count, reservations/allocations, event
offsets, and in-flight operations. Differences create cases with evidence. Automatic
corrections are limited by reason/amount; larger drift requires approval. Correct by
appending an adjustment with source snapshot/version, preserving the full ledger.

## 15. Partitioning and regional consistency

Hash `(sku, location)` to logical shards and colocate its stock, line states, and
adjustments. Split shard maps, but never allow two leaders for one key; consensus
term/fencing rejects the old owner. Route commands to the stock's home region. Serve
availability reads regionally, while failover pauses unsafe writes until a single
up-to-date leader is established.

## 16. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Caller times out after reserve | Same key returns HELD/rejected result |
| Saga fails after some lines | Durable compensations release each held line once |
| Expiry races commit | Row lock/CAS allows exactly one valid transition |
| Expiry worker dies | Lease/bucket replay and overdue sweeper recover it |
| Outbox duplicates/reorders | Stock version makes read projections monotonic |
| Availability cache is stale | Reserve transaction remains authoritative |
| WMS event duplicates | Unique source reference applies one adjustment |
| Shard leader partitions | Fencing rejects old leader; favor consistency/no oversell |
| Flash queue overloads | Admission rejects/queues fairly before hot stock key |

## 17. Security and audit

Use service identities and least privilege: checkout may reserve/release its own holds,
order may commit, WMS may ship/adjust with scoped locations, and humans need approved
roles. Prevent negative/overflow quantities, arbitrary expiries, source-ID reuse,
IDOR, bot hoarding, and replay. Encrypt data, sign events, audit every command/change/
manual correction, separate duties, and apply retention, legal hold, residency, and
seller/location offboarding across logs, projections, caches, and backups.

## 18. Observability

Track reserve/commit/release/ship latency/errors, success/insufficient-stock/conflict,
available/reserved/allocated/on-hand by bounded dimensions, invariant violations,
idempotency replays/hash mismatch, active/overdue holds, expiry lateness, saga age/
compensation, hot-key queue depth/fairness, escrow allocation/utilization, shard leader
changes, read-model lag, WMS event age, reconciliation drift/corrections, and oversell/
undersell business incidents.

State-machine/property tests generate duplicate/reordered reserve/commit/expiry/ship
commands and assert conservation/nonnegative counters. Model-check expiry/commit races.
Load-test one flash key, not only uniform keys. Chaos tests kill coordinators/workers/
leaders; reconciliation verifies stock counters equal sums of active line states and
immutable adjustments.

## 19. Implementation path

1. **MVP:** one strongly consistent database, stock invariant, idempotent single-line
   reserve/commit/release, immutable adjustments, and authoritative availability.
2. **Checkout lifecycle:** multi-line saga, expiry buckets/sweeper, shipments, outbox,
   regional read model, WMS integration, and reconciliation.
3. **Scale:** logical shards/fenced leaders, hot-SKU admission/fair batching, escrow
   rights where justified, seller/location partitioning, and capacity controls.
4. **Hardening:** regional failover/no-oversell drills, security/audit lifecycle,
   model/property/load/chaos tests, restores, runbooks, and SLOs.

## 20. Final design

Represent stock as conserved on-hand, reserved, and allocated buckets owned by one
strongly consistent SKU/location shard. Atomic conditional transitions and immutable
adjustments make reserve, commit, expiry, cancellation, and shipment idempotent and
auditable. Multi-line checkout is a compensating saga; stale read models may reject
but cannot oversell. Durable expiry/reconciliation repair failures, while fair
admission or preallocated escrow rights scale flash demand without inventing stock.
