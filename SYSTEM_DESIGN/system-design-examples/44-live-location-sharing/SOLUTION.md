# Complete Solution: Live Location Sharing

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

A user explicitly starts a bounded session, chooses viewers/precision/duration, streams
location from one active device, and can pause/revoke/end immediately. Authorized
viewers receive latest position with event/receive time, accuracy, motion and freshness;
reconnect fetches a snapshot then deltas. Optional short trail is tightly retained.

Targets: 10 million active sessions, ingest-to-viewer p99 below two seconds, latest
read p99 below 150 ms, 99.99% viewer availability, revocation denial within seconds,
and session data automatically deleted at expiry. Updates are at least once and may
drop/coalesce; per device session/sequence makes latest state monotonic. Staleness is
shown explicitly—never extrapolated as fact.

## 2. Capacity estimation

At ten million active shares and one moving update/five seconds:

- ingest averages two million updates/s; stationary adaptive sampling can reduce it
  by an order of magnitude;
- at 150 bytes/update, ingress is about 300 MB/s before replication/protocol overhead;
- latest records at 300 bytes are only 3 GB before replicas, but write churn is high;
- with three viewers/session, naive delivery is six million messages/s; regional
  gateway subscription aggregation/coalescing is required;
- retaining every update for 24 hours would be roughly 26 TB/day raw, so store only
  consented sampled trail with short TTL, not an unlimited history by default.

## 3. APIs and connection protocol

```text
POST   /v1/location-shares                  {viewers, duration, precision} Idempotency-Key
PATCH  /v1/location-shares/{id}             {viewers, precision, expiresAt} If-Match
POST   /v1/location-shares/{id}/pause       Idempotency-Key
POST   /v1/location-shares/{id}/resume      Idempotency-Key
DELETE /v1/location-shares/{id}             Idempotency-Key
POST   /v1/location-shares/{id}/positions   {deviceSession, sequence, points[]}
GET    /v1/location-shares/{id}/latest
GET    /v1/location-shares/{id}/trail?cursor=
POST   /v1/location-shares/{id}/stream-tokens
```

Stream token binds session, viewer, session ACL version, precision, expiry and nonce.
Messages include session version, position sequence, coordinates at authorized precision,
accuracy radius, device event time, server receive time and `fresh|stale` status.
Bound duration/viewers/batch/rate/history and reject coordinates/time outside limits.

## 4. Data model and lifecycle

```text
ShareSession(id, owner_id, state, expires_at, precision_policy,
             history_policy, acl_version, active_device_session, version, created_at)
ShareViewer(session_id, principal_id, role, state, acl_version)
DeviceSession(id, share_session_id, owner_id, device_id, state,
              last_sequence, issued_at, expires_at)
LatestPosition(session_id, device_session_id, sequence, lat_e7, lng_e7,
               accuracy_m, speed, heading, event_time, receive_time, integrity_state)
PositionSample(session_id, time_bucket, sequence, encrypted_point, expires_at)
Revocation(session_id, acl_version, revoked_before, reason)
Outbox(id, aggregate_id, version, event_type, payload, published_at)
```

```text
CREATED -> ACTIVE -> PAUSED -> ACTIVE
   any nonterminal -> ENDED | EXPIRED
```

Only ACTIVE accepts/publishes. One active device session simplifies ordering; handoff
atomically revokes the old device and creates a higher session generation.

## 5. Architecture

```text
owner app -> regional ingest/auth -> session owner shard -> latest-position KV
                      |                    |                   |
                 abuse/integrity       session SQL/outbox     pub/sub by session
                                                                 |
viewer -> edge auth/token -> WebSocket gateways <----------------+
                     |             |
                latest snapshot  regional subscription/coalescing

expiry buckets/sweeper -> session shard/revocation/purge
optional sampled encrypted trail -> short-TTL object/time-series store
```

Hash session ID to a home shard/region that serializes lifecycle, ACL and active-device
generation. Position data can ingest regionally but routes to/replicates through the
session owner with sequence-conditional latest updates. Pub/sub is ephemeral; latest
store provides recovery.

## 6. Step-by-step workflow

1. Owner explicitly creates share with allowed principals/link policy, duration,
   precision and history setting. Transaction stores session/ACL, expiry entry and
   active device credential; return invite/token references.
2. Viewer authenticates/accepts invitation. Edge checks current session/ACL and issues
   a short stream token; gateway rechecks version on connection and subscribes session.
3. Owner app adaptively samples, attaches current device session and increasing sequence,
   batches briefly, and sends over authenticated encrypted channel.
4. Ingest validates session/owner/state/expiry/device generation, point/time/accuracy/
   plausibility/rate, then conditionally updates latest only for higher sequence.
5. After successful update, publish compact latest event. Gateways authorize subscribers,
   apply each viewer's precision, coalesce intermediate points, and send newest sequence.
6. On reconnect/gap, viewer fetches authorized latest then resumes events after sequence;
   UI displays accuracy and age, declaring stale after threshold.
7. Pause/revoke/end/expiry increments ACL/session version, invalidates tokens/gateway
   subscriptions immediately, stops ingest/fan-out, and schedules latest/trail purge.

## 7. Core session creation and authorization

```text
function createShare(owner, command, key):
    require duration within policy and viewers.size <= MAX_VIEWERS
    requestHash = canonicalHash(command)
    transaction:
        return matching prior idempotent response if exists
        require every viewer is valid and ownerMayShareWith(viewer)
        session = sessions.insert(owner.id, ACTIVE, now + command.duration,
                                  command.precision, command.history, aclVersion=1)
        viewers.insertAll(session.id, command.viewers, aclVersion=1)
        device = deviceSessions.insert(session.id, owner.deviceId, generation=1)
        expiry.insert(session.expiresAt, session.id, session.version)
        outbox.insert(ShareStarted(session.id, session.version))
        store idempotency response
    return scoped owner credential and invite references

function authorizeViewer(viewer, sessionId):
    session = sessions.getStrongOrVersionValidated(sessionId)
    require session.state == ACTIVE and session.expiresAt > now
    require viewers.active(sessionId, viewer.id, session.aclVersion)
    return capability(sessionId, viewer.id, session.aclVersion,
                      allowedPrecision(session, viewer), ttl=short)
```

Knowledge of session ID is never authorization. Link sharing uses high-entropy,
revocable, expiring capability with optional login/approval and limited resharing.

## 8. Core position acceptance logic

```text
function ingest(owner, sessionId, update):
    session = sessionCache.getWithVersion(sessionId)
    require session.ownerId == owner.id
    require session.state == ACTIVE and session.expiresAt > now
    require update.deviceSession == session.activeDeviceSession
    require validCoordinatesAccuracyAndTime(update)
    integrity = detectImpossibleJumpOrSpoof(latest.get(sessionId), update)
    require policyAllows(integrity)

    applied = latest.compareAndSetIf(
      sessionId,
      predicate = old => old == null or
         (old.deviceSession == update.deviceSession and update.sequence > old.sequence),
      value = normalizedPosition(update, serverReceiveTime, integrity))
    if !applied: return DUPLICATE_OR_OLD

    if session.historyPolicy.enabled and shouldSampleForTrail(update):
        trail.appendEncryptedWithTTL(sessionId, update)
    pubsub.publish(sessionId, LatestChanged(update.sequence, session.aclVersion))
    return ACCEPTED
```

The authoritative compare-and-set must not rely only on a racy local cache. A new
device generation compares higher session identity; old device packets are rejected.

## 9. Adaptive client sampling

```text
function chooseSampling(state):
    if appHasNoActiveShare: stopGPS()
    else if batteryCritical and not emergencyMode: interval=30s; accuracy=BALANCED
    else if movingFast or viewerActivelyWatching: interval=2-5s; accuracy=HIGH
    else if walking: interval=5-10s; accuracy=HIGH
    else if stationary: interval=30-120s; use significant-change/geofence wakeup
    add immediate sample on session start/resume, large movement, network recovery
```

Use OS fused location/activity APIs, distance and time thresholds, batch while offline,
and exponentially back off network errors. Keep sequence and original event times.
Server may return desired maximum frequency based on viewers/load, but device safety/
accessibility/emergency policy governs minimum behavior.

## 10. Fan-out and backpressure

Gateways subscribe once per local session regardless of local viewer connections,
fetch latest record on event, and send only if sequence advances. Coalesce a busy
session to at most product frequency; slow sockets drop intermediate positions and
receive the newest, never build an unbounded queue. Control/revocation messages outrank
position data.

For large public-event sharing, use a separate broadcast product with stronger consent,
aggregation/delay and CDN/event fan-out; do not let one personal session have millions
of viewers. Apply per-session/owner/viewer gateway quotas.

## 11. Precision and privacy transformation

Precision is enforced server-side per viewer, not only UI. Options may include exact,
rounded/coarse cell, delayed, or ETA-only. Transform before gateway payload/cache key.
Do not add naive random noise that averages away across frequent updates without a
defined privacy mechanism; coarser stable cell/delay may be clearer.

Viewer cannot request higher precision than owner/session/relationship allows. Changing
precision increments ACL version and reconnects streams. Derived address/place/route
data follows the same access and retention policy as coordinates.

## 12. Revocation and expiry correctness

```text
function revokeViewer(owner, sessionId, viewerId, expectedVersion):
    transaction:
        session = sessions.getForUpdate(sessionId)
        require session.ownerId == owner.id and session.version == expectedVersion
        viewers.disable(sessionId, viewerId)
        session.aclVersion += 1; session.version += 1
        revocations.upsert(session.id, session.aclVersion, now)
        outbox.insert(ShareAclChanged(session.id, session.aclVersion))
    gatewayControl.disconnect(sessionId, viewerId, newAclVersion)
```

Every position event carries ACL version but gateway also checks current revocation
watermark; an old queued event/token cannot pass after version advance. Expiry workers
use durable buckets and conditionally expire only if stored time/version still matches.
A sweeper finds overdue ACTIVE sessions. Purge is idempotent and tracked to completion.

## 13. Reconnect, offline, and staleness

Viewer first reads latest with strong/version-validated authorization, records sequence,
then connects; gateway sends a snapshot if an event raced the join. Events below current
sequence are ignored. On stream gap/disconnect, fetch latest and display last update age.

Owner may batch offline points only while the session was active and within a short
allowed lateness. A late historical point must not replace a newer latest sequence.
If session expired/revoked before upload, reject and delete local batch per policy.

## 14. Location quality and abuse

Validate coordinate/accuracy/time, impossible speeds/teleports, mock-location/device
integrity, sensor/network consistency and repeated scripted paths. Low-confidence data
can be labeled rather than rejected for ordinary social sharing; safety/regulated uses
need stronger policy. Never silently “correct” a real user to a different location.

GPS jitter while stationary is smoothed with accuracy-aware filter/deadband; report
accuracy circle. Map matching is optional and should not place a pedestrian on a
nearby highway. Rate-limit spoof floods and account/link enumeration.

## 15. Partitioning and resilience

Session ID hashes to logical owner shard; latest KV/pubsub partitions by session.
Replicate session/ACL and latest across zones, with one fenced lifecycle writer. Route
viewer to nearest gateway while authorizing against regional version cache plus rapid
revocation stream. If cache version is uncertain, fail closed or strong-read.

During pub/sub failure, latest ingest/read continues and viewers poll/reconnect. During
latest-store failure, stop ACKing unsafe writes or buffer durably with clear staleness;
never fabricate movement. Region failover promotes a fenced caught-up session shard
and invalidates old device/token generations if necessary.

## 16. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Device retries/reorders points | Session/sequence CAS keeps newest once |
| Old device sends after handoff | Active device generation rejects it |
| Pub/sub drops event | Viewer sequence gap/snapshot reads latest |
| Gateway dies | Client reconnects, reauthorizes, fetches latest |
| Slow viewer | Drop intermediates and deliver newest/control events |
| Revocation races queued update | ACL watermark denies/disconnects before delivery |
| Expiry worker dies | Durable bucket replay plus overdue sweep |
| Owner network disappears | Show last location/accuracy/age, then stale/offline |
| Region partitions | Fence lifecycle writer; fail closed on uncertain authorization |

## 17. Security, safety, and privacy

Require explicit informed start, prominent active indicator, easy pause/end, bounded
default duration and periodic reminder. Authenticate owner/viewer/device; use session-
scoped short tokens, mTLS internally, encrypted storage/transport, HSM/KMS keys,
anti-replay nonce/sequence, rate limits, field-masked support tools, tamper-evident
access/ACL audit, and break-glass review.

Prevent IDOR, capability guessing/resharing, stalking/coercive sharing, account takeover,
employee lookup, token leakage in URLs/referrers/logs, spoofing, scraping, and session
existence leaks. Offer block/report/safety support and hide viewers as product policy
requires. Minimize history/log precision, enforce consent/child-safety/retention/deletion/
residency/legal hold, and publish law-enforcement/emergency access policy.

## 18. Observability

Track active sessions/viewers, start/pause/revoke/end/expiry, ingest QPS/latency,
accepted/duplicate/old/invalid/impossible updates, latest CAS failures, event-to-viewer
latency, location/ACL version skew, pubsub/gateway fan-out/coalescing/drop/reconnect,
position age/accuracy/stale duration, token/authorization/revocation propagation,
expiry/purge lag, trail bytes/TTL, battery/network estimates, abuse reports and
unauthorized attempts. Avoid raw coordinates/user IDs as metric labels/log fields.

Property tests reorder/duplicate points across device handoff and session transitions.
Race ACL changes with fan-out and assert no post-revocation delivery. Load-test high
viewer count and millions of moving/stationary sessions. Chaos tests kill gateways,
pubsub/latest/shards/expiry; privacy reconciliation proves ended/expired sessions,
tokens, latest, caches and trails are purged within policy.

## 19. Implementation path

1. **MVP:** one bounded owner-viewer session, strong ACL, sequenced latest KV, polling,
   explicit age/accuracy, end/expiry and deletion.
2. **Realtime/reliable:** WebSocket/pubsub, snapshot-gap recovery, device generations,
   durable expiry/sweeper, revocation watermark, adaptive sampling and coalescing.
3. **Scale/product:** regional gateways/shards, multi-viewer roles/precision, short
   consented trail, safe link sharing, quality/integrity, safety/support controls.
4. **Hardening:** fenced failover, privacy/child-safety/abuse lifecycle, race/property/
   load/chaos tests, purge/restore/key drills, runbooks, dashboards, and SLOs.

## 20. Final design

Keep lifecycle/ACL/device generation in a strongly consistent session shard and high-
rate latest position in a sequence-conditional KV record. Pub/sub and gateways deliver
coalesced newest values, while snapshot reads recover every gap. Short tokens bind ACL
version and precision; revocation/expiry advance a watermark that rejects old tokens,
devices, queued events and ingest immediately. Adaptive sampling balances freshness
with battery, but explicit staleness, short retention and tracked purge preserve the
central promise: only currently authorized viewers can see a bounded live share.
