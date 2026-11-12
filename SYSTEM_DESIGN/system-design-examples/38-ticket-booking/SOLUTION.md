# Complete Solution: Ticket Booking

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Users discover events, view a seat map, enter fair high-demand onsales, hold exact
seats or general-admission quantity, pay, receive verifiable tickets, transfer/resell
where allowed, cancel/refund under policy, and enter the venue once. Organizers manage
inventory, pricing tiers, holds, sale windows, and reports.

Targets: browse p99 below 200 ms, hold decision p99 below 500 ms for admitted users,
99.99% reads, 99.95% booking commands, and zero double-sold seats or duplicate entry.
Availability views may lag and must be labeled; the hold transaction is authoritative.
A payment timeout is unknown, not failure, and stays linked to the same hold/reference.

## 2. Capacity estimation

Assume 100,000 seats for a major event, five million interested users in ten minutes,
four seats/hold maximum, ten-minute holds, 10,000 sustainable hold commands/s per
event cell, and 10x availability reads/command.

- Arrival can exceed 8,000 users/s for one event and far more through retries/bots;
  a virtual waiting room admits only measured downstream capacity.
- Seat-map reads can reach hundreds of thousands/s but use CDN/cached immutable layout
  plus compact availability deltas.
- One event's seat state is only tens of MB, so correctness bottleneck is contention,
  not storage.
- Millions of events/tickets need partitioned metadata/history, but a hot event must
  be isolated from other events.
- Holds at 10,000/s for ten minutes could reach six million attempts, so admission,
  quotas, and aggressive terminal-state cleanup are required.

## 3. APIs

```text
GET  /v1/events?query=&city=&from=&cursor=
GET  /v1/events/{eventId}/seat-map
GET  /v1/events/{eventId}/availability?sinceVersion=
POST /v1/events/{eventId}/admission-tokens
POST /v1/holds                         {eventId, seatIds|quantity} Idempotency-Key
GET  /v1/holds/{holdId}
POST /v1/holds/{holdId}/checkout       Idempotency-Key
POST /v1/bookings/{bookingId}/cancel   Idempotency-Key
POST /v1/tickets/{ticketId}/transfer   Idempotency-Key
POST /v1/tickets/{ticketId}/scan       {gateId, nonce} Idempotency-Key
```

Mutation requests require a signed admission token bound to event/user/session/
device, issue time, queue generation, and expiry. Bound seats/booking, request rate,
hold lifetime, attempts/user/payment method, resale price, page size, and scan retries.

## 4. Seat and booking state model

```text
Seat(event_id, seat_id, section, row, number, tier_id, state,
     hold_id, booking_id, version)
Hold(id, event_id, user_id, state, expires_at, payment_deadline,
     price_quote_id, amount, currency, version, created_at)
HoldSeat(hold_id, event_id, seat_id, price_component)
GAInventory(event_id, tier_id, capacity, held, sold, safety_stock, version)
Booking(id, event_id, hold_id, user_id, state, payment_intent_id,
        amount, currency, version, confirmed_at)
Ticket(id, booking_id, seat_id_or_tier, owner_id, state,
       credential_generation, transfer_version)
Scan(ticket_id, venue_id, gate_id, scan_id, result, credential_generation, scanned_at)
PriceQuote(id, event_id, tier_versions, fees, taxes, total, expires_at)
Inbox(source, external_event_id, payload_hash, processed_at)
Outbox(id, aggregate_id, sequence, event_type, payload, published_at)
```

```text
Seat:    AVAILABLE -> HELD -> SOLD
                     \-> AVAILABLE (release/expiry)
Hold:    ACTIVE -> PAYMENT_PENDING -> CONFIRMED
          \-> EXPIRED/RELEASED; PAYMENT_PENDING -> PAYMENT_UNKNOWN/FAILED
Booking: PENDING -> CONFIRMED -> PARTIALLY_REFUNDED/REFUNDED/CANCELLED
Ticket:  ACTIVE -> TRANSFER_PENDING -> ACTIVE(new owner/generation)
          \-> USED/VOID/REFUNDED
```

Invariant: an exact seat has at most one current hold/booking; GA
`held + sold + safety_stock <= capacity`; tickets issue only from a confirmed booking.

## 5. Architecture

```text
client -> CDN/search/event metadata
       -> virtual waiting room -> admission token
       -> availability API -> cached seat bitmap/delta stream
       -> booking command router -> event inventory cell (strong DB/log)
                                      |       |       |
                                    holds   expiry   outbox
                                      |
                               checkout orchestrator -> payment gateway
                                      |
                              booking/ticket issuer -> signed credential

venue gates -> offline-capable scanner sync -> ticket admission service
payment/provider reports <-> reconciliation
```

Partition inventory by event, optionally section only when seats never move atomically
across sections or a coordinator handles it. Colocate a normal booking's selected seats
so one serializable transaction can hold all-or-none.

## 6. Step-by-step workflow

1. Waiting room rate-limits identity/device/network, assigns a fair position, and
   issues a short-lived one-use admission token when event cell has capacity.
2. Client downloads immutable venue layout and current versioned availability bitmap;
   selection is optimistic because another user may hold it before submission.
3. Hold command validates admission/idempotency/limits/quote, locks selected seat rows
   in sorted order, proves all AVAILABLE, marks all HELD, inserts hold/expiry/outbox,
   and commits atomically.
4. Checkout atomically changes active hold to `PAYMENT_PENDING` with bounded grace and
   creates stable payment intent/reference before calling payment gateway.
5. Verified authorization/capture result converts exactly those held seats to SOLD
   and booking CONFIRMED in one inventory transaction; ticket issuance consumes event.
6. Timeout leaves `PAYMENT_UNKNOWN` and seats protected until status query/reconciliation.
   Definitive failure/expiry releases once. Late proven success after forced release
   cannot recreate sold seats; it triggers automatic refund/manual resolution.
7. Ticket credential is signed/versioned. Venue scan atomically accepts first valid
   use and rejects repeats; offline gates reconcile conflicts under venue policy.

## 7. Core exact-seat hold algorithm

```text
function createHold(actor, command, key):
    require 1 <= command.seatIds.size <= MAX_SEATS
    require allUnique(command.seatIds)
    verifyAdmissionToken(command.token, actor, command.eventId)
    requestHash = canonicalHash(command.eventId, sort(command.seatIds), command.quoteId)

    transaction SERIALIZABLE on event cell:
        prior = idempotency.get(actor.id, "hold", key)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response
        consumeAdmissionNonceOnce(command.token.nonce)
        event = events.getForShare(command.eventId)
        require event.saleOpen and buyerLimitsAllow(actor, event)
        quote = quotes.requireValidForSeats(command.quoteId, command.seatIds, now)
        seats = lockSeatsSorted(event.id, command.seatIds)
        require every seat.state == AVAILABLE

        hold = holds.insert(event.id, actor.id, ACTIVE,
                            expiresAt=now + HOLD_TTL, quote.total)
        for seat in seats:
            seat.state = HELD; seat.holdId = hold.id; seat.version += 1
            holdSeats.insert(hold.id, seat.id, quote.component(seat))
        expiry.insert(hold.expiresAt, hold.id, hold.version)
        outbox.insert(SeatsHeld(event.id, hold.id, seatVersions(seats)))
        result = publicHold(hold, seats)
        idempotency.insert(actor.id, key, requestHash, result)
    return result
```

Either every selected seat changes or none do. Lock order prevents deadlocks. Unique/
check constraints on current seat ownership are defense in depth. Returning “seat no
longer available” is normal, not a consistency failure.

## 8. General-admission hold algorithm

```text
function holdGA(eventId, tierId, quantity, holdId):
    transaction:
        stock = gaInventory.getForUpdate(eventId, tierId)
        available = stock.capacity - stock.safetyStock - stock.held - stock.sold
        require available >= quantity
        stock.held += quantity
        stock.version += 1
        insert hold/line/adjustment/expiry/outbox atomically
```

Commit moves quantity `held -> sold`; release moves `held -> available`. An idempotent
line-state transition changes counters once. Never scale GA by independent salted
counters unless capacity rights were atomically preallocated to each bucket (escrow).

## 9. Expiry and release correctness

Use coarse durable time buckets plus authoritative `expires_at`. Workers lease due
entries and run a conditional transition; a database sweeper finds overdue ACTIVE
holds missed by queue processing.

```text
function expireHold(holdId, scheduledVersion):
    transaction on event cell:
        hold = holds.getForUpdate(holdId)
        if hold.state != ACTIVE or hold.expiresAt > now: return NOOP
        seats = lockSeatsSorted(hold.eventId, holdSeatIds(holdId))
        require each HELD seat still references hold.id
        for seat in seats: seat -> AVAILABLE, clear holdId, version++
        hold.state = EXPIRED; hold.version += 1
        append outbox event
```

Checkout first locks hold and moves it from ACTIVE to `PAYMENT_PENDING`, so expiry
cannot release it concurrently. Payment grace is bounded and separately swept.

## 10. Payment and confirmation logic

```text
function beginCheckout(actor, holdId, key):
    transaction:
        return prior if key exists
        hold = holds.getForUpdate(holdId)
        require hold.userId == actor.id and hold.state == ACTIVE
        require hold.expiresAt > now and quoteStillValid(hold.priceQuoteId)
        paymentIntentId = stableId("ticket-payment", hold.id, hold.version)
        hold.state = PAYMENT_PENDING
        hold.paymentDeadline = now + MAX_PAYMENT_GRACE
        booking = bookings.insert(hold, PENDING, paymentIntentId)
        append outbox/idempotency
    paymentGateway.confirm(paymentIntentId, hold.amount, hold.currency,
                           idempotency=paymentIntentId)

function confirmFromPayment(event):
    verify gateway event and amount/currency/reference
    transaction on event cell:
        dedupe event ID/hash
        booking = bookings.getForUpdateByPayment(event.intentId)
        hold = holds.getForUpdate(booking.holdId)
        if event is proven success and hold.state in [PAYMENT_PENDING, PAYMENT_UNKNOWN]:
            require now within resolvable grace and all seats still reference hold
            mark seats SOLD with booking.id
            hold.state = CONFIRMED; booking.state = CONFIRMED
            append outbox TicketIssuanceRequested
        else if success but seats already released:
            mark booking PAYMENT_SUCCEEDED_NO_INVENTORY and request refund
```

Do not issue tickets merely because the browser returns from payment. Use signed
gateway callback/status. Capture timing may be authorize-then-capture on confirmation;
all retries use stable references.

## 11. Payment ambiguity and compensation

If provider times out, keep the hold in `PAYMENT_UNKNOWN`, query the same intent, and
accept verified callbacks. Do not route a new charge. After maximum grace, policy may
release inventory but must continue reconciling. A later success receives immediate
idempotent void/refund and prominent customer handling, not a ticket for a seat sold
to somebody else.

Reconciler compares booking/hold, payment intent/ledger, seat states, and issued
tickets. It repairs missing ticket events, refunds success-without-inventory, and
flags sold-without-payment. Manual seat/money corrections require audit and approval.

## 12. Availability read model

Immutable seat layout contains labels/geometry/tier/accessibility, cached long at CDN.
Dynamic state is a compressed bitmap/version per section plus small deltas from
outbox. Clients subscribe/poll by version and reconcile gaps with a snapshot. The API
may group `AVAILABLE/LOW/SOLD_OUT` rather than expose exact bot-friendly counts.

The read model can show a seat as available after someone holds it; the authoritative
transaction rejects the loser. Never use Redis bitmap alone as inventory truth unless
it provides durable replicated transactional semantics and recoverable audit.

## 13. Flash-sale waiting room and fairness

- Admit at a rate driven by event-cell hold latency, lock contention, payment backlog,
  and inventory, not raw arrivals.
- Assign queue positions with a server-side random/fair ordering window before sale;
  do not reward millisecond network advantage unless product policy says so.
- Admission token is signed, user/device/event-bound, short-lived, nonce-protected,
  and permits a bounded number of hold attempts.
- Enforce account/household/payment-method ticket limits, CAPTCHA/risk/device/IP bot
  signals, proxy farms and headless automation defenses with accessible alternatives.
- Cache browse/layout and shed viewer counts/live decoration before inventory commands.
- Isolate each hot event/cell so one onsale cannot exhaust all bookings.

## 14. Ticket issuance and venue scanning

A ticket carries a random ID/reference and server-signed short credential bound to
ticket, event, entitlement section/seat, generation, and expiry—not raw personal data.
Use rotating QR/challenge when screenshots are a risk. Transfer/resale atomically
changes owner and increments credential generation, invalidating old credentials.

```text
function scan(ticketId, credential, scanId, gate):
    verify signature, event, generation, time window, gate policy
    transaction:
        return prior result for scanId
        ticket = tickets.getForUpdate(ticketId)
        require ticket.state == ACTIVE
        require credential.generation == ticket.credentialGeneration
        ticket.state = USED
        scans.insert(ticket, gate, scanId, ACCEPTED)
        append audit/outbox
    return ACCEPTED
```

Online scanning provides global first-use correctness. Offline scanners receive a
signed event allowlist/revocation delta and allocate gate/device partitions or accept
explicit duplicate-entry risk; sync resolves conflicts and security staff handle them.

## 15. Cancellation, refund, transfer, and resale

Cancellation validates event/ticket/refund policy and booking state. Lock booking/
tickets/seats, mark tickets VOID/refund pending, and only return a reserved seat to
AVAILABLE under organizer resale policy. Refund is a separate idempotent payment
workflow; display `REFUND_PENDING` until proven.

Transfer requires recipient acceptance/eligibility, atomically replaces owner and
generation, and audits both parties. Controlled resale holds the ticket while listing,
enforces price/fee/identity/legal rules, and atomically transfers on payment; old QR
generation becomes invalid. Never duplicate a ticket record to transfer it.

## 16. Sharding and regional resilience

Assign an event to a home cell/region whose strongly consistent database owns seats,
holds, bookings, and ticket issuance. Read models replicate globally. Large venues can
partition by section only if a multi-section request is prohibited/coordinated; one
event-level metadata version controls sale state/prices.

Consensus/fencing ensures one writer leader. During partition, keep browse/queue
available but reject holds if seat ownership is uncertain. Promote a fully caught-up
replica, rebuild availability from seat rows/outbox, and preserve admission tokens by
queue generation.

## 17. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client retries hold/checkout | Same key/hash returns same resource/effect |
| Two users select same seat | Row locks/CAS commit one all-or-none hold |
| Expiry races checkout | Locked hold state lets one transition win |
| Expiry worker dies | Bucket replay plus overdue sweep releases once |
| Payment timeout | Keep bounded hold/UNKNOWN; query stable intent |
| Payment succeeds after forced release | Never resell same seat to payer; void/refund and reconcile |
| Ticket issuer event duplicates | Unique booking/seat ticket key issues once |
| Availability cache fails/stales | Strong hold path remains authoritative |
| Event-cell region partitions | Fence old leader and reject unsafe seat writes |

## 18. Security and compliance

Protect user/organizer/admin/gate roles, admission and ticket signing keys in HSM/KMS,
payment tokens, PII and accessibility information. Prevent IDOR, token/QR forgery,
replay, credential sharing, bots, queue bypass, account/payment limit evasion, insider
seat allocation, price tampering, resale fraud, scanner compromise, XSS and enumeration.
Use mTLS, field encryption, signed callbacks, nonce/timestamp windows, tamper-evident
audit and dual control for inventory overrides.

Apply ticketing/resale/tax/accessibility laws, payment rules, privacy consent/retention/
deletion where permitted, legal hold, residency, chargeback/refund evidence, organizer
settlement, and tested backup/key recovery.

## 19. Observability

Track queue arrivals/admission/wait/fairness/abandonment, hold latency/success/conflict,
lock contention, available/held/sold conservation, active/expired/payment-unknown hold
age, expiry lag, quote failures, payment conversion/ambiguity/refund, booking-to-ticket
lag, availability version lag/gaps, ticket transfers/resale, scan accept/duplicate/
offline conflict, bot/rate-limit signals, event-cell saturation/leader changes, and
reconciliation mismatch count/value.

Property/model tests generate concurrent holds, checkout/expiry races, duplicate and
late payment events, ticket transfer/scan races, and prove seat/GA invariants. Load-test
one hot event with realistic bots/retries, not uniform events. Chaos tests kill expiry,
payment, issuer, cache, and leaders at commit boundaries. Recompute seats and bookings/
tickets/payment control totals continuously.

## 20. Implementation path

1. **MVP:** one-event-cell reserved seating, transactional holds/TTL, idempotent checkout,
   one payment gateway, confirmed booking, signed static ticket, online scan.
2. **Reliability:** durable expiry/sweep, UNKNOWN reconciliation/refunds, outbox/inbox,
   versioned availability, payment/ticket controls, cancellation, and transfers.
3. **Scale:** virtual waiting room, anti-bot/fair admission, event isolation, GA counters,
   rotating QR, offline gate policy, resale, organizer reporting/settlement.
4. **Hardening:** fenced failover, security/legal/privacy lifecycle, state/property/
   flash-load/chaos tests, control totals, restore/key drills, runbooks, and SLOs.

## 21. Final design

Make each event inventory cell the single strongly consistent owner of its seat or GA
state. An admitted, idempotent command atomically holds all requested seats with a
durable expiry. Checkout changes the hold state before payment; only verified payment
evidence converts the same inventory to a booking, and unknown outcomes remain bounded
and reconciled. Signed generation-based tickets derive only from confirmed bookings,
and first-use scan is atomic. Cached availability and global queues absorb reads and
flash demand without participating in the no-double-sale invariant.
