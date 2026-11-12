# Complete Solution: Order Management System

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Create an order from a checkout snapshot, preserve the exact commercial agreement,
coordinate inventory and payment, route fulfillment, expose customer status, and
support cancellation, partial shipment, return, replacement, and refund. Every
external callback/retry is idempotent and every material transition is auditable.

Targets: create/query p99 below 400/200 ms, 99.99% reads and 99.9% commands, accepted
orders never lost, workflow steps normally progress within seconds, and stuck states
detected within minutes. The order aggregate is strongly consistent per order;
payment/inventory/warehouse coordination is an eventually completing saga with
explicit `PENDING`/`UNKNOWN` states, never fictional distributed atomicity.

## 2. Capacity estimation

Assume 10 million orders/day, five lines/order, 20 durable events/order, 10 status
reads/order, 10 KB order snapshot, seven-year financial retention, and 10x campaigns.

- Order creates average 116/s and peak near 1,200/s.
- Events average 2,300/s and peak above 23,000/s.
- Status reads average 1,160/s and peak above 12,000/s.
- Initial order data adds about 100 GB/day; immutable events, fulfillment, returns,
  indexes, replicas, and archives multiply it.
- Partition by order ID and separately index user/time; campaign skew is usually
  seller/SKU downstream, not one order key.

## 3. Domain and invariants

The order owns immutable item/price/tax/discount/address snapshots and workflow state.
Pricing, payment, inventory, shipment, and refund services remain authoritative for
their domains. The OMS stores their stable references and observed states.

Core invariants:

- one client idempotency key creates at most one order;
- `sum(line totals) + tax + shipping - discounts = order total` in integer minor units;
- fulfilled/cancelled/returned quantities never exceed ordered quantity;
- captured minus refunded never exceeds authorized/captured legal amounts;
- every transition matches current version/state and appends one immutable event;
- no external uncertainty is interpreted as success or failure without evidence.

## 4. APIs

```text
POST /v1/orders                         {checkoutSnapshotId} Idempotency-Key
GET  /v1/orders/{orderId}
GET  /v1/users/me/orders?cursor=&limit=
POST /v1/orders/{orderId}/cancel        {lines, reason} Idempotency-Key
POST /v1/orders/{orderId}/returns       {lines, reason} Idempotency-Key
GET  /v1/orders/{orderId}/events?cursor=

POST /internal/orders/{id}/payment-events       providerEventId
POST /internal/orders/{id}/inventory-events     eventId
POST /internal/orders/{id}/fulfillment-events   eventId
```

Customer commands authenticate ownership; internal callbacks use mutually authenticated
service identity/signature. Bound lines, quantity, request size, pagination, cancel/
return windows, and retry rate. Mutations return order version and operation status.

## 5. Data model

```text
Order(id, user_id, state, version, currency, subtotal, discount, tax,
      shipping, total, checkout_snapshot_id, address_snapshot_ciphertext,
      created_at, updated_at)
OrderLine(id, order_id, sku, seller_id, title_snapshot, unit_price,
          discount, tax, ordered_qty, reserved_qty, allocated_qty,
          shipped_qty, cancelled_qty, returned_qty, refunded_qty, version)
PaymentRef(order_id, payment_intent_id, state, authorized_amount,
           captured_amount, refunded_amount, version)
InventoryRef(order_id, reservation_id, state, expires_at, version)
Fulfillment(id, order_id, location_id, state, carrier, tracking_ref, version)
FulfillmentLine(fulfillment_id, order_line_id, quantity)
Return(id, order_id, state, reason, received_at, version)
OrderEvent(order_id, sequence, type, payload, actor, command_id, created_at)
Saga(order_id, workflow, step, state, attempt, next_attempt_at, lease_until)
Inbox(source, external_event_id, payload_hash, processed_at)
Outbox(id, order_id, sequence, event_type, payload, published_at)
```

Order-event sequence increments with aggregate version. Store commercial snapshots,
not mutable catalog references alone. Sensitive address/customer fields are encrypted
and access-scoped.

## 6. State model

Avoid one giant enum encoding every combination. Keep an overall derived state plus
orthogonal payment, inventory, fulfillment, and return state machines:

```text
Order:       PENDING -> CONFIRMED -> PROCESSING -> PARTIALLY_FULFILLED -> FULFILLED
                \-> PAYMENT_FAILED / CANCELLED
Payment:     NONE -> AUTHORIZING -> AUTHORIZED -> PARTIALLY_CAPTURED -> CAPTURED
                                      \-> VOIDED; captured -> PARTIALLY_REFUNDED -> REFUNDED
Inventory:   NONE -> RESERVING -> RESERVED -> ALLOCATED -> SHIPPED
                          \-> RELEASED / FAILED
Fulfillment: PLANNED -> ACCEPTED -> PICKING -> PACKED -> SHIPPED -> DELIVERED
                                      \-> CANCELLED / EXCEPTION
Return:      REQUESTED -> APPROVED -> IN_TRANSIT -> RECEIVED -> REFUNDED / REJECTED
```

Overall state is recalculated from line quantities and sub-states. History never
changes; corrections append events.

## 7. Architecture

```text
checkout -> order API -> order SQL shard + event/outbox
                                 |
                             order event log -> read models/notifications/analytics
                                 |
                         saga orchestrator + durable timers
                         /          |             \
                 inventory adapter payment adapter fulfillment adapter
                         |          |             |
                    inventory   payment PSP    warehouse/carrier

reconciliation workers <-> order/external status APIs and settlement/WMS feeds
```

Use orchestration because monetary/stock compensations and customer-visible state
need an explicit durable plan. Adapters translate provider-specific protocols into
canonical commands/events. Transactional outbox prevents committed state without an
event; inbox prevents repeated callback effects.

## 8. Step-by-step workflow

1. Checkout creates an immutable priced basket snapshot. Order API validates ownership,
   quote expiry, totals, address, and idempotency, then commits `PENDING` order/event/
   outbox in one transaction.
2. Orchestrator sends idempotent inventory reservation using order ID and deadline.
   Success records reservation/version; failure cancels order before charging.
3. Send idempotent payment authorization for exact order amount. Definitive decline
   releases reservation and marks payment failure; timeout becomes `AUTHORIZING_UNKNOWN`
   and is queried/reconciled before retry or release.
4. When stock and authorization are proven, transition to `CONFIRMED` and request
   fulfillment. Warehouse accepts/allocates lines.
5. Capture payment according to policy (on confirmation or shipment). Shipment events
   advance line quantities, commit inventory shipment, notify customer, and derive
   partial/full order state.
6. Cancellation/return validates remaining quantities, asks downstream systems, then
   releases/voids/refunds through durable compensation steps. Reconciliation closes
   mismatches and stuck unknown states.

## 9. Atomic command and transition logic

```text
function applyOrderCommand(actor, orderId, command):
    requestHash = canonicalHash(command.payload)
    transaction on shard(orderId):
        prior = inboxOrCommands.get(command.source, command.id)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response

        order = orders.getForUpdate(orderId)
        require authorize(actor, command, order)
        require validTransition(order, command)
        changes = stateMachine.reduce(order, lines(orderId), command)
        require quantitiesAndMoneyRemainValid(changes)

        apply(changes)
        order.version += 1
        sequence = order.version
        event = orderEvents.insert(order.id, sequence, command.type,
                                   changes.auditPayload, actor, command.id)
        outbox.insert(order.id, sequence, event.type, event.payload)
        result = summarize(order, changes)
        inboxOrCommands.insert(command.source, command.id, requestHash, result)
    return result
```

State, lines, event, outbox, and dedupe commit together. An invalid/out-of-order
callback is recorded for investigation or safely ignored if an older known version;
it never forces state backward.

## 10. Saga orchestration logic

```text
function advanceOrderSaga(orderId):
    saga = sagas.claimDue(orderId, worker, lease=30s)
    if saga == null: return
    order = orders.get(orderId)

    switch saga.step:
      RESERVE_INVENTORY:
        send Reserve(order.lines, key=order.id + ":reserve:v1")
        wait for callback/query result
      AUTHORIZE_PAYMENT:
        send Authorize(order.total, key=order.id + ":authorize:v1")
        wait for callback/query result
      CONFIRM:
        applyOrderCommand(system, order.id, Confirm(expected sub-states))
        saga.moveTo(REQUEST_FULFILLMENT)
      COMPENSATE_RESERVATION:
        send Release(reservationId, key=order.id + ":release:v1")
      RECONCILE_UNKNOWN:
        query external system by stable reference; do not duplicate effect blindly
```

Commands are at least once and carry stable idempotency keys. The saga persists
before calls, records responses through the order command path, uses exponential
jitter, and has an absolute deadline/manual-review state. A worker crash resumes from
durable step, not memory.

## 11. External-call ambiguity

There is no atomic transaction across OMS and PSP/WMS. If an HTTP timeout occurs, the
remote effect may have happened. Mark `UNKNOWN`, query by stable request/reference,
accept signed callbacks, and reconcile provider reports. Never issue a new unrelated
payment authorization because the old request timed out.

Adapters persist mapping `(order, operation, generation) -> provider reference` before
or with the outbound attempt. Provider callbacks are signature/timestamp verified,
stored raw, deduplicated by provider event ID, and applied only to the mapped order.

## 12. Cancellation logic

```text
function requestCancellation(user, orderId, requestedLines, commandId):
    transaction:
        order = lock(orderId)
        for requested in requestedLines:
            line = lockLine(requested.lineId)
            cancellable = line.orderedQty - line.shippedQty
                          - line.cancelledQty - pendingCancellationQty(line)
            require 0 < requested.qty <= cancellable
            create CancellationLine(PENDING, requested.qty)
        append OrderCancellationRequested and outbox

orchestrator:
    ask warehouse to stop unshipped quantities
    once confirmed, release inventory allocation if required
    void uncaptured authorization or refund captured amount
    atomically mark quantities CANCELLED only from proven results
```

If already shipped, direct the quantity into return flow. Partial failures stay
visible per line; do not mark the whole order cancelled until every requested unit
reaches a terminal state.

## 13. Fulfillment, capture, and partial orders

The fulfillment planner groups lines by location/seller/shipping promise. Each group
has independent state. On shipment, validate cumulative quantity, record carrier
reference, tell inventory to consume allocation, and capture the corresponding amount
if capture-on-ship. Allocate discounts/tax deterministically per line so partial
capture/refund totals sum exactly to the order total, with documented rounding remainder.

Duplicate shipment/capture events use source IDs and cannot advance quantities twice.
Overall `FULFILLED` requires all noncancelled units shipped/delivered per product
definition; otherwise expose partial state and individual fulfillment timelines.

## 14. Returns and refunds

Return eligibility uses immutable sale time/policy version, delivery evidence, item
type, quantity, and prior returns. Approval creates an RMA and expected lines. Warehouse
receipt/inspection decides restock, damaged, or rejected; inventory receives a unique
adjustment. Refund request uses stable `(return, line, amount, generation)` and payment
reconciliation. Customer status distinguishes requested, received, refund pending,
and refunded—never declares refund from an outbound request alone.

## 15. Read models and customer timeline

Outbox relay publishes ordered per-order events. Consumers build customer list,
seller queue, fulfillment view, and timeline conditionally by source sequence. The
detail API may read primary for read-your-write; list/history uses projections and
returns freshness watermark. Cache is versioned by order/version.

Cursor pagination uses `(created_at, order_id)` for user history. Read policy masks
PII by role and rechecks ownership even if a stale projection contains the row.

## 16. Partitioning and retention

Hash order ID to logical database shards; colocate order, lines, events, inbox/outbox,
and saga where possible. Maintain user/time and seller/status projections separately
instead of cross-shard primary scans. Use sortable IDs for operational locality only
if shard balance remains safe.

Keep recent active orders in hot storage and immutable financial/audit history in
partitioned archive with verified restores. Data retention separates legal financial
records from erasable/minimized customer PII.

## 17. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client retries create | Same idempotency key returns same order |
| Outbox publish fails | Relay retries committed row; consumers dedupe sequence |
| Orchestrator dies | Saga lease expires and resumes durable step |
| External call times out | Enter UNKNOWN, query/reconcile stable reference |
| Payment declines | Release inventory idempotently, mark definitive failure |
| Fulfillment rejects | Replan or cancel affected lines and void/refund |
| Callback duplicates/reorders | Inbox ID/version plus valid transitions suppress regression |
| Read projection lags | Detail reads primary; list exposes watermark |
| Order shard region fails | Fenced replica promotion prevents split-brain transitions |

## 18. Security, privacy, and compliance

Authorize customer, seller, warehouse, support, finance, and admin operations with
least privilege and field-level masking. Tokenize payment instruments outside OMS;
encrypt address/contact snapshots with rotating keys; prevent IDOR, quantity/amount/
currency tampering, forged callbacks, replay, refund abuse, and CSV/formula injection.
Audit every state/manual override/refund/export/access. Apply tax/financial retention,
privacy erasure/minimization, legal hold, residency, fraud review, and separation of
duties across primary, events, projections, logs, archives, and backups.

## 19. Observability

Track create/query/command latency/errors, orders and value by state, transition
rejects, idempotency replays/hash mismatch, age in each saga/sub-state, retries/
timeouts/unknowns, inventory reserve/release, authorization/capture/void/refund,
partial fulfillment, cancellations/returns, outbox/inbox/read lag, callback signature
failures, shard skew, and reconciliation mismatches. Alert on business invariants and
stuck money/stock, not only infrastructure.

State-machine/property tests generate duplicated/reordered callbacks, partial line
operations, and crash points and assert quantity/money invariants. Contract-test each
adapter. Load-test campaign/order-history patterns. Chaos tests kill orchestrators,
brokers, external dependencies, and leaders. Reconciliation compares every nonterminal
external reference with provider/WMS truth.

## 20. Implementation path

1. **MVP:** transactional order/line snapshot, explicit state machine, idempotent
   create/cancel, immutable events, primary detail, and manual operations.
2. **Reliable checkout:** outbox/inbox, durable orchestrator/timers, inventory/payment
   adapters, UNKNOWN reconciliation, compensations, and customer timeline.
3. **Fulfillment lifecycle:** partial shipments/capture, warehouse/carrier, returns/
   refunds, seller projections, archive, and automated reconciliation.
4. **Hardening:** sharding/regional fencing, fraud/security/privacy/financial controls,
   state/property/load/chaos tests, restores, SLOs, runbooks, and admin tooling.

## 21. Final design

Keep a versioned order aggregate and immutable commercial snapshot as the durable
source of customer truth. Every command conditionally transitions state and commits
its audit event/outbox/dedupe together. A persistent orchestrator drives idempotent
inventory, payment, and fulfillment operations, treats timeouts as unknown, and uses
explicit compensation/reconciliation rather than distributed transactions. Per-line
quantities and orthogonal sub-state machines make partial fulfillment, cancellation,
returns, and refunds correct and understandable end to end.
