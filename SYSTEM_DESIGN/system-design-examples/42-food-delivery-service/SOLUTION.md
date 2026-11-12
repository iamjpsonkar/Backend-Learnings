# Complete Solution: Food-Delivery Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Customers discover open restaurants, browse versioned menus, build a cart, receive a
priced quote, place/pay for an order, track restaurant acceptance/preparation, courier
assignment/pickup/delivery, communicate safely, cancel/refund, and rate. Restaurants
manage menu/availability/capacity and preparation. Couriers stream location, accept
tasks, navigate, and earn settlement.

Targets: restaurant/menu reads p99 below 250 ms, checkout decision below two seconds
excluding external payment, restaurant acknowledgment within one minute, courier match
within two minutes, live location age below five seconds, and 99.99% status reads with
99.95% workflow commands. Order state is strongly consistent per order; menu/search,
location, ETA, notifications, and projections are eventual. External ambiguity remains
explicit and reconciled.

## 2. Capacity estimation

Assume 20 million orders/day, two million online couriers updating every five seconds,
ten million restaurants, 50 menu items/restaurant, 20 workflow events/order, and 5x
meal peaks.

- Orders average 231/s and peak around 1,200/s, geographically concentrated.
- Courier location averages 400,000 updates/s before customer tracking reads.
- Order events average 4,600/s and peak over 23,000/s.
- 500 million menu items at 1 KB are 500 GB before search/cache/media/replicas; menu
  changes are bursty around meal boundaries.
- Restaurant tablet and courier offer connections need regional gateway fleets; one
  restaurant/city outage must not consume all queues.

## 3. APIs

```text
GET  /v1/restaurants?location=&filters=&cursor=
GET  /v1/restaurants/{id}/menu
POST /v1/order-quotes                     {restaurantId, items, address} Idempotency-Key
POST /v1/orders                           {quoteId, paymentMethodToken} Idempotency-Key
GET  /v1/orders/{id}
POST /v1/orders/{id}/cancel               Idempotency-Key
POST /v1/restaurant-orders/{id}/accept    {prepMinutes} Idempotency-Key
POST /v1/restaurant-orders/{id}/reject    {reason} Idempotency-Key
POST /v1/delivery-offers/{id}/accept      Idempotency-Key
POST /v1/deliveries/{id}/arrive|pickup|complete Idempotency-Key, If-Match
POST /v1/courier-locations                {session, sequence, points[]}
```

Bound cart items/quantities/modifiers, delivery distance, quote lifetime, request
size/rate, prep estimates, courier offers, and location batches. Monetary amounts are
integer minor units. All participant commands are actor-scoped and idempotent.

## 4. State model and invariants

```text
Order: CREATED -> PAYMENT_PENDING -> RESTAURANT_PENDING -> ACCEPTED -> PREPARING
       -> READY_FOR_PICKUP -> PICKED_UP -> DELIVERED
       pre-delivery -> CANCELLING -> CANCELLED; any stage -> EXCEPTION
Payment: NONE -> AUTHORIZING -> AUTHORIZED -> CAPTURED -> PARTIALLY/FULLY_REFUNDED
Delivery: UNASSIGNED -> DISPATCHING -> ASSIGNED -> AT_RESTAURANT -> PICKED_UP
          -> AT_CUSTOMER -> COMPLETED; pre-pickup -> REASSIGNING/CANCELLED
Offer: PENDING -> ACCEPTED | DECLINED | EXPIRED | REVOKED
```

Invariants:

- an order contains an immutable item/price/tax/fee/address/policy snapshot;
- one order has at most one active courier assignment (or one explicit batch plan);
- a courier cannot accept incompatible simultaneous tasks;
- picked-up quantity/order cannot be cancelled as if food were still at restaurant;
- capture/refund/restaurant/courier pay references are unique and amount-bounded;
- state transitions, event, outbox, and command dedupe commit together.

## 5. Data model

```text
Restaurant(id, location, timezone, state, capacity_state, menu_version, version)
MenuItem(id, restaurant_id, name, base_price, modifiers, availability,
         schedule, tax_category, version)
OrderQuote(id, customer_id, restaurant_id, menu_version, item_snapshot,
           subtotal, discounts, tax, fees, courier_tip, total, currency,
           delivery_address_ciphertext, route_version, expires_at)
Order(id, customer_id, restaurant_id, state, version, quote_id,
      payment_intent_id, promised_at, created_at)
RestaurantTask(order_id, state, accepted_at, prep_ready_at, version)
Delivery(id, order_id, courier_id, zone_id, state, dispatch_epoch,
         pickup_eta, delivery_eta, version)
DeliveryOffer(id, delivery_id, dispatch_epoch, courier_id, state, expires_at)
Courier(id, state, active_task_ids, vehicle, city_id, version)
OrderEvent(order_id, sequence, type, actor, payload, created_at)
Inbox(source, event_id, payload_hash, processed_at)
Outbox(id, aggregate_id, sequence, event_type, payload, published_at)
```

## 6. Architecture

```text
customer -> restaurant search/menu CDN/cache -> quote/pricing/tax/routing
customer -> order API -> order SQL/state/outbox -> durable saga/timers
                                      |       |       |
                              restaurant   payment   dispatch trigger
                               gateways              |
                                       zone matcher -> courier offer gateways
                                                         |
courier location gateway -> stream -> latest geospatial index/tracking/ETA

order events -> customer tracking/notifications/read models/analytics
ledger/reconciliation <-> payment, restaurant payable, courier payable/refunds
```

Partition orders by ID/home city and dispatch/location by zone. Menus/search are
versioned read-heavy projections. Restaurant/courier channels and partner adapters are
isolated so a slow participant does not block the order database.

## 7. Step-by-step workflow

1. Search filters indexed restaurants by delivery area, opening hours, capacity,
   category and coarse ETA; menu read returns versioned current items.
2. Quote validates item/modifier availability against authoritative menu, calculates
   promotions/tax/service/delivery fees/tip, routes address, snapshots all inputs,
   currency/policies, and expires shortly.
3. Order create claims idempotency, validates quote/customer/address/payment readiness,
   persists order/snapshot reference/outbox, and starts payment authorization with a
   stable intent. Timeout remains payment unknown.
4. After authorization, send restaurant task with stable order/version. Restaurant
   accepts with prep estimate or rejects; timeout escalates/contact/rejects by policy.
5. On acceptance capture payment according to product contract and schedule courier
   dispatch so pickup arrival aligns with predicted food readiness, not immediately.
6. Matcher sends bounded expiring offers. First valid accept atomically assigns delivery
   and courier. Tracking updates customer/restaurant and continuously recalculates ETA.
7. Restaurant READY and courier ARRIVE/PICKUP commands converge; pickup proof moves
   custody. Delivery proof/PIN/photo policy completes order and posts ledger payables.
8. Cancellation/failure saga stops outstanding work, releases courier, voids/refunds,
   and compensates restaurant/courier according to stage/evidence.

## 8. Quote and menu consistency

```text
function createQuote(customer, request, key):
    restaurant = restaurants.requireOrderable(request.restaurantId, now)
    menu = menus.readVersion(restaurant.menuVersion)
    normalizedItems = []
    for requested in request.items:
        item = menu.requireAvailable(requested.itemId, now)
        require requested.quantity within limits
        modifiers = item.validateModifiers(requested.modifiers)
        normalizedItems.add(snapshot(item, modifiers, requested.quantity))
    route = routing.route(restaurant.pickup, request.address)
    require route.distance <= restaurant.deliveryRadiusPolicy
    price = pricing.compute(normalizedItems, customer, restaurant, route)
    tax = taxService.quote(price, itemTaxCategories, addresses)
    persist idempotent immutable quote with menu/price/tax/route/policy versions + expiry
```

If menu price/availability changes after quote, order creation follows a documented
guarantee window or returns `REQUOTE_REQUIRED`. Never substitute/delete an item without
customer consent. Restaurant may mark out-of-stock; projection/search catches up later.

## 9. Core order command logic

```text
function applyCommand(actor, orderId, command):
    requestHash = canonicalHash(command)
    transaction on order shard:
        prior = commandDedupe.get(actor.key, command.id)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response
        order = orders.getForUpdate(orderId)
        require actorMayPerform(actor, command, order)
        require stateMachineAllows(order, command)
        changes = reduce(order, restaurantTask, delivery, command)
        require moneyAndCustodyInvariants(changes)
        apply(changes); order.version += 1
        event = orderEvents.insert(order.id, order.version, command, actor)
        outbox.insert(event)
        commandDedupe.insert(actor.key, command.id, requestHash, result)
    return result
```

Callbacks and offline device commands enter the same path. Older versions cannot move
state backward. An invalid contradictory event is retained/quarantined for reconciliation.

## 10. Restaurant acceptance and prep prediction

Restaurant gateway delivers pending orders at least once; tablet ACK does not mean
acceptance. Accept command includes explicit prep duration, item exceptions (which
require customer flow), and task version. One restaurant may have multiple devices,
but transactional task state accepts one decision.

Prep model combines restaurant/item/day/time/load/history/courier availability and
tablet estimate. Update prediction on acceptance, prep progress, and READY. Durable
timers alert restaurant/support at ACK/accept/prep deadlines. A restaurant offline or
reject causes payment void/refund and order cancellation; accepted food can incur
compensation under policy.

## 11. Timed courier dispatch

Ideal courier arrival is near ready time:

```text
dispatchAt = predictedReadyAt - predictedTravelToRestaurant - pickupBuffer
```

Use a durable versioned timer. If prep estimate shifts, reschedule with new generation;
old timer becomes no-op. Dispatch early in low supply or long pickup travel and later
when oversupply/restaurant delay is likely. Optimize combined customer lateness,
courier waiting, food quality, cost and fairness—not travel ETA alone.

## 12. Candidate and offer logic

Location stream/session sequence maintains an expiring H3/S2 index of AVAILABLE
couriers. Matcher expands pickup cells, filters stale/ineligible/vehicle/capacity,
batch-computes route ETA, then scores:

```text
score = pickupETA + expectedCourierWait + expectedCustomerLateness
        + detourCost + assignmentRisk
        - idleTimeFairnessCredit - compatibleBatchBenefit
```

Send small offer waves tagged with delivery dispatch epoch and expiry. First valid
accept transaction locks delivery/courier, verifies both states/epoch/eligibility,
sets assignment, revokes other offers, and writes outbox/dedupe. A delayed accept is
rejected. On timeout/courier cancel, atomically detach, increment epoch, and redispatch.

## 13. Batched delivery

Batch only compatible orders with similar pickup readiness, route direction, food
temperature/handling constraints, promised times, vehicle capacity, and legal/product
rules. A batch planner simulates stop sequence and accepts only if every order's
lateness/quality guardrail remains satisfied. Persist immutable plan version and
ordered stops; dynamic changes create a new version and notify participants.

Courier assignment can carry multiple task IDs with a capacity/compatibility constraint,
not an unbounded “active task” loophole. Pickup/delivery proof and pay are per order.

## 14. Pickup, delivery, and proof

ARRIVE requires assigned courier and pickup geofence or audited override. PICKUP
requires restaurant READY (or explicit handoff), one-time order code/scan, and custody
timestamp. After pickup, customer cancellation becomes support/refund resolution, not
inventory rollback.

Completion requires destination geofence plus PIN/signature/photo/recipient confirmation
according to fraud/privacy/accessibility policy. Proof is encrypted, access-limited,
and retained only as necessary. Contactless/unattended delivery has explicit safe-
location and failure rules.

## 15. Live tracking and ETA

Courier app sends session/sequence/accuracy/speed/heading points. Gateway validates
plausibility, map-matches, appends stream; consumers conditionally update latest/index.
Only assigned customer/restaurant/support receives short scoped stream token. Gateways
coalesce updates and include event time/accuracy/staleness.

ETA combines route/traffic, courier position, remaining restaurant prep, pickup wait,
batch stops, parking/building and historical bias. Continuously calibrate prediction
intervals; show a range when uncertainty is high. Tracking outage never advances state.

## 16. Cancellation and compensation

Policy depends on stage and actor:

- before authorization/restaurant acceptance: cancel and void without food cost;
- after restaurant accepts/prepares: customer may owe restaurant/cancellation fee;
- after courier assignment/arrival: courier may receive compensation;
- after pickup: resolve delivery/return/disposal and refund by evidence, not simple cancel.

Saga first commits `CANCELLING` and stable compensation commands, then revokes offers/
releases courier, cancels restaurant where possible, voids/refunds payment, and finally
marks terminal from proven results. Timeouts become UNKNOWN and reconcile.

## 17. Payment, ledger, and settlement

Use payment authorization before exposing restaurant to unpaid risk; capture at
acceptance/pickup according to contract. All calls use stable order operation IDs.
Ledger posts customer charge/receivable, restaurant payable, courier payable, platform
fees, tax, tips, promotions/subsidies, adjustments and refunds as balanced entries.

Restaurant/courier payout follows delivered/eligible ledger payables and batch provider
settlement. Reconcile payment, order state, ledger, participant statements and bank/
provider files. Payment failure after accepted work follows collections/compensation,
not deletion of the order.

## 18. Scaling and degradation

Cellize by city/metro with independent order/matcher/location/gateway capacity; keep
active order in its home cell. Partition restaurants and courier zones, query neighbors
at boundaries, and isolate hot chains/meal peaks with fair queues. Menus/search/CDN
replicate globally; one fenced leader owns each order/assignment transition.

Under load, preserve order/callback/timer/state commands, reduce search ranking sources,
serve cached menus with version checks at quote, lower tracking frequency/coalesce,
pause optional batching, and shrink service area/acceptance based on real capacity.
Never accept orders that cannot be fulfilled merely to keep API availability green.

## 19. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client retries order/command | Same key/hash returns original resource/result |
| Restaurant tablet offline | Retry/escalate until deadline, then compensate/cancel |
| Prep timer duplicates after update | Generation mismatch makes old timer no-op |
| Two couriers accept | Delivery/courier locks and epoch allow one assignment |
| Courier disappears prepickup | Grace, detach atomically, increment epoch, redispatch |
| Location/index fails | Rebuild from stream/latest; state remains authoritative |
| Payment/refund times out | Mark UNKNOWN and reconcile stable reference |
| Notification fails | Workflow continues; client polls current state |
| City cell partitions | Fence old writer and reject ambiguous transitions |

## 20. Security, safety, and privacy

Authorize customer/restaurant/courier/support/finance operations and field-mask address,
phone, proof, and payment. Verify restaurant/courier identity, food/vehicle eligibility,
device integrity, signed callbacks, one-time pickup/delivery codes, mTLS, encryption,
rate limits, tamper-evident audit, and dual control for refunds/overrides. Prevent IDOR,
account takeover, fake GPS, order/refund/promotion fraud, restaurant self-orders,
courier collusion/theft, tip/amount tampering, bot menu scraping, contact abuse, and
insider location/address lookup.

Provide SOS/incident/contact masking, allergy information handling (without promising
unverified safety), accessibility, dangerous-address/courier safety, and support. Apply
food delivery/worker/tax/payment laws, consent/minimization/retention/deletion, legal
hold, residency, dispute evidence, incident response, and backup/key recovery.

## 21. Observability

Track search/menu/quote/order latency/errors, menu-version/requote/out-of-stock, orders
by stage and stage age, payment authorization/capture/refund unknowns, restaurant ACK/
accept/prep estimate/error/ready delay, dispatch timing, candidate/offer/accept/reassign,
courier location age/accuracy, pickup wait, promised/actual ETA error, batch lateness,
cancellations/compensation, delivery proof/disputes, payout, city/restaurant/courier
saturation, leader changes, outbox/timer lag, and reconciliation mismatch count/value.

State/property tests duplicate/reorder restaurant/courier/payment commands and race
accept/cancel/reassign. Simulate prep and courier movement to validate dispatch/ETA/
batch constraints. Load-test meal peak, hot chains and weather/event zones. Chaos tests
kill gateways/timers/matcher/location/payment/cells; controls prove one active courier
assignment and order-payment-ledger-participant agreement.

## 22. Implementation path

1. **MVP:** one city, versioned menus/quote, order/restaurant state machine, payment,
   manual courier assignment, basic tracking, delivery proof, and refunds.
2. **Reliable marketplace:** durable saga/timers, outbox/inbox, prep prediction,
   location index/matcher/offer epochs, compensation/reconciliation, and participant pay.
3. **Scale/intelligence:** city cells, search/cache, dynamic dispatch timing, ETA,
   batching, capacity-based service areas, incentives, regional gateways, and fraud/safety.
4. **Hardening:** fenced failover, security/privacy/food/worker/payment controls,
   state/simulation/peak/chaos tests, restores, drills, runbooks, and SLOs.

## 23. Final design

Use a versioned quote and per-order state machine as the durable customer contract.
A persistent saga authorizes payment, obtains restaurant acceptance/prep readiness,
times courier dispatch, and compensates each failure explicitly. High-rate courier
locations feed a rebuildable zone index; bounded offer waves and one atomic assignment
prevent double dispatch. Versioned restaurant/courier commands, durable timers, scoped
tracking, delivery proof, and balanced participant settlement make the full meal path
recoverable from cart through restaurant, courier, payment, and payout.
