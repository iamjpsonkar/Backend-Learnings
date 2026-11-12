# Complete Solution: Geofencing Platform

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Tenants create versioned circle/polygon/corridor fences with schedules, device/group
scope, enter/exit/dwell rules and actions. Authenticated devices send sequenced points.
The platform finds candidate fences, performs exact accuracy-aware geometry tests,
suppresses GPS boundary jitter, maintains per-device membership, durably emits unique
transitions, and delivers signed webhooks/actions with retries and audit.

Targets: one million positions/s, 100 million fences, event-to-transition p99 below
three seconds for online data, 99.99% ingest/evaluation availability, bounded candidates
per point, and deterministic replay from the same positions/fence versions. Events are
at least once/out of order. State is keyed by device and event time; actions are at
least once with stable transition IDs.

## 2. Capacity estimation

At one million points/s and 200 bytes/point, ingress is 200 MB/s or 17 TB/day before
replication. Assume 100 million fences, ten covered index cells/fence average, five
candidates/point after scope/cell filtering, and 1% active device-fence memberships.

- Index can approach one billion postings; compress by cell/tenant and separate large
  geometry tiers.
- Exact tests can reach five million/s; geometry simplification/bounding boxes and
  prepared shapes are essential.
- If ten million active devices each retain 20 nearby/inside states at 100 bytes, state
  is about 20 GB before checkpoint/replication.
- A bad tenant with thousands of overlapping fences can multiply cost enormously;
  enforce overlap/candidate/evaluation quotas at write and serve time.
- Raw position retention is expensive and privacy-sensitive; keep only the durable log
  horizon needed for replay plus tenant/legal policy, then aggregate/delete.

## 3. APIs

```text
POST   /v1/fences                         Idempotency-Key
PATCH  /v1/fences/{id}                    If-Match: version
DELETE /v1/fences/{id}                    If-Match: version
GET    /v1/fences?cursor=
POST   /v1/device-sessions
POST   /v1/positions                      {sessionId, sequence, points[]}
GET    /v1/devices/{id}/memberships
GET    /v1/transitions?device=&fence=&cursor=
POST   /v1/action-endpoints
POST   /v1/transitions/{id}/replay-action Idempotency-Key
```

Fence request specifies coordinate reference (normally WGS84), circle/polygon/multipolygon/
corridor, altitude optional, schedule/timezone, scope selector, transition types, dwell,
hysteresis, accuracy policy and action. Bound vertices/area/perimeter/fences/tenant,
overlap, schedules, positions/batch/rate/lateness and action destinations.

## 4. Data model

```text
Fence(id, tenant_id, geometry_ref, geometry_type, bounding_box, state,
      schedule, timezone, scope_selector, rule, hysteresis,
      version, effective_at, created_at)
FenceIndexPosting(tenant_id, cell_id, fence_id, fence_version, index_tier)
DeviceSession(id, tenant_id, device_id, generation, last_sequence, state, expires_at)
Position(id, tenant_id, device_id, session_id, sequence, event_time,
         receive_time, point, altitude, accuracy_m, integrity_flags)
Membership(device_id, fence_id, fence_version, relation,
           candidate_relation, candidate_since_event_time,
           last_event_time, last_position_sequence, version)
Transition(id, tenant_id, device_id, fence_id, fence_version, type,
           occurrence_key, event_time, emitted_at, evidence, processor_version)
ActionIntent(transition_id, endpoint_id, action_generation, state, attempt, next_at)
Checkpoint(partition_id, input_offset, state_snapshot_ref, processor_version)
Outbox(id, aggregate_id, version, event_type, payload, published_at)
```

Fence geometry artifacts and prepared indexes are immutable per version. Transition
unique `occurrence_key` makes replay/action creation idempotent.

## 5. Architecture

```text
tenant -> fence API/schema/geometry validator -> fence DB/object geometry
                                                   |
                                           index builder/change log
                                                   |
                                         H3/S2 cell candidate index

device -> authenticated ingest -> device-partitioned durable position log
                                                  |
                                      event-time state processors
                                       /         |          \
                                candidate index geometry   membership/checkpoint
                                       \\         |          /
                                         transition log/outbox
                                                  |
                                      action scheduler -> signed webhooks/connectors
```

Partition positions/state by tenant+device so one processor sees ordered device history.
Partition fence index by tenant/cell and cache hot prepared geometry near processors.
Separate evaluation from external action delivery.

## 6. Step-by-step workflow

1. Tenant submits fence. Service authenticates scope, validates/normalizes geometry,
   topology, size, schedule/rules and quotas; writes versioned fence plus outbox.
2. Index builder covers geometry conservatively at one/multiple cell resolutions,
   writes immutable prepared shape/postings, verifies cover, then marks version ACTIVE.
3. Device opens authenticated generation session and sends batches with increasing
   sequence, event time and accuracy. Ingest deduplicates and appends durably before ACK.
4. Stateful processor reorders within watermark, selects fence version effective at
   event time, retrieves scoped cell candidates plus currently active memberships, and
   runs bounding-box then exact geometry/accuracy relation.
5. Per device-fence hysteresis/dwell state machine conditionally advances membership.
   A committed transition and membership/checkpoint output share an exactly-once
   transactional stream boundary or use unique keys/idempotent sinks.
6. Action planner creates one intent per transition/endpoint/generation. Dispatcher
   signs payload, retries with jitter, records attempts and dead-letters persistently
   failing destinations without slowing evaluation.
7. Late data follows documented correction policy; fence edit/delete triggers explicit
   re-evaluation/config transitions rather than fabricated movement.

## 7. Geometry validation and normalization

```text
function normalizeFence(input):
    require supported WGS84 geometry and finite coordinate ranges
    geometry = closeRingsAndNormalizeOrientation(input.geometry)
    geometry = splitOrRepresentAntimeridianCorrectly(geometry)
    require no invalid self-intersections unless valid multipolygon semantics
    require vertices <= MAX and area/perimeter/radius within tenant tier
    prepared = geometryLibrary.prepare(geometry)
    bbox = geodesicAwareBoundingBox(geometry)
    test representative/boundary points and serialization round trip
    return immutable geometry, prepared, bbox
```

Use a proven spherical/ellipsoidal geometry library. Raw longitude/latitude planar
math fails near poles/antimeridian and on large polygons. Define boundary inclusion,
holes, overlapping multipolygons, altitude and corridor buffer semantics explicitly.

## 8. Spatial candidate index

Circle/polygon cover is a **superset** of geometry: boundary cells must not be missed.
False positives are removed by exact test.

```text
function buildFencePostings(fence):
    if fence is small:
        cells = H3.polyfillOrCircleCover(fence.geometry, fineResolution,
                                         includeBoundary=true)
        if cells.size <= MAX_POSTINGS: write FINE postings
    else:
        cells = coverAtCoarserResolution(fence.geometry, MAX_POSTINGS)
        write COARSE postings and prepared exact geometry
    verify random/boundary sample points inside fence map to at least one posting
```

At query, lookup device point's ancestors/descendants needed by index tiers. Scope by
tenant/device group before exact work. Very large/global fences use a separate tenant-
wide tier, not postings in millions of cells. Cache posting lists with fence version.

## 9. Position ingestion and ordering

```text
function ingest(device, batch):
    require certificate/token binds tenant, device, session generation
    validate checksum/schema/count/time/coordinate/accuracy
    for point in sequence order:
        appendUnique(positionLog,
          key=(sessionId, point.sequence), partition=(tenant, device), point)
    after durable quorum append return highest contiguous accepted sequence
```

Processor uses `(session_generation, sequence)` for dedupe and event time for spatial
semantics. Watermark `max_event_time - allowed_lateness` bounds reorder. New session
generation fences old device uploads. Retain receive time and clock-integrity flags;
device clock is not automatically trusted.

## 10. Accuracy-aware geometry relation

A GPS point represents uncertainty, often a radius. Compute signed distance to boundary
(positive inside, negative outside under chosen convention) using exact geometry:

```text
function relation(point, accuracy, fence, membership):
    d = signedDistanceToBoundary(point, fence.geometry)
    enterThreshold = fence.enterMargin + accuracyWeight * accuracy
    exitThreshold  = fence.exitMargin  + accuracyWeight * accuracy

    if d >= enterThreshold: return DEFINITELY_INSIDE
    if d <= -exitThreshold: return DEFINITELY_OUTSIDE
    return UNCERTAIN_BOUNDARY
```

Margins/accuracy policy depend on safety/product. Do not emit enter/exit while uncertain;
retain prior stable relation and possibly expose confidence. For simple circles, use
geodesic center distance; for polygons/corridors, prepared exact geometry and boundary
distance. Smooth obviously noisy points, but do not move users across real boundaries.

## 11. Enter/exit/dwell state machine

```text
function applyRelation(m, relation, event, fence):
    target = relation == DEFINITELY_INSIDE ? INSIDE
           : relation == DEFINITELY_OUTSIDE ? OUTSIDE
           : UNKNOWN
    if target == UNKNOWN:
        m.candidateRelation = NONE
        return no transition
    if target == m.relation:
        m.candidateRelation = NONE
        update last evidence
        if target == INSIDE and dwellDueAndNotEmitted(m, fence, event.eventTime):
            emit DWELL with stable entry generation
        return
    if m.candidateRelation != target:
        m.candidateRelation = target
        m.candidateSince = event.eventTime
        return
    if event.eventTime - m.candidateSince >= requiredDwellFor(target, fence):
        previous = m.relation
        m.relation = target; m.entryGeneration += (target == INSIDE)
        m.candidateRelation = NONE
        emit target == INSIDE ? ENTER : EXIT using stable occurrence key
```

An initial point inside follows configured `emitInitialEnter` policy; otherwise it
establishes membership silently. Dwell is tied to one entry generation and emitted once.
Sparse sampling may mean actual crossing time is within an interval; use evidence time/
confidence instead of claiming exact boundary instant.

## 12. Candidate lifecycle and missing fences

Always evaluate currently INSIDE/candidate memberships even if current point's cell
lookup omits fence due to index version/cache issues, so exits are not lost. Union:

```text
cellCandidates(point, activeIndexVersion)
+ device active/candidate membership fence IDs
+ tenant-wide large fences
```

Expire OUTSIDE state after retention if far/no longer candidate; retain active INSIDE
until exit, fence deactivation/config action or device/session expiry policy. Cap nearby
state per device and reject tenant fence layouts that exceed evaluation budget.

## 13. Fence updates and event-time versions

Fence update creates new immutable version/effective time, builds/verifies postings,
then atomically activates. Events before effective time use prior retained version;
later events use new. State migration re-evaluates latest position and labels results:

- `ENTER/EXIT_BY_MOVEMENT` for position-driven transitions;
- `INSIDE/OUTSIDE_BY_CONFIGURATION` when geometry/scope activation changed relation;
- `FENCE_DEACTIVATED` when deletion ends membership.

Whether configuration changes trigger business actions is explicit per rule. Do not
send “device entered” merely because an administrator enlarged a polygon unless desired.

## 14. Late data and corrections

Operational processor uses short watermark for low latency. Events later than watermark:

- update audit/history and optionally recompute membership timeline in a new correction
  version;
- do not retract already delivered physical actions automatically;
- emit explicit correction transition only for tenants/rules that support it;
- never replace current membership with a very old point.

For billing/compliance use a slower finalization pipeline with longer lateness and
versioned results. Define semantics at product contract level.

## 15. Action delivery

Payload includes transition ID, occurrence key, tenant/device pseudonymous ID, fence/
version, type, evidence event time, emitted time, confidence and schema version. Sign
timestamp plus raw body (HMAC/asymmetric), use TLS, restrict endpoints and prevent SSRF.

Dispatcher applies per-tenant/endpoint concurrency, circuit breaker and exponential
jitter. 2xx succeeds; retry timeouts/429/5xx within max age; permanent errors/DLQ alert.
Customer must deduplicate transition ID. Manual replay uses a new delivery generation
but same transition identity and is audited.

## 16. Partitioning and state recovery

Hash `(tenant,device)` to ordered input/state partition. Fence index shards by
`tenant,cell/tier`; replicate across zones and cache prepared shapes. Stateful processor
checkpoint contains input offset plus membership/timer state in durable backend.

On failure restore consistent checkpoint and replay. Transition sink unique occurrence
key/outbox makes duplicates harmless. Rescaling transfers keyed state and fences old
processor epoch before new ownership; two processors must not concurrently emit for
one device partition.

## 17. Overload and tenant isolation

Charge cost units for positions × candidate fences × geometry complexity. Enforce
fences/vertices/overlap/device/QPS/action backlog quotas and validate worst-case cell
density at fence creation. Isolate large tenants/regions and give live versus offline
backfill separate queues. Under pressure preserve durable ingest/transition state,
reduce optional history/analytics, slow backfills/actions with visible lag, and reject
new abusive fences rather than drop transitions silently.

## 18. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Device repeats/reorders point | Session sequence and watermark dedupe/order it |
| Processor crashes after transition write | Replay hits unique occurrence key |
| Checkpoint/state is lost | Restore prior checkpoint and replay durable positions |
| Fence index update is partial | Keep prior ACTIVE version; never expose incomplete cover |
| Point jitters at boundary | Uncertain band plus enter/exit dwell suppresses flapping |
| Webhook endpoint fails | Evaluation continues; durable intent retries/DLQs |
| Late point contradicts history | Versioned correction policy, not current regression |
| Fence deletion races position | Effective version ordering/config transition decides |
| Region fails | Restore fenced partition owners from replicated log/checkpoint |

## 19. Security, safety, and privacy

Enforce tenant/device/fence/action roles and device credentials; use mTLS, signed fence/
config/artifacts/webhooks, encrypted position/state, KMS keys, anti-replay session/
sequence, endpoint egress controls, rate limits, tamper-evident audit and break-glass
review. Prevent cross-tenant IDOR, device spoofing/cloning, fake GPS, malicious polygons,
overlap amplification, webhook SSRF, secret leaks, replay, transition forgery, dashboard/
export scraping and insider location lookup.

Obtain clear consent/purpose for tracking/actions; minimize precision/history, use
pseudonymous device IDs in callbacks, restrict sensitive fences (homes, clinics,
workplaces), and enforce retention/deletion/residency/child/worker laws/legal hold.
Safety-critical automation must have fail-safe local confirmation; a noisy cloud GPS
transition alone should not unlock machinery or trigger irreversible harm.

## 20. Observability

Track ingest QPS/bytes/latency/ACK gaps, duplicate/old/late/invalid/spoof points,
watermark/partition lag and skew, candidates per point/tenant/cell, exact-test latency/
geometry tier/cache hit, uncertain boundary/jitter suppressed, memberships/state size,
enter/exit/dwell count/delay/corrections, fence index build/activation/version skew,
checkpoint/recovery/replay duplicates, action queue/delivery/retry/DLQ/signature, quota/
overlap rejection, data age and cost million evaluations.

Property-test circles/polygons/holes/corridors, boundary/accuracy, antimeridian/poles,
shuffled duplicate points, dwell and fence version races. Replay golden trajectories
and compare deterministic transitions. Load-test dense overlapping cells/noisy devices,
kill processors/index/state/action/regions, and reconcile active membership/transition/
action counts against replay and retention/purge policy.

## 21. Implementation path

1. **MVP:** tenant/device auth, circle fences, durable sequenced positions, exact
   geodesic relation, simple enter/exit state, transition log and signed webhook.
2. **Correctness:** polygon/corridor prepared geometry, conservative cell index,
   accuracy hysteresis/dwell, checkpoints/replay, idempotent action/DLQ and fence versions.
3. **Scale/product:** 100M-fence tiers, device groups/schedules, large-tenant isolation,
   late correction/finalization, dashboard/history, regional state and connectors.
4. **Hardening:** security/privacy/safety/worker controls, geometry/property/dense-load/
   chaos tests, replay/restore/key drills, runbooks, dashboards, and SLOs.

## 22. Final design

Compile each immutable fence version into a verified conservative multi-tier cell cover
and prepared exact geometry. Device-sequenced positions flow through a device-keyed
event-time state processor that unions cell candidates with active memberships, applies
accuracy-aware exact relation plus hysteresis/dwell, and writes a unique transition with
checkpointed state. Signed actions retry independently. Explicit effective versions,
configuration-versus-movement semantics and late-correction policy keep replay
deterministic, while overlap quotas and privacy/safety controls prevent spatial scale
or noisy GPS from becoming duplicate or harmful actions.
