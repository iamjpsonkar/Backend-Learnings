# Complete Solution: Fleet Tracking

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Authenticated vehicle devices stream GPS, motion, ignition, odometer, battery/fuel,
diagnostics and sensor telemetry, buffering while offline. Operators view current
fleet state, subscribe to subsets, replay trips, define geofences/rules, receive
deduplicated alerts, and export retained/downsampled history under tenant isolation.

Targets: five million active vehicles, accepted ingest p99 below 200 ms, event-to-
dashboard/geofence alert p99 below five seconds for online devices, latest read below
150 ms, 99.99% operational reads, and no silent data loss after ACK. Events are at
least once and out of order; device session/sequence/event time define dedupe/order.
Late data corrects history but does not pretend an old location is current.

## 2. Capacity estimation

Five million vehicles updating every ten seconds produce 500,000 events/s. At 250
bytes compressed/event:

- ingress is about 125 MB/s or 10.8 TB/day before replication;
- 30 days raw is roughly 324 TB, requiring compression, columnar object storage and
  tiered retention/downsampling;
- latest state at 1 KB/vehicle is only 5 GB before replicas, but receives high churn;
- offline reconnect can create 10–100x bursts, so per-device/tenant admission and
  batch limits protect live traffic;
- dashboards should subscribe to visible/selected vehicles, not broadcast all five
  million positions to every operator.

## 3. Device and operator APIs

```text
POST /v1/device-sessions                   mutual auth, bootId, firmware
POST /v1/telemetry/batches                 {sessionId, firstSeq, events[], checksum}
GET  /v1/fleets/{id}/vehicles?cursor=
GET  /v1/vehicles/{id}/latest
GET  /v1/vehicles/{id}/trips?from=&to=&cursor=
GET  /v1/vehicles/{id}/telemetry?from=&to=&signals=&cursor=
POST /v1/geofences                         Idempotency-Key
PATCH /v1/geofences/{id}                   If-Match: version
POST /v1/alert-rules                       Idempotency-Key
GET  /v1/alerts?state=&cursor=
POST /v1/alerts/{id}/acknowledge           Idempotency-Key
```

Batch response returns highest durably accepted contiguous sequence plus per-event
rejections/gaps, allowing device retry. Bound events/bytes/time span, coordinate/sensor
ranges, upload rate, query interval/signals, polygon complexity and stream subscriptions.

## 4. Data model

```text
Device(id, tenant_id, vehicle_id, certificate_id, state, firmware, version)
DeviceSession(id, device_id, boot_id, started_at, last_contiguous_sequence, state)
TelemetryEvent(tenant_id, vehicle_id, device_session_id, sequence, event_time,
               receive_time, location, accuracy, speed, heading, ignition,
               odometer, signals, integrity_flags, schema_version)
LatestVehicle(vehicle_id, session_id, sequence, event_time, receive_time,
              location, motion, ignition, signals_summary, freshness, version)
Trip(id, vehicle_id, start_time, end_time, start_point, end_point,
     distance, duration, state, processor_version)
Geofence(id, tenant_id, geometry, rule, version, state)
FenceMembership(vehicle_id, geofence_id, geofence_version, state,
                candidate_since, last_event_time, version)
Alert(id, tenant_id, vehicle_id, rule_id, occurrence_key, state,
      first_event_time, last_event_time, evidence, version)
```

Raw durable log/object lake is the event source. Latest, trips, memberships, alerts,
dashboard streams and aggregates are rebuildable versioned projections.

## 5. Architecture

```text
vehicle device -> mTLS regional ingest -> durable vehicle-partitioned log
                         |                         |
                   device registry          stream processors
                                            /      |       \
                                       latest    trips    geofence/rules -> alert outbox
                                          |        |               |
                                     latest KV  hot TSDB      notification/escalation
                                                     \
                                                      columnar object archive

operator -> API/auth -> fleet/vehicle index -> latest/history stores
operator -> scoped WebSocket gateway <- subscription router/latest-change stream
```

Partition log by stable vehicle ID to preserve per-vehicle arrival order. Separate
regions/cells by tenant/device geography, with schema registry and replayable processor
checkpoints. Alert delivery is downstream from durable alert state.

## 6. Step-by-step workflow

1. Provision device certificate bound to tenant/vehicle; device opens boot session,
   synchronizes approximate clock, and receives schema/rate/config policy.
2. Device samples adaptively, assigns increasing sequence within session, persists
   unacknowledged batch locally, compresses/checksums, and uploads over mTLS.
3. Ingest authenticates binding, validates batch/schema/ranges/time/size, deduplicates
   session sequences, appends accepted events durably keyed by vehicle, then ACKs.
4. Latest processor applies only a newer valid session/sequence/event, marks integrity/
   freshness, and emits compact change. Dashboard gateway fans it only to authorized
   visible subscriptions, coalescing intermediates.
5. Event-time processors reorder within watermark, map-match/smooth as appropriate,
   segment trips, evaluate geofence/rules with hysteresis/dwell, and persist alerts
   idempotently.
6. Hot detailed history lands in time-series store; immutable raw/normalized files are
   compacted to columnar object storage, downsampled and expired by policy.
7. Late offline events enter historical correction path; alerts have a separate lateness
   policy and never replace current position with old telemetry.

## 7. Device batching and ACK logic

```text
device:
    event = sampleSensors()
    localQueue.append(sessionId, nextSequence++, eventTime, event)
    when online and (batch full or maxDelay reached):
        batch = localQueue.oldestContiguous(MAX_BYTES, MAX_EVENTS)
        response = upload(compress(batch), checksum)
        localQueue.deleteThrough(response.highestContiguousAccepted)

server ingest(batch):
    require certificate.deviceId == batch.deviceId
    require session active and bootId matches
    validate checksum/schema/count/time/ranges
    for event in batch:
        appendUnique(log, key=(sessionId, sequence), vehicleKey, event)
    after durable quorum append:
        advance contiguous ACK from session sequence bitmap/gap state
    return ACK and explicit invalid/gap list
```

Do not ACK before durable append. Unique session/sequence makes retry harmless. Limit
device disk retention and prioritize newest safety-critical live points while retaining
explicit gap/drop counters if buffer fills.

## 8. Latest-state logic

```text
function applyLatest(event):
    current = latest.get(event.vehicleId)
    if !deviceSessionOrdering.allows(current.sessionId, event.sessionId): return OLD_SESSION
    if event.sessionId == current.sessionId and event.sequence <= current.sequence:
        return DUPLICATE_OR_OLD
    if event.eventTime < current.eventTime - LATEST_LATENESS_TOLERANCE:
        routeToHistoryOnly(event); return LATE

    integrity = validateMovementAndSensors(current, event)
    next = normalize(event, integrity, freshness=receiveTime-event.eventTime)
    latest.compareAndSetBySessionSequence(event.vehicleId, next)
```

A new boot session receives a server-ordered session generation; old device/session
packets cannot displace it. Device clock is untrusted: retain both times and estimate
offset/drift. UI always shows event time, receive age and accuracy/integrity.

## 9. Event-time reorder and watermarks

For each vehicle/partition, maintain maximum observed event time and watermark such as:

```text
watermark = maxObservedEventTime - ONLINE_ALLOWED_LATENESS
```

Buffer events until watermark, then process in `(event_time, session_generation,
sequence)` order. Persist state/checkpoint atomically with output or use idempotent
output keys. Events later than watermark update history/trip correction version but
only generate real-time alerts if rule's lateness policy allows. A longer watermark
improves ordered trip accuracy but delays alerts; use short operational and longer
historical correction pipelines.

## 10. Trip segmentation logic

```text
function onOrderedTelemetry(state, event):
    moving = event.ignition == ON or event.speed > MOVE_THRESHOLD
             or significantDisplacement(state.lastPoint, event)
    if state.trip == NONE and moving persists START_DWELL:
        state.trip = createTrip(startAt=firstMovingEvent,
                                startPoint=firstMovingPoint)
    if state.trip active:
        if plausible(event):
            state.trip.distance += mapMatchedOrGeodesicDelta(state.lastGood, event)
            update duration/stops/sensor summaries
        if !moving persists STOP_DWELL and ignition != ON:
            closeTrip(endAt=lastMovingEvent, endPoint=lastGood)
    state.lastPoint = event
```

Use ignition when reliable, with movement fallback. Accuracy-aware filtering avoids
stationary GPS drift adding kilometers. Odometer deltas can cross-check/map calibration
but may reset/roll over. Late events produce a new trip projection version and audit diff.

## 11. Geofence evaluation

Index versioned geofence bounding cells (H3/S2/R-tree) to retrieve candidates; exact
point-in-polygon/circle/corridor test decides membership. Account for GPS accuracy and
boundary noise with inner/outer hysteresis and dwell:

```text
function evaluateFence(membership, point, accuracy, fence, eventTime):
    insideInner = fence.containsWithMargin(point, +ENTER_MARGIN + accuracyFactor)
    outsideOuter = !fence.containsWithMargin(point, -EXIT_MARGIN - accuracyFactor)
    desired = membership.state
    if membership.state == OUTSIDE and insideInner: desired = ENTER_CANDIDATE
    if membership.state == INSIDE and outsideOuter: desired = EXIT_CANDIDATE
    if candidate desired persists fence.dwellDuration:
        transition to INSIDE/OUTSIDE
        emit occurrenceKey=(vehicle,fence,fenceVersion,transition,candidateStart)
```

Geometry margin sign follows library convention and must be tested. Version change
re-evaluates memberships explicitly; it should not create phantom enter/exit without
marked `CONFIG_CHANGE` semantics.

## 12. Rules and alert delivery

Rules include enter/exit/dwell, speeding by road/zone, device silence, ignition after
hours, route deviation, sensor threshold duration and maintenance. A stateful evaluator
uses versioned configuration/effective time, suppresses flapping, groups repeated
conditions, and stores evidence/confidence.

```text
transactionally upsert Alert by unique occurrence_key
    NEW -> ACTIVE -> ACKNOWLEDGED -> RESOLVED
append alert outbox once per escalation generation
```

Notification service applies user schedule/channel/escalation and retries with stable
delivery ID. Delivery failure does not erase alert. Silence alerts use durable timers/
periodic scans of latest receive time, not absence from a best-effort stream alone.

## 13. Dashboard fan-out

Operator obtains token scoped to tenant/fleet/vehicle/filter. Gateway authorizes initial
vehicle set and subscribes to relevant partition/cell groups, then filters every update
by current membership/ACL version. Send snapshot followed by deltas with vehicle state
version; gap/reconnect fetches latest snapshot. Coalesce each vehicle, cap viewport/
selection counts, cluster at low zoom, and drop intermediate movements for slow clients.

ACL/fleet membership changes push revocation version and disconnect/remove affected
vehicles. Cached latest data never bypasses tenant authorization.

## 14. History storage and queries

Keep recent normalized telemetry in time-partitioned TSDB for operational ranges.
Compact immutable raw events and derived points into columnar files partitioned by
tenant/date/vehicle hash with catalog/checksums. Downsample older data (for example
one-minute stops/route summaries) per product/legal policy while retaining required
audit/safety evidence separately.

History query validates tenant/vehicle/time/signal authorization, chooses hot/cold
partitions, merges by event ordering, applies correction version, and uses cursor
`(event_time, session_generation, sequence)`. Large exports are asynchronous, encrypted,
expiring and audited.

## 15. Device configuration and commands

Desired config (sampling, sensors, thresholds, firmware) is versioned and signed.
Device reports applied version/status; server never assumes delivery equals application.
Remote commands have ID, nonce, expiry, allowed device state, approval, and result
state. Safety-critical immobilization/control is outside ordinary telemetry path and
requires specialized fail-safe/legal/security design; do not infer authorization from
fleet dashboard access.

## 16. Partitioning and overload

Partition by vehicle for ordered processing and tenant/cell for access/search indexes.
Large tenants receive isolated quotas/partitions; hot firmware bugs cannot flood shared
ingest. Offline backlog uses separate fair queue/throughput from live events. Under
load, preserve durable ingest and safety alerts, lower dashboard frequency, delay
analytics/history compaction, and communicate data age. Autoscale by bytes/events/
stateful partition lag, not CPU alone.

## 17. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Device retries batch | Session/sequence unique key accepts events once |
| Device offline | Persist local bounded queue; upload later with event time |
| Ingest dies before ACK | Device retries; durable log deduplicates |
| Latest processor replays | CAS session/sequence prevents regression |
| Stream processor dies | Restore checkpoint/state and replay partition |
| Geofence config changes | Versioned re-evaluation with config-change semantics |
| Dashboard gateway dies | Reconnect, authorize, snapshot then deltas |
| Alert channel fails | Durable alert remains and delivery retries/escalates |
| Region partitions | Devices buffer/reroute policy; fenced config/lifecycle writers |

## 18. Security, safety, and privacy

Provision unique device certificates in secure hardware where possible; rotate/revoke,
use mTLS, signed firmware/config, anti-replay session/sequence, encrypted storage,
tenant/vehicle/field RBAC, network isolation, KMS/HSM keys, tamper-evident audit, and
break-glass review. Prevent device cloning, fake GPS/CAN data, firmware downgrade,
command spoofing, tenant IDOR, fleet enumeration, export abuse, dashboard token theft,
malformed telemetry and insider tracking.

Treat routes, homes, schedules, drivers and diagnostics as sensitive. Apply explicit
purpose/consent, least precision, role/time restrictions, retention/downsampling/
deletion, residency, labor/vehicle/safety law, legal hold and incident response.
Separate operational safety evidence from optional analytics and test backup/key recovery.

## 19. Observability

Track devices online/silent/session churn, ingest events/bytes/latency/ACK gaps,
duplicates/out-of-order/late/invalid/impossible movement, clock skew, stream partition
lag/skew/rebalances, latest age/CAS rejects, trip start/stop/correction/distance drift,
geofence candidate/transition/delay/flap, alert creation/dedupe/delivery/ack age,
dashboard connections/coalescing/drops/version gaps, history compaction/query/export,
tenant quota, storage growth, firmware/schema mix and region health.

Property tests reorder/duplicate sessions/events and assert latest monotonicity. Replay
golden trips/geofences including noisy boundaries, tunnels, offline batches and config
changes. Load-test live plus reconnect storms and one noisy tenant. Chaos tests kill
ingest/brokers/processors/latest/gateways/alerts; reconciliation compares ACK ranges
to log, projections/checkpoints to replay, holds retention/purge, and alert occurrences.

## 20. Implementation path

1. **MVP:** mTLS devices, sequenced batches/durable log, latest KV, tenant API/map,
   explicit staleness and basic recent history.
2. **Operational intelligence:** event-time processor/checkpoints, trips, geofences/
   dwell alerts, WebSockets, device silence, retry/escalation and reconciliation.
3. **Scale/lifecycle:** regional vehicle partitions, offline fair lane, TSDB/object
   archive/downsampling, exports, config/firmware status, advanced rules/analytics.
4. **Hardening:** device/tenant/security/privacy/safety controls, property/replay/noisy-
   tenant/load/chaos tests, restore/key/firmware drills, runbooks, dashboards, and SLOs.

## 21. Final design

Authenticate each device and durably append session-sequenced telemetry before ACK to
a vehicle-partitioned log. Conditional latest state serves operations without late
regression; independent event-time processors with watermarks build correctable trips,
geofence membership and idempotent alerts. Scoped gateways coalesce authorized live
views while raw history flows to tiered, downsampled retention. Device offline replay,
processor checkpoints and explicit data age make failures visible and recoverable
without inventing positions or losing the audit trail.
