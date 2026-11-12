# Complete Solution: Configuration Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Author, validate, approve, version, distribute, canary, roll back, and audit dynamic
application configuration. Clients must keep operating when the control plane is
down and must never activate a partial or invalid snapshot.

Target 10 million client processes, 10 thousand updates/day, propagation to a
canary in under 10 seconds and globally in under 5 minutes, plus 99.99% read/
distribution availability. Secrets are referenced but stored in a separate secret
manager.

## 2. Capacity estimation

Assume each client watches 20 scoped keys and a compiled snapshot averages 100 KB.
A synchronized reconnect would imply 1 PB of transfer, so clients use regional
relays/CDN, conditional fetches, compression, and jitter. Updates are infrequent;
fan-out and safe rollout dominate storage and write throughput.

```text
10M clients / 20 regions = 500K clients/region
one 100 KB full refresh  = 50 TB/region without caching/compression
```

Relays cache each distinct scope snapshot once and fan it to many clients.

## 3. API and model

```text
createDraft(scope, base_version, changes) -> draft_id
validate(draft_id) -> diagnostics
approve(draft_id, approver, signature)
startRollout(draft_id, strategy) -> rollout_id
pause | resume | rollback(rollout_id)
getSnapshot(scope, version?) -> signed snapshot
watch(scope, after_version) -> stream<version notification>
```

```text
ConfigKey(scope, key, schema_id, sensitivity, owner)
ConfigVersion(scope, version, parent, values_blob, checksum,
              author, created_at, validation_result)
Approval(version, principal, decision, timestamp)
Rollout(id, version, cohorts, current_stage, state, guardrails)
ClientReport(scope, instance, active_version, status, observed_at)
AuditEvent(actor, action, target, diff_hash, time)
```

Versions and snapshots are immutable. Rollback selects an older known version by
creating a new rollout; history is never rewritten.

## 4. Architecture

```text
admin/CI -> authoring API -> validator/policy -> version DB + blob store
                                  |
                             approval service
                                  |
                           rollout controller
                                  |
                     regional relays/CDN + watch stream
                                  |
                         client SDK local cache

health/metrics -> guardrail evaluator -> advance, pause, or rollback
```

The authoring/control plane and serving relays are isolated. Clients evaluate and
cache locally; no request-time application path calls the configuration service.

## 5. Step-by-step workflow

### Author and publish

1. Author reads current version and creates a draft against that exact base.
2. Validator checks schema, types, ranges, unknown keys, cross-key dependencies,
   policy, ownership, and secret references.
3. System renders a human-readable diff and computes immutable checksum.
4. Required owners/security approvers sign the validated version.
5. Rollout starts with internal/canary cohort selected deterministically.
6. Guardrails compare errors, latency, saturation, and business correctness with
   control population.
7. Controller advances through stages or pauses/rolls back.

### Client activation

1. SDK boots from a previously verified disk snapshot and safe compiled defaults.
2. It watches nearest relay with current scope/version.
3. On notification, SDK downloads full signed snapshot or verified delta.
4. It verifies signature, checksum, schema compatibility, size, and monotonic
   version/rollout eligibility.
5. SDK builds typed in-memory representation before taking any write lock.
6. One atomic pointer swap activates the complete snapshot.
7. It persists last-known-good and reports version/health asynchronously.

## 6. Snapshot format

```text
SnapshotEnvelope
  scope
  version
  parent_version
  created_at
  minimum_sdk_version
  rollout_id and cohort rule
  compressed_values
  values_checksum
  signing_key_id
  signature over all fields above
```

Canonical serialization is mandatory so signature/checksum verification is
stable across languages.

## 7. Core client logic

```text
function receiveSnapshot(envelope, client):
    if not trustStore.verify(envelope.keyId, envelope.signature,
                             canonicalBytes(envelope.withoutSignature)):
        reject("invalid signature")

    if envelope.scope != client.scope: reject("wrong scope")
    if envelope.minimumSdkVersion > client.sdkVersion: reject("SDK too old")
    if not rolloutIncludes(envelope.rolloutRule, stableClientId(client)):
        return NotEligible

    values = decompressBounded(envelope.compressedValues, MAX_SNAPSHOT_BYTES)
    if sha256(values) != envelope.valuesChecksum: reject("checksum")
    typed = schemaRegistry.parseAndValidate(values)

    current = activeSnapshot.get()
    if envelope.version <= current.version: return AlreadyCurrent

    activeSnapshot.atomicSet(typed)
    persistAtomically(envelope)       // temp file, fsync, rename
    reportAsync(ACTIVATED, envelope.version)
```

If persistence fails after memory activation, the process may use the new version
until restart, then fall back to prior disk snapshot. This is observable but safe.

## 8. Draft and publish logic

```text
function publishDraft(actor, draftId):
    draft = drafts.get(draftId)
    authorize(actor, "publish", draft.scope)
    require draft.baseVersion == versions.current(draft.scope)

    merged = applyPatch(draft.baseValues, draft.changes)
    diagnostics = validators.runAll(merged, draft.scope)
    require diagnostics.hasNoErrors()
    require approvals.satisfyPolicy(draft, diagnostics)

    transaction:
        version = versions.next(draft.scope)
        blob = immutableBlobStore.putIfAbsent(checksum(merged), merged)
        versions.insert(version, parent=draft.baseVersion, blob=blob,
                        author=actor, checksum=checksum(merged))
        audit.insert(PUBLISHED, actor, version, diffHash(draft))
    return version
```

Optimistic base-version comparison prevents silently overwriting a concurrent
change. The author rebases and revalidates instead.

## 9. Deterministic rollout

```text
function rolloutIncludes(rule, stableId):
    bucket = unsignedHash(rule.salt + stableId) mod 10_000
    return bucket < rule.basisPoints
```

The same client stays in its cohort as percentage expands. Change salt only when a
new independent allocation is intended. Stages might be 0.1%, 1%, 10%, 50%, 100%
with minimum observation time and sample size.

## 10. Configuration precedence

If hierarchical scopes are required, define one unambiguous order, for example:

```text
compiled default < global < environment < region < service < instance override
```

The server compiles the effective snapshot and records source provenance per key.
Clients should not independently merge changing layers; otherwise clients can
observe layer versions that were never validated together.

## 11. Secrets

Configuration contains a secret reference and optional required version, never the
secret value. SDK separately authenticates to a secret manager, obtains short-lived
material, and rotates it. Logs, diffs, snapshots, CDN, and audit UI therefore do
not leak secrets.

## 12. Failure handling

| Failure | Behavior |
| --- | --- |
| Authoring DB unavailable | Publishing stops; clients continue active snapshots |
| Watch/control plane unavailable | SDK uses last-known-good and polls with jitter |
| Relay failure | Clients reconnect to another relay/CDN using conditional version |
| Invalid/corrupt snapshot | SDK rejects before activation and reports reason |
| Bad but valid configuration | Canary guardrail pauses/rolls back to known version |
| Mass reconnect | Exponential jitter, CDN/relay cache, conditional fetch, admission |
| Signing key compromise | Revoke key, publish trust update through independent root, rotate snapshots |
| Client too old | It rejects incompatible version and remains on last-known-good |

## 13. Security and governance

- SSO/workload identity, scope RBAC, and owner-based permissions.
- Two-person approval for authentication, networking, data-loss, and kill-switch
  configuration.
- Signed immutable snapshots and tamper-evident audit retention.
- Separate break-glass path with strong authentication, short expiry, and review.
- Bounds on snapshot/key/value size and decompression.
- No secrets or sensitive customer data in ordinary configuration.
- Periodic removal of stale instance overrides and unused keys.

## 14. Observability

Measure draft/validation/approval latency, publish failures, active rollout stage,
guardrail metrics, versions by client cohort/region/SDK, propagation p50/p99,
stale-client age, snapshot bytes/cache hit, watch reconnects, validation/signature
rejections, rollback rate, last-known-good fallback, and audit completeness.

Synthetic tests publish a harmless canary key, verify deterministic cohort and
multi-region propagation, force rollback, disconnect the control plane, restart a
client from disk, and confirm safe operation.

## 15. Implementation path

1. **MVP:** typed versioned files deployed with applications; schemas and review.
2. **Dynamic serving:** immutable version store, polling SDK, checksum, atomic swap,
   disk last-known-good, RBAC, and audit.
3. **Safe rollout:** approvals, deterministic cohorts, health guardrails, rollback,
   compatibility rules, and signed snapshots.
4. **Fleet scale:** regional relays/CDN, watch notifications, reconnect controls,
   hierarchical compilation, disaster tests, and key rotation.

## 16. Final design

Use a strongly audited authoring plane that produces immutable, signed, fully
compiled snapshots; a staged rollout controller; regional cached distribution;
and SDKs that verify, build, and atomically activate snapshots while preserving
last-known-good state. The central invariant is that a client runs either the old
complete valid version or the new complete valid version—never a partial merge.
