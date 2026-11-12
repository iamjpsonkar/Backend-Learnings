# Complete Solution: Service Discovery

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Services register instances with address, zone, protocol, version, and metadata.
Clients resolve a service and watch changes. Dead instances disappear within a
bounded time; clients survive registry outages using last-known-good endpoints.

Targets: 1 million instances, 10 million clients, 99.99% read/watch availability,
registration convergence under 10 seconds, and no stale instance advertised more
than 60 seconds after sustained loss. The registry is not a general configuration
database or traffic load balancer.

## 2. Capacity estimation

With 1 million instances and a 30-second heartbeat interval:

```text
heartbeats/second = 1,000,000 / 30 ~= 33,300
```

Ten million direct watches would overwhelm a small consensus cluster. Regional
relays consume one authoritative watch and fan out snapshots/deltas. Assuming 200
bytes/instance, authoritative live state is about 200 MB before indexes/history;
watch traffic, not storage, is the main scale concern.

## 3. API and data model

```text
register(service, instance_id, address, zone, metadata, ttl)
  -> {lease_id, lease_epoch, registry_revision, renew_before}
renew(lease_id, lease_epoch) -> {expires_at, revision}
deregister(lease_id, lease_epoch)
resolve(service, constraints, min_revision?) -> snapshot
watch(service, after_revision) -> stream<delta | snapshot_required>
```

```text
Service(name, namespace, policy)
Instance(service, instance_id, address, zone, metadata,
         health, lease_id, lease_epoch, expires_at, revision)
Change(revision, operation, service, instance_id, value)
```

Revisions are globally monotonic within one registry cluster. Lease epochs fence
an old process that reconnects after its identity was reassigned.

## 4. Architecture

```text
instance agents -> regional registry quorum -> replicated change log
                            |
                            +-> regional watch relays -> client SDK caches
health probes ------------>|

client request -> SDK chooses endpoint from atomic local snapshot
```

Use a three- or five-node consensus group per failure domain for authoritative
writes. Relays are stateless/rebuildable and shield consensus nodes from millions
of connections and repeated full snapshots.

## 5. Step-by-step workflow

### Registration

1. Agent authenticates workload identity and validates the address belongs to it.
2. Registry conditionally creates `(service, instance_id)` with a new lease epoch.
3. Consensus commit assigns revision; only then does registration succeed.
4. Change enters watch log and relays publish the instance.
5. Agent renews at roughly one-third TTL with random jitter.

### Client resolution and watch

1. SDK loads persisted last-known-good snapshot on startup.
2. It connects to nearest relay and requests changes after its revision.
3. Relay returns ordered deltas or a full snapshot if history was compacted.
4. SDK validates sequence/checksum and atomically swaps immutable endpoint set.
5. Request selection filters protocol/metadata, prefers local zone, then balances.
6. Reconnect uses exponential backoff with jitter while cached endpoints continue.

### Expiration

1. Registry timing wheel identifies leases past expiry.
2. It marks instance `SUSPECT` first if policy requires failure hysteresis.
3. After grace/probe evidence, a consensus transaction removes or marks unhealthy.
4. New revision propagates to relays and clients.

## 6. Core lease logic

```text
function register(identity, request):
    authorize(identity, request.service, request.address)
    key = (request.service, request.instanceId)

    transaction:
        old = instances.get(key)
        epoch = (old?.leaseEpoch or 0) + 1
        leaseId = secureRandomId()
        value = Instance(request..., leaseId, epoch,
                         expiresAt=serverNow()+request.ttl)
        revision = consensus.append(PUT, key, value)
    return leaseId, epoch, revision

function renew(leaseId, epoch):
    transaction:
        instance = leaseIndex.get(leaseId)
        if missing or instance.leaseEpoch != epoch:
            return LeaseLost
        instance.expiresAt = serverNow() + instance.ttl
        // Coalesce renewals; publish only material endpoint/health changes.
        instances.updateExpiry(instance)
    return instance.expiresAt

function expire(candidate, now):
    transaction:
        current = instances.get(candidate.key)
        if current.leaseId != candidate.leaseId: return
        if current.expiresAt > now: return
        revision = consensus.append(DELETE, current.key, current.leaseEpoch)
```

Use registry server time for leases. Publishing every heartbeat as a watch change
would create needless fan-out; expiry renewal is internal unless state changes.

## 7. Client snapshot logic

```text
function applyWatchMessage(message):
    if message.type == SNAPSHOT:
        require checksum(message.instances) == message.checksum
        atomicSwap(serviceEndpoints, immutable(message.instances))
        lastRevision = message.revision
        persistAsync(lastKnownGood)
        return

    if message.revision != lastRevision + 1:
        requestFullSnapshot()
        return

    next = copy(serviceEndpoints)
    apply(next, message.operation)
    atomicSwap(serviceEndpoints, immutable(next))
    lastRevision = message.revision

function chooseEndpoint(request):
    snapshot = serviceEndpoints.get()
    eligible = filter(snapshot, request.protocol, request.metadata, healthy=true)
    local = filter(eligible, zone=request.zone)
    return powerOfTwoChoices(local if not empty else eligible)
```

Readers never lock while a snapshot changes, and one request sees one coherent
endpoint set.

## 8. Health semantics

Lease freshness proves the agent can reach registry, not that the application can
serve traffic. Combine:

- self-reported readiness for startup/drain;
- active probes from independent observers;
- passive request outcomes at load balancers;
- lease expiry for process/network loss.

Store health reason and observation time. Avoid rapid healthy/unhealthy flapping
with thresholds, but keep the total removal bound within the SLO.

## 9. Watch history and compaction

Retain a bounded revision log. A client whose revision is still retained receives
deltas. An older client receives `SNAPSHOT_REQUIRED`. Periodic snapshots make relay
restart independent of replaying the entire registry history.

Relays deduplicate identical service watches and maintain one in-memory snapshot
per service. Large services support metadata filters and pagination for initial
snapshot, while deltas remain ordered.

## 10. Failure handling

| Failure | Behavior |
| --- | --- |
| Registry follower fails | Quorum continues; replace follower from snapshot/log |
| Registry loses quorum | Authoritative writes stop; relays/clients serve stale-labeled last-known-good |
| Relay fails | Clients reconnect with jitter to another relay and resume revision |
| Client misses deltas | Revision gap triggers a complete snapshot |
| Network partition isolates instance | Lease expires on quorum side; stale process epoch is fenced on reconnect |
| Bad health probe rollout | Canary policy and last-known-good rollback prevent mass removal |
| Mass reconnect | Backoff/jitter, relay admission, snapshot CDN/compression, and stale cache protect registry |
| Zone failure | Clients select healthy other-zone endpoints if service policy/capacity permits |

## 11. Security

- Mutual workload identity for registration, renewal, relay, and watch access.
- Namespace/service ACLs; an instance can register only addresses it owns.
- Validate metadata size/schema to prevent registry memory abuse.
- Encrypt transport/state and audit registration, deregistration, policy, and
  administrative overrides.
- Do not expose private topology to unauthorized clients.
- Rate-limit registrations/watches and cap instances per tenant/service.

## 12. Observability

Measure quorum/leader health, commit latency, registrations and expirations,
heartbeat rejection, instances by health, revision rate, watch connections,
relay fan-out and memory, snapshot size/time, client revision lag, stale-cache age,
reconnect storms, flapping endpoints, and time from failure to client removal.

Synthetic tests register an endpoint, observe it from multiple zones, stop renewals,
verify bounded removal, restart relay/client from old revisions, and exercise quorum
loss while real requests continue from cached endpoints.

## 13. Implementation path

1. **Prefer platform discovery:** DNS/Kubernetes/cloud discovery when it satisfies
   metadata and convergence requirements.
2. **Registry MVP:** consensus store, leases, server time, resolve API, ACLs, and a
   client cache.
3. **Scale watches:** regional relays, immutable snapshots, revisioned deltas,
   compaction, jittered reconnect, and last-known-good persistence.
4. **Operational maturity:** independent health signals, drain states, zone-aware
   selection, quotas, chaos tests, and regional recovery drills.

## 14. Final design

Use a small consensus-backed authoritative registry with lease epochs and a
revisioned change log, protected by regional fan-out relays and atomic client-side
snapshots. The core invariant is that only the current lease epoch may advertise
an instance identity, and clients apply a gap-free revision sequence or replace it
with a verified full snapshot. During control-plane failure, stale but known
endpoints are safer than an empty result.
