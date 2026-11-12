# Complete Solution: Ride-Hailing Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Drivers go online and stream location/availability. Riders request an eligible vehicle,
receive price/ETA, match to one driver, track arrival/trip, communicate safely, cancel,
pay, rate, and use safety support. Drivers receive fair expiring offers, navigate,
start/end trips, and earn payouts.

Targets: quote p99 below 500 ms, first dispatch offer below two seconds, median match
below five seconds in healthy supply, live location age below five seconds, and 99.99%
trip/status reads with 99.95% state commands. Latest location/index is approximate and
eventual. Ride and driver assignment/state are strongly consistent: one driver cannot
hold two active rides and one ride cannot have two assigned drivers.

## 2. Capacity estimation

Assume 10 million simultaneously online drivers updating every four seconds, 20
million active riders, 10 million trips/day, ten rider location views/trip/minute,
and 5x commute peaks.

- Driver ingest averages 2.5 million location updates/s before rider/trip telemetry.
- At 100 bytes/update, raw traffic is 250 MB/s; keep latest in memory and sample/
  compress durable history according to safety/privacy policy.
- Trip requests average 116/s globally but peak by city/zone and event; design city
  cells for thousands/s.
- WebSocket fan-out is bounded mostly one driver to one rider, unlike broadcast media.
- One latest driver record at 200 bytes is about 2 GB for ten million drivers before
  indexes/replicas; the high cost is churn and cell movement.

## 3. APIs and streams

```text
POST /v1/drivers/me/availability          {state, vehicleId} Idempotency-Key
POST /v1/driver-locations                 {sessionId, sequence, lat, lng, ...}
POST /v1/ride-quotes                      {pickup, destination, product} Idempotency-Key
POST /v1/rides                            {quoteId, pickup, destination} Idempotency-Key
GET  /v1/rides/{id}
POST /v1/offers/{id}/accept               Idempotency-Key
POST /v1/rides/{id}/arrive|start|complete Idempotency-Key, If-Match
POST /v1/rides/{id}/cancel                Idempotency-Key
GET  /v1/rides/{id}/location-stream-token
POST /v1/rides/{id}/safety-events         Idempotency-Key
```

Location batches use device session plus monotonically increasing sequence, server
receive time, device event time, accuracy, speed, heading, and integrity signals.
Bound coordinate ranges, accuracy/age, batch size, rate, quote lifetime, and command
transitions. Never trust client-calculated fare/distance/state.

## 4. Data model and state machines

```text
Driver(id, account_state, availability_state, active_ride_id,
       vehicle_id, city_id, state_version)
DriverSession(id, driver_id, device_id, started_at, last_sequence, state)
DriverLocation(driver_id, session_id, sequence, point, road_segment,
               cell_id, accuracy, event_time, receive_time, integrity_state)
Ride(id, rider_id, driver_id, product, state, dispatch_epoch, version,
     pickup, destination, quote_id, created_at, matched_at, started_at, ended_at)
Offer(id, ride_id, dispatch_epoch, driver_id, state, expires_at, version)
Quote(id, rider_id, product, route_version, distance, duration,
      fare_breakdown, currency, pricing_version, expires_at)
TripEvent(ride_id, sequence, type, actor, payload, created_at)
PaymentRef(ride_id, payment_intent_id, amount, state, version)
Outbox(id, aggregate_id, sequence, event_type, payload, published_at)
```

```text
Driver: OFFLINE -> AVAILABLE -> OFFERED -> ASSIGNED -> ON_TRIP -> AVAILABLE/OFFLINE
Ride: REQUESTED -> DISPATCHING -> ASSIGNED -> DRIVER_ARRIVING -> DRIVER_WAITING
      -> IN_PROGRESS -> COMPLETED
      any allowed pre-completion -> CANCELLED; dispatch -> NO_DRIVER
Offer: PENDING -> ACCEPTED | DECLINED | EXPIRED | REVOKED
```

Assignment changes driver, ride, and accepted offer in one transaction/cell or one
serialized compare-and-set command with unique active-ride constraint.

## 5. Architecture

```text
driver app -> regional location gateway -> durable stream -> latest-location store
                                                       -> H3/S2 in-memory cell indexes
                                                       -> sampled history/safety

rider -> quote API -> routing/ETA + pricing
rider -> ride API/state DB/outbox -> zone dispatch orchestrator
                                      |        |
                                  matcher   offer gateways -> driver
                                      |
                                 assignment transaction

trip events -> tracking/notifications -> fare/payment/ledger -> driver payout
safety/support/fraud services consume controlled trip/location evidence
```

Partition operational matching by city and geographic zone; keep the ride/driver
assignment control in a city cell. Border queries read adjacent zones. Indexes are
rebuildable from latest location/availability and stream, never the financial source.

## 6. Step-by-step workflow

1. Driver authenticates vehicle/eligibility and goes AVAILABLE. Location gateway
   validates/deduplicates session sequences and updates stream/latest geospatial cell.
2. Rider requests quote. Routing snaps pickup/destination to road graph and returns
   distance/time; pricing snapshots base/time/distance/demand/tolls/taxes/fees and expiry.
3. Ride create validates quote/rider/payment readiness/pickup and commits `DISPATCHING`
   plus outbox under idempotency.
4. Matcher expands nearby cells, removes stale/ineligible/busy drivers, computes road
   pickup ETA and score, then sends a bounded wave of expiring offers tagged with ride
   `dispatch_epoch`.
5. First valid acceptance atomically changes ride to ASSIGNED and driver to ASSIGNED;
   all other offers are revoked. Losers receiving delayed acceptance get a clear rejection.
6. Driver arrives, starts after rider/PIN/geofence policy, and streams route. Versioned
   trip commands progress state; server computes fare from trusted route/time/evidence.
7. Completion commits trip/fare, charges idempotent payment, posts ledger/payout, and
   sends receipt. Unknown payment reconciles without reopening trip.

## 7. Location ingest and index logic

```text
function ingestLocation(driver, update):
    require authenticatedSession(driver, update.sessionId)
    require validPointAccuracyTime(update)
    session = sessionCache.get(update.sessionId)
    if update.sequence <= session.lastSequence: return DUPLICATE_OR_OLD
    if impossibleJump(session.lastPoint, update): flagOrRejectByPolicy()

    matched = mapMatcher.snap(update.point, update.heading, update.accuracy)
    cell = spatial.cell(matched.point, resolutionForCity(driver.cityId))
    event = LocationEvent(driver.id, update.sessionId, update.sequence,
                          matched, cell, serverReceiveTime)
    locationStream.append(key=driver.id, event)

consumer atomically/conditionally:
    if event.session is current and event.sequence > latest.sequence:
        remove driver from old cell index if cell changed
        latest.put(event)
        if driver state == AVAILABLE: add/update driver in new cell index
```

Stream partition by driver preserves order; conditional session/sequence protects
against delayed old devices. Index entry expires after a short heartbeat TTL. Persist
sampled/triggered history, not every point forever.

## 8. Candidate search and ranking

```text
function candidates(request, budget):
    pickupCell = spatial.cell(request.pickup)
    raw = []
    for ring in expandingRings(pickupCell, MAX_RADIUS):
        raw += index.availableDrivers(ring, request.product)
        raw = raw.filter(d => latestAge(d) < MAX_LOCATION_AGE)
                 .filter(d => driverSnapshotEligible(d, request))
        if raw.size >= MIN_CANDIDATES or budget.nearDeadline(): break

    approximate = raw.sortBy(straightLineOrCachedEta).take(ROUTE_ETA_LIMIT)
    etas = routing.batchPickupEta(approximate, request.pickup, trafficVersion)
    return score(approximate, etas,
        pickupEta, acceptanceProbability, idleTimeFairness,
        destinationCompatibilityIfAllowed, driverConstraints,
        cancellationRisk).take(OFFER_POOL)
```

Do not select solely by Euclidean distance; rivers/roads/direction matter. Apply fair
idle-time/earnings constraints and prevent protected-attribute discrimination. If
routing times out, use calibrated approximate ETA and label/fallback.

## 9. Offer waves and dispatch epochs

Send one or a small batch of offers based on supply/latency policy. Large simultaneous
broadcasts increase driver distraction and acceptance races. Each dispatch attempt
increments ride epoch; offers contain epoch/expiry and one driver can have bounded
outstanding offers.

```text
function dispatch(rideId):
    ride = rides.lockAndAdvanceEpochIfStillDispatching(rideId)
    candidates = matcher.find(ride)
    for wave in partitionWaves(candidates):
        create offer rows transactionally for ride.epoch with short expiry
        push offers
        wait until accepted or wave deadline
        if assigned: revoke remaining and return
    mark NO_DRIVER or schedule expanded retry under total deadline
```

An offer push is advisory; driver acceptance endpoint checks authoritative rows.
Expired/revoked offers cannot assign even if the notification arrives late.

## 10. Atomic offer acceptance

```text
function acceptOffer(driverActor, offerId, key):
    transaction in city cell:
        prior = idempotency.get(driverActor.id, "accept", key)
        if prior exists: return prior
        offer = offers.getForUpdate(offerId)
        ride = rides.getForUpdate(offer.rideId)
        driver = drivers.getForUpdate(driverActor.id)

        require offer.driverId == driver.id
        require offer.state == PENDING and offer.expiresAt > now
        require ride.state == DISPATCHING
        require offer.dispatchEpoch == ride.dispatchEpoch
        require driver.availabilityState in [AVAILABLE, OFFERED]
        require driver.activeRideId == null and driverStillEligible(driver)

        offer.state = ACCEPTED
        ride.state = ASSIGNED; ride.driverId = driver.id; ride.version += 1
        driver.availabilityState = ASSIGNED
        driver.activeRideId = ride.id; driver.stateVersion += 1
        offers.revokeOtherPending(ride.id, ride.dispatchEpoch)
        append ride/driver outbox events and idempotency response
    return assignment
```

Unique active assignment plus locks/CAS make simultaneous ride/driver acceptances
choose one outcome. Timeout after commit is safe because the same key returns assignment.

## 11. Trip transition logic

Every trip command has actor, GPS/evidence, expected ride version, server time, and
idempotency key. State rules specify who can act and preconditions:

```text
ARRIVE: driver assigned, near pickup or audited override
START:  driver waiting, rider PIN/confirmation if enabled, start geofence
COMPLETE: in progress, plausible endpoint/duration, fare inputs finalized
CANCEL: role/state-specific policy, fee decision recorded separately
```

Transaction conditionally moves state, increments trip event sequence, and writes
outbox. Device offline commands carry occurrence time/evidence but server validates
against current state; they cannot rewrite a trip already completed/cancelled.

## 12. Quote, surge, and fare calculation

Quote stores route distance/duration/version, base/time/distance rates, demand multiplier,
minimum, booking fee, toll/tax estimate, currency, product and expiry. Surge uses
privacy-safe supply/demand aggregates over zones with smoothing, caps, hysteresis, and
regulatory/product rules; disclose before request.

Final fare uses trusted trip start/end, map-matched distance/time, waits/stops/tolls,
quote guarantee policy, and anomaly review. Integer minor-unit rounding is deterministic.
A material destination/route/product change creates a new fare basis/consent where
required; clients never submit final payable amount.

## 13. Cancellation and reassignment

Before acceptance, rider cancel increments dispatch epoch and revokes offers. After
assignment, cancellation locks ride/driver, applies reason/time/arrival policy, frees
driver exactly once, and creates any cancellation-fee payment separately. Driver
cancel can redispatch with new epoch if rider still wants ride.

If driver disconnects, do not instantly reassign an active trip. During dispatch/
prepickup, use heartbeat grace, contact attempts, and policy; atomically detach old
driver and advance epoch before redispatch. Once trip starts, safety/support workflow
handles connectivity rather than assigning another driver.

## 14. Tracking and communication

Only assigned rider/driver and authorized safety/support receive a scoped, short-lived
stream token. Gateway sends latest map-matched position with sequence/time/accuracy;
coalesce intermediate updates and let clients fetch snapshot on gap. Location loss
shows stale status and last update, not false movement.

Use masked calling/in-app messaging tied to ride and short retention. Filter abuse,
rate-limit, and preserve safety evidence under strict access policy. Communications/
tracking failure never changes authoritative trip state.

## 15. Payment and driver payout

Prevalidate/tokenize rider method and optionally authorize estimate. On completion,
create stable payment intent for final fare; timeout remains unknown and reconciles.
Ledger posts rider receivable/cash, driver payable, platform revenue, tax/tolls, tips,
adjustments/refunds as balanced entries. Driver payout batches only settled eligible
payables and reconciles provider/bank evidence.

Trip completion can succeed while payment is pending; collections/fraud workflow may
restrict future rides. Never repeat charge under a new reference merely because the
first call timed out.

## 16. City/zone scaling and resilience

Cellize by city/metro: independent location topics, indexes, ride database, matchers,
and capacity limits. H3/S2 zone ownership includes overlap/neighbor queries at borders.
When a driver crosses zone, location index changes freely; active ride remains owned
by its city cell until terminal. Rebalance zone/index workers with stream offsets and
epochs; latest records rebuild state after failure.

One fenced leader/transaction domain owns ride-driver assignment. During cell database
partition, keep map/tracking degraded but reject ambiguous assignment/state transitions.
Route new demand away or show unavailable rather than double-assign drivers.

## 17. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Location update duplicates/reorders | Current session/sequence applies newest once |
| Location index worker dies | Rebuild latest cell memberships from stream/store |
| Offer notification is lost | Offer expires; next wave proceeds |
| Two offers accepted | Ride/driver locks and epoch let one assignment commit |
| Client retries state command | Idempotency returns same version/result |
| Matcher/routing fails | Approximate/fallback matching or explicit no-service |
| Driver disconnects prepickup | Grace then atomic detach/new dispatch epoch |
| Payment times out | Trip stays complete; payment UNKNOWN reconciles stable intent |
| City cell partitions | Fence writers and reject unsafe assignment transitions |

## 18. Safety, security, and privacy

Verify driver identity/license/vehicle/background status and rider account/device;
apply step-up, SOS, route-deviation/crash/long-stop signals, trip sharing, audio/privacy
policy, incident response, and trained support escalation. Emergency functions have
high availability and audited break-glass access.

Use service mTLS, role/ride-scoped authorization, encrypted PII/location, rotating
masked contacts, signed commands, anti-replay, device integrity, rate limits, and
tamper-evident audit. Prevent fake GPS, account takeover, collusion, promotion/payment
fraud, IDOR, stalking, unauthorized employee lookup, destination discrimination, and
driver/rider harassment. Minimize precise location retention, separate analytics,
honor consent/deletion/legal hold/residency and transport/accessibility/worker/payment laws.

## 19. Observability

Track location ingest/age/accuracy/drop/reorder/impossible jumps, online drivers per
cell, index divergence, quote/routing/pricing latency, requests-to-first-offer/match,
candidate/ring/ETA distributions, offer delivery/accept/expiry, assignment conflicts,
driver utilization/idle fairness, pickup ETA/error/cancellations, trip state age/
invalid transitions, tracking lag, fare estimate error, payment/payout unknowns,
safety alerts, cell saturation/leader changes, and reconciliation mismatches.

Simulation/property tests generate moving drivers, border zones, duplicate/reordered
locations, simultaneous accept/cancel, and state races. Compare matcher choices to
routing truth and measure cohort fairness. Load-test commute/event hotspots. Chaos
tests kill indexes/matchers/gateways/ride leaders/payment; reconciliation verifies no
driver/ride has multiple active assignments and trips map to ledger/payment evidence.

## 20. Implementation path

1. **MVP:** one city, driver availability/latest location, basic cell index, quote,
   serial ride/driver assignment, trip states, one payment path, and tracking.
2. **Reliable dispatch:** stream-rebuilt indexes, expanding-cell/routing ETA ranking,
   offer epochs/waves, outbox, expiry/reassignment, idempotent commands, reconciliation.
3. **Marketplace scale:** city cells, dynamic pricing, fair matching, regional gateways,
   incentives, pooled/product variants, driver payout, and sophisticated risk/safety.
4. **Hardening:** fenced failover, privacy/transport/payment controls, simulation/
   property/hotspot/chaos tests, restores, emergency drills, runbooks, and SLOs.

## 21. Final design

Keep high-rate driver location in a sequence-guarded stream and rebuildable in-memory
geospatial index, while a strongly consistent city cell owns ride/driver state. Matchers
expand nearby cells, calculate road ETA, rank fairly, and send bounded expiring offer
waves. The first valid acceptance atomically claims both ride and driver under dispatch
epoch, making delayed/duplicate accepts harmless. Versioned trip transitions, trusted
fare calculation, idempotent payment/ledger settlement, and scoped live tracking form
the complete safe path from request to driver payout.
