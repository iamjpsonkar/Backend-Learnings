# Complete Solution: Presence Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Expose online, idle, offline, and last-seen state across multiple devices. Accept
heartbeats, notify authorized subscribers, honor privacy, and recover from missing
disconnects. Presence is best-effort soft state, not durable proof that a person is
actively viewing an application.

Targets: 100 million concurrent devices, transition propagation below 5 seconds
p99, stale-online state removed within 60 seconds, and graceful degradation to
`UNKNOWN`/aged last-seen during partitions.

## 2. Capacity estimation

At a 30-second heartbeat interval:

```text
heartbeats/s = 100M / 30 ~= 3.33 million
```

A 100-byte heartbeat is already about 333 MB/s before protocol overhead. Gateways
aggregate/refresh sessions locally and batch store updates. Only state transitions,
not every heartbeat, are fanned out.

## 3. State model

```text
DeviceSession(user_id, device_id, connection_id, gateway_id,
              activity=ACTIVE|IDLE, last_heartbeat, expires_at, epoch)
UserPresence(user_id, state=ONLINE|IDLE|OFFLINE|UNKNOWN,
             latest_activity, last_seen, version)
Privacy(user_id, visibility=EVERYONE|CONTACTS|NOBODY, exceptions)
Subscription(subscriber, subject_set, authorization_version)
```

User is `ONLINE` if any visible session is active, otherwise `IDLE` if any is idle,
otherwise `OFFLINE`. `last_seen` advances when the final session disappears, with
privacy-controlled granularity.

## 4. Architecture

```text
clients -> regional socket gateways -> session shards (in-memory TTL + replicas)
                    |                         |
                    |                         v
                    +----------------> user aggregator -> transition pub/sub
                                                          |
privacy/relationship service --------------------------> authorized fan-out

sampled durable last-seen store <--- aggregate transitions
```

Partition sessions and aggregation by user ID so all devices for one user share an
owner. Gateways keep connection mapping; session shards own authoritative TTL.

## 5. Step-by-step workflow

### Connect

1. Gateway authenticates user/device and creates monotonically increasing session
   epoch for that device identity.
2. It writes session with TTL and ACTIVE activity.
3. User aggregator recalculates aggregate state.
4. Only if aggregate changes does it publish versioned transition.
5. Fan-out checks privacy/relationship before notifying subscribers.

### Heartbeat and activity

1. Client sends heartbeat with connection/session epoch and optional activity.
2. Gateway rejects stale epoch and refreshes local/session-shard expiry.
3. Repeated unchanged heartbeats are coalesced; no subscriber event is emitted.
4. ACTIVE-to-IDLE transition is published only after configured inactivity.

### Disconnect/expiry

1. Graceful close attempts conditional session removal.
2. Ungraceful loss is discovered when TTL expires.
3. Aggregator removes that device and recomputes across remaining sessions.
4. When last session leaves, it records last-seen and emits OFFLINE after debounce.

## 6. Core logic

```text
function openSession(identity, connection):
    key = (identity.userId, identity.deviceId)
    epoch = sessionEpochs.increment(key)
    session = DeviceSession(key, connection.id, connection.gatewayId,
                            ACTIVE, now(), now()+TTL, epoch)
    sessionStore.put(key, session)
    recomputeUser(identity.userId)
    return epoch

function heartbeat(user, device, epoch, activity):
    sessionStore.compute((user,device), current ->
        if current missing or current.epoch != epoch: return current, STALE
        current.lastHeartbeat = now()
        current.expiresAt = now()+TTL
        current.activity = activity
        return current, OK)
    if activity materially changed: recomputeUser(user)

function expire(candidate):
    removed = sessionStore.compareAndDelete(
        candidate.key, expectedEpoch=candidate.epoch,
        condition=expiresAt <= now())
    if removed: recomputeUser(candidate.userId)
```

Epoch comparison prevents a delayed disconnect/expiry from deleting a newer
connection for the same device.

## 7. Aggregate and transition logic

```text
function recomputeUser(userId):
    sessions = sessionStore.getAllForUser(userId)
    next = deriveState(sessions)
    userPresence.compute(userId, current ->
        if equivalent(current.state, next): return current
        updated = Presence(next, latestActivity(sessions),
                           lastSeenFor(next, current), current.version+1)
        outbox.publish(PresenceChanged(userId, updated))
        return updated)
```

Debounce rapid online/offline transitions for a few seconds, but keep total stale
bound under SLO. Subscribers apply only transitions with a newer version.

## 8. Authorized fan-out

Do not precompute every follower subscription for celebrity users. Use:

- direct push for small contact sets and active chat participants;
- query-on-read or sampled/coarse presence for massive audiences;
- subscription caps and short-lived room/conversation subscriptions;
- privacy cache with version and deny-by-default on uncertainty.

```text
function visiblePresence(viewer, subject):
    policy = privacy.get(subject)
    if not policy.allows(viewer, relationship(viewer,subject)):
        return HIDDEN
    presence = userPresence.get(subject)
    return reducePrecisionIfRequired(presence, policy)
```

## 9. Last-seen semantics

Last-seen is durable at much lower write rate than heartbeat. Persist only when the
aggregate user becomes offline, and coalesce frequent reconnects. Privacy may show
exact time, coarse ranges such as “today,” or nothing. Never derive sensitive
activity history from raw session logs beyond retention needs.

## 10. Multi-region behavior

Route each user to a home aggregation shard while gateways may be regional. A
device move creates new epoch before old connection expires, preventing false
offline. Replicate aggregate transitions regionally. During home-shard partition,
show cached state with age or `UNKNOWN` rather than asserting online indefinitely.

## 11. Failure handling

| Failure | Behavior |
| --- | --- |
| Gateway crashes | Sessions expire by TTL; clients reconnect with newer epochs |
| Heartbeat lost | One loss is tolerated; repeated loss reaches TTL and offline |
| Session shard fails | Replica takes ownership; TTL wheel rebuilds from expiry timestamps |
| Aggregator event duplicated | Versioned atomic recomputation makes it idempotent |
| Pub/sub/fan-out fails | Current state remains queryable; transition can replay |
| Privacy service unavailable | Use validated cache; otherwise hide/deny presence |
| Region partition | Show aged cached or UNKNOWN; reconcile newer epochs on recovery |
| Reconnect storm | Jitter, gateway admission, batched heartbeats, and fan-out debounce |

## 12. Security and privacy

- Authenticated device/session epochs and encrypted transport.
- Relationship/privacy authorization on subscriptions and point reads.
- Rate limits on watched subjects and heartbeat frequency.
- Minimize/raw-session retention; encrypt last-seen and restrict employee access.
- Do not leak blocked users through timing, errors, or aggregate room presence.
- Audit privacy changes and privileged queries.
- Allow invisible mode that suppresses outgoing presence while preserving local
  connection operation.

## 13. Observability

Measure concurrent sessions, heartbeat QPS/latency/drop, expiry delay, reconnects,
aggregate transition latency, fan-out backlog, duplicate/stale epochs, flapping,
privacy denials/cache age, subscriber counts, hot users, session memory, and state
age observed by clients.

Synthetic tests connect two devices, idle one, kill a gateway, reconnect during
expiry, change privacy, partition pub/sub, and verify monotonic versioned state.

## 14. Implementation path

1. **MVP:** gateway-local online status plus TTL and point query.
2. **Distributed sessions:** user-sharded replicated TTL store, epochs, multi-device
   aggregation, durable last-seen, and reconnect handling.
3. **Realtime fan-out:** versioned transitions, conversation/contact subscriptions,
   privacy enforcement, debounce, and overload controls.
4. **Global scale:** home aggregation, regional replicas, celebrity strategy,
   UNKNOWN semantics, privacy audits, and failure drills.

## 15. Final design

Use user-partitioned expiring device sessions, epoch-fenced updates, derived
multi-device aggregate state, and versioned privacy-authorized transition fan-out.
The core invariant is that an old session event can never remove or overwrite a
newer device epoch. Presence remains explicitly soft state: when freshness cannot
be proven, the system reports age or UNKNOWN instead of false certainty.
