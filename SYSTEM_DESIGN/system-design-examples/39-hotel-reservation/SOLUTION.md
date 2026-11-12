# Complete Solution: Hotel Reservation

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Travelers search by location/dates/guests/filters, view room types and rate plans,
revalidate a priced offer, hold room-nights, pay, confirm, modify/cancel, and receive
a voucher. Properties and channel partners synchronize inventory, rates, restrictions,
reservations, and cancellations. The system detects and resolves allocation drift.

Targets: search p99 below 500 ms, availability/quote below 300 ms, booking decision
below two seconds excluding partner/payment, 99.99% search and 99.95% commands, and no
oversell beyond explicit property policy. Search is stale by design; a hold/partner
confirmation is authoritative. External timeouts are unknown, never guessed failures.

## 2. Capacity estimation

Assume one million properties, ten room types/property, 365-day sellable horizon,
100,000 peak search QPS, 1,000 booking QPS, three-night average stay, 20 candidates
rechecked/search, and 10x campaigns.

- Room-type/date rows total about 3.65 billion; at 100 bytes this is 365 GB before
  indexes, versions, allocation sources, and replicas.
- Search fan-out cannot perform live checks against all properties. Use geographic/
  attribute/rate index, then recheck only candidates.
- A booking touches three room-night counters on average; deterministic locks and
  property partitioning keep this local.
- Partner inventory/rate updates can burst into millions/minute; stage, coalesce by
  newest source version, and isolate adapters from interactive booking capacity.
- Rate/availability cache keys grow by location/date/occupancy/filter combinations;
  cache popular result components, not every full query permutation.

## 3. Inventory semantics

Inventory is by `property + room type + local stay date`, where date is in the
property's IANA time zone. Checkout date is exclusive. For owned/allocated inventory:

```text
sellable = physical_or_allocated - safety_stock - held - confirmed + allowed_overbook
```

`allowed_overbook` is an explicit property/room/date policy with limits and audit,
not an implementation race. A reservation consumes one unit for every night in
`[check_in_date, check_out_date)`. All nights must succeed or none are held.

For free-sale partners without local allocation, local availability is indicative;
only the partner's stable confirmation proves inventory. Clearly distinguish these
models in the offer.

## 4. APIs

```text
GET  /v1/search?lat=&lng=&checkIn=&checkOut=&guests=&filters=&cursor=
GET  /v1/properties/{id}/offers?checkIn=&checkOut=&occupancy=
POST /v1/quotes                           {offerId, dates, occupancy} Idempotency-Key
POST /v1/holds                            {quoteId, rooms[]} Idempotency-Key
POST /v1/holds/{id}/confirm               {paymentMethodToken, guests} Idempotency-Key
GET  /v1/reservations/{id}
POST /v1/reservations/{id}/cancel         Idempotency-Key
POST /v1/reservations/{id}/modify         Idempotency-Key
POST /internal/partners/{id}/updates      sourceMessageId/version
```

Bound stay length/horizon, rooms/request, occupancy, guest fields, search radius/
filters/page size, hold TTL, and attempts. Money uses integer minor units plus
currency; dates are property-local civil dates with explicit timezone.

## 5. Data model

```text
Property(id, owner_or_partner, timezone, location, state, content_version)
RoomType(id, property_id, code, capacity, attributes, state, version)
RoomNight(property_id, room_type_id, stay_date, base_capacity,
          held, confirmed, safety_stock, overbook_limit, version)
Allocation(id, partner_id, property_id, room_type_id, date_range,
           quantity, model, source_version, state)
RatePlan(id, property_id, room_type_id, currency, cancellation_policy_id,
         meal_plan, occupancy_rules, restrictions, version)
RateNight(rate_plan_id, stay_date, base_amount, taxes_fees, source_version)
Quote(id, property_id, room_type_id, rate_plan_id, dates, occupancy,
      nightly_breakdown, taxes_fees, total, currency, policy_snapshot,
      inventory_model, versions, expires_at)
Hold(id, quote_id, user_id, state, expires_at, version)
HoldNight(hold_id, property_id, room_type_id, stay_date, quantity)
Reservation(id, hold_id, user_id, state, partner_reference,
            payment_intent_id, version, confirmed_at)
Inbox(source, external_event_id, source_version, payload_hash, processed_at)
Outbox(id, aggregate_id, sequence, event_type, payload, published_at)
```

Store guest/address/identity fields encrypted and separately access-controlled. The
quote snapshots price, policy, occupancy, inventory model, and source versions; it is
not recomputed after customer acceptance without reconfirmation.

## 6. Architecture

```text
client -> search API -> geo/content/rate-availability index + cache
                     -> offer aggregator -> authoritative rate/inventory read
client -> booking API -> property inventory shard + holds/expiry/outbox
                              |        |
                         saga/workflow +-> payment gateway
                              |
                         partner adapter -> hotel/OTA channel manager

partner feeds -> safe adapter/staging -> versioned rate/inventory/content stores
events -> search projection/notifications/analytics
partner reports/PMS snapshots -> reconciliation cases/repairs
```

Partition authoritative room-night inventory by property (and date bucket for storage
while retaining multi-night transaction access). One property home cell serializes
holds. Partner adapters normalize semantics and have separate queues/circuits.

## 7. Step-by-step workflow

1. Search index retrieves geographically/content-eligible properties with indicative
   minimum price/availability. Rank and cursor-page them under a pinned index version.
2. Offer aggregator batch-fetches current candidate room-night summaries, rate plans,
   occupancy/restrictions, taxes/fees, partner health, and returns labeled offers.
3. Selected offer is revalidated into a short immutable quote with nightly price,
   policies, source versions, exact occupancy, currency, and expiry.
4. For locally controlled allocation, hold transaction locks all room-night rows in
   date order, proves capacity, increments held, and writes expiry/outbox atomically.
5. Confirmation creates stable payment/partner references. Depending contract, authorize
   payment then confirm partner, or partner hold then authorize; persist every saga step.
6. Local confirmed inventory moves `held -> confirmed` only after required partner/
   payment evidence. Issue reservation/voucher from committed state.
7. Definitive failure releases hold and voids/refunds. Unknown responses retain bounded
   protection and reconcile. Cancellation/modification execute policy-aware sagas.

## 8. Search and stable pagination

Index property geo point, text, amenities, category, guest capacity, approximate price
bucket, and coarse availability horizon. Search selects candidates by geo/filter,
then ranking combines relevance, quality, price, predicted availability, popularity,
and personalization. The final offer recheck removes stale candidates.

Cursor binds query/filter/date/occupancy, index/model versions, and last `(rank_score,
property_id)`. Over-fetch to replace unavailable properties and advance cursor by
consumed candidates. If the pinned snapshot expires, restart explicitly. Cache property
content long; cache date/rate summaries briefly with observed version/time.

## 9. Quote calculation logic

```text
function createQuote(user, request, key):
    require validLocalDateRange(request, property.timezone)
    dates = eachDate(checkIn inclusive, checkOut exclusive)
    ratePlan = rates.getCurrent(request.ratePlanId)
    require occupancyRulesAllow(ratePlan, request.guests, request.rooms)

    nightly = []
    for date in dates:
        rate = ratePlan.rateFor(date)
        require rate exists and restrictionsAllow(ratePlan, date, request)
        availability = inventory.observe(property, roomType, date)
        require availability.mightFit(request.rooms)
        nightly.add(rate.amountForOccupancy(request.guests))
    taxesFees = taxService.quote(property, user.market, nightly, ratePlan)
    total = exactMinorUnitSum(nightly, taxesFees)
    snapshot = {ratePlan.version, nightly source versions,
                inventory observed versions, cancellation policy/version}
    persist and return idempotent short-lived quote
```

The UI displays every nightly component, mandatory fee, tax treatment, currency, and
cancellation/no-show policy before booking. FX display is indicative unless the quote
explicitly guarantees converted charge amount.

## 10. Core multi-night hold logic

```text
function createHold(actor, quoteId, roomQuantity, key):
    requestHash = hash(quoteId, roomQuantity)
    transaction on property shard:
        prior = idempotency.get(actor.id, "hold", key)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response

        quote = quotes.getForShare(quoteId)
        require quote.userOrSession == actor and quote.expiresAt > now
        require quote.inventoryModel == LOCAL_ALLOCATION
        nights = lockRoomNightsSorted(quote.propertyId, quote.roomTypeId,
                                      quote.stayDates)
        for night in nights:
            sellable = night.baseCapacity - night.safetyStock - night.held
                       - night.confirmed + night.overbookLimit
            require sellable >= roomQuantity

        hold = holds.insert(quote, actor, ACTIVE, now + HOLD_TTL)
        for night in nights:
            night.held += roomQuantity; night.version += 1
            holdNights.insert(hold.id, night.key, roomQuantity)
        expiry.insert(hold.expiresAt, hold.id, hold.version)
        outbox.insert(RoomsHeld(hold.id, nightVersions(nights)))
        save idempotency response
    return hold
```

One serializable transaction gives all-night-or-none semantics. Lock in date/key order
to avoid deadlocks. A broad search/cache result never decrements inventory.

## 11. Hold expiry and confirmation

Expiry worker scans durable time buckets plus overdue-row sweeper. It locks hold and
all its nights; only `ACTIVE` past due releases `held` once. Begin confirmation first
changes hold to `CONFIRMING`, sets a bounded payment/partner deadline, and persists
stable external IDs, so ordinary expiry cannot race it.

```text
function confirmLocalHold(holdId, paymentEvidence, partnerEvidence):
    verify references, amount/currency, signatures, and required partner state
    transaction on property shard:
        dedupe external event IDs
        hold = holds.getForUpdate(holdId)
        require hold.state in [CONFIRMING, CONFIRMATION_UNKNOWN]
        nights = lock hold nights
        require each night has hold quantity accounted
        for night: night.held -= qty; night.confirmed += qty; night.version++
        reservation = reservations.markConfirmed(...)
        hold.state = CONFIRMED
        append outbox voucher/notification event
```

If external success arrives after a forced local release, do not decrement already
sold capacity; attempt safe reaccommodation or void/refund and open an incident.

## 12. Partner inventory models

### Allocated inventory

Partner grants the platform a quantity by room/date. Import versioned allocation and
make local strong decisions. Send confirmed reservation to partner idempotently and
reconcile allocation consumption. This gives fast booking but platform must honor
stop-sell/allocation changes and contract.

### Live/free-sale inventory

No guaranteed local quantity. Quote is indicative and confirmation calls partner with
stable request ID. Persist `PARTNER_CONFIRMING` before call. Only partner confirmation
code creates a confirmed reservation; timeout remains unknown and must be queried.
Capacity/latency/availability now depend on partner.

### Hybrid

Use local allocation until exhausted, then live request. Every offer declares model
and source version so orchestration chooses correct rules. Never treat a cached partner
“available” reply as a reservation.

## 13. Payment ordering and saga

There is no perfect order across payment and partner:

- authorize payment first protects revenue but may require void/refund if partner fails;
- partner hold first protects room but may expire if payment is slow;
- parallel calls lower latency but increase compensation complexity.

A common flow is local/partner hold -> payment authorization -> partner/local confirm
-> capture at confirmation or per policy. Every step has stable idempotency/reference,
durable state, deadline, query, and compensation. Unknown payment/partner status is
reconciled before a new attempt. Never issue voucher from browser return alone.

## 14. Modification and cancellation

A modification is not an in-place mutation of nights/prices. Create a new quote,
atomically hold added/replacement inventory, calculate price/refund difference and
policy, get confirmation, then release old inventory. If it fails, retain original
reservation. Same-property local inventory can swap under one transaction; partner
changes use saga and explicit intermediate status.

Cancellation evaluates immutable booked policy against property-local time, quantities,
no-show/arrival status, and prior refunds. Confirm partner cancellation, decrement
confirmed/return inventory according to resale policy, then void/refund idempotently.
Expose `CANCELLATION_PENDING`/`REFUND_PENDING` until proven.

## 15. Partner synchronization and ordering

Partner messages carry property/room/rate/date, stable event ID, source version or
effective timestamp, and snapshot/delta type. Adapter verifies/authenticates, stages
raw evidence, normalizes identifiers/timezone/currency, then conditionally applies only
newer version. A snapshot replaces a scoped version only after completeness/checksum;
an old delta cannot overwrite it.

Coalesce high-rate updates by newest key/version for search projection, but process
reservation/cancellation events individually. Maintain mapping between internal IDs
and partner codes with versioned configuration and quarantine unmapped/invalid data.

## 16. Reconciliation and overbooking response

Compare per property/room/date:

```text
base/allocation - held - confirmed versus partner/PMS availability
internal reservation/reference/status versus partner reservation
payment authorization/capture/refund versus reservation state
```

Also verify holds sum to counters and confirmed reservations sum to booked inventory.
Drift creates case with guests/dates/value/SLA. Stop-sell or safety stock can contain
risk. Resolution may release orphan holds, import missing reservation, refund, or
reaccommodate under contractual priority; manual inventory corrections are audited.

## 17. Time, timezone, and policy correctness

Store stay dates as property-local dates and property IANA zone/version; store event
instants in UTC. Check-in/out cutoff and cancellation deadline resolve local DST gaps/
folds under explicit property policy. Do not compute nights as `UTC hours / 24`.
Retain the exact cancellation/tax/rate policy snapshot used at purchase even after
the current plan changes.

## 18. Sharding and degradation

Assign each property to a strongly consistent home cell and colocate future room-night
rows/holds/reservations. Date-partition cold history and logical shards while keeping
normal stay transactions local. Read/search replicates globally. Consensus/fencing
prevents two property writers during failover.

Under pressure, preserve booking/expiry/callbacks, slow partner bulk feeds, serve
stale-labeled search, reduce candidate rechecks, and disable optional ranking features.
One failing partner has isolated queues/circuits and cannot exhaust owned inventory.

## 19. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Two users request last room | Locked all-night check commits one valid hold |
| Hold expiry races checkout | Locked hold state makes one transition win |
| Expiry worker dies | Bucket replay and overdue sweep release idempotently |
| Payment/partner call times out | Mark UNKNOWN; query same stable reference |
| Partner sends old/duplicate update | Inbox ID and source version prevent regression |
| Search/index is stale | Quote/hold revalidates authoritative inventory/rate |
| Confirmed partner booking but payment failed | Void/cancel/release or reconcile per saga |
| Property cell partitions | Fence old leader and reject unsafe inventory writes |
| Source snapshot is partial | Keep prior version; quarantine incomplete import |

## 20. Security and privacy

Authorize traveler/property/partner/support/finance roles and field-mask guest data.
Encrypt PII and tokenize payment methods; sign partner/payment callbacks, use mTLS,
nonce/timestamp replay protection, strict URL/file/parser controls, tamper-evident audit,
and dual approval for inventory/refund overrides. Prevent IDOR, account takeover, bot
holds, fake availability/rates, amount/currency/date tampering, coupon/refund abuse,
partner credential compromise, CSV injection, scraping, and insider guest lookup.

Apply payment/travel/tax/accessibility laws, privacy consent/minimization/retention/
deletion, residency, legal hold, sanctions, fraud, guest safety, incident response,
and tested backup/key recovery across primary, partner raw data, indexes, logs, and archives.

## 21. Observability

Track search/offer/quote/hold/confirm/cancel latency and errors, candidate-to-valid-offer
rate, cache/index/source age, room-night lock contention, holds and expiry lag, inventory
conservation/drift, quote price/restriction changes, payment/partner success/timeout/
unknown age, booking conversion, cancellation/refund, adapter queue/source-version
lag, source quarantine, property-cell leader changes, overbooking/reaccommodation, and
reconciliation case count/value/age.

Property tests generate overlapping date holds, checkout/expiry races, modifications,
duplicate/reordered partner/payment events, and assert room-night conservation. Test
DST/local-date boundaries and price rounding. Load-test one hot property/date. Chaos
tests kill expiry/adapters/payment/cells at every boundary; reconciliation recomputes
counters from holds/reservations and compares partner/PMS truth.

## 22. Implementation path

1. **MVP:** owned properties, content/search, rate quote, property-local room-night
   counters, atomic multi-night hold/expiry, one payment flow, confirmation/voucher.
2. **Reliability:** durable saga/timers, UNKNOWN reconciliation, outbox/inbox, versioned
   availability/search, cancellation/refund, projections, and inventory controls.
3. **Partner scale:** isolated adapters, allocated/live/hybrid models, source versions/
   snapshots, bulk coalescing, modifications, PMS reconciliation, and overbooking cases.
4. **Hardening:** cell/fenced failover, bot/fraud/security/privacy/legal controls,
   property/DST/property-state/load/chaos tests, restores, runbooks, and SLOs.

## 23. Final design

Treat each property/room-type/local-date row as conserved inventory owned by one
strongly consistent property cell. Search and offer caches narrow discovery but never
authorize sale. A versioned quote snapshots rate and policy; an all-night transaction
holds every date or none. Durable payment/partner orchestration converts that hold only
from verified evidence, preserves unknown states, and compensates failures. Explicit
allocated versus live partner models, source-version ordering, and continuous PMS/
payment reconciliation prevent stale availability from silently becoming overbooking.
