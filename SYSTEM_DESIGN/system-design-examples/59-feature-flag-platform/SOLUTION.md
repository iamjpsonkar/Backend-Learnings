# Worked Solution: Feature Flag Platform

[Design brief](README.md) | [All examples](../README.md)

## Requirements and guarantees

The platform lets teams author typed flags, target users or services, perform stable percentage rollouts, distribute immutable configurations, evaluate without a network round trip, emit bounded exposure events, audit changes, and rapidly disable unsafe behavior.

Required behavior:

- boolean, string, number, and structured variations;
- environment-scoped rules, prerequisites, segments, schedules, and percentage rollout;
- server, mobile, browser, and edge SDKs with identical conformance semantics;
- approval, canary publication, rollback, and emergency kill switches;
- last-known-good behavior during control-plane or network failure;
- privacy-preserving evaluation telemetry.

Targets: local evaluation p99 below 1 ms after initialization, 99.999% evaluation availability, normal update propagation p99 below 30 seconds, emergency changes below 5 seconds for connected server SDKs, and complete auditability. The control plane is strongly consistent for authors; SDK delivery is eventually consistent and exposes its snapshot version/age.

## Capacity estimation

Assume 100,000 flags across 10,000 tenants, 10 million SDK processes, 100 configuration changes/s at peak, and billions of local evaluations/s. The service must distribute changes, not serve every evaluation. A 500 KB tenant/environment snapshot sent to one million relevant clients is 500 GB per full rollout, so publish deltas, compress, use regional relays/CDN, and force a compact full snapshot periodically. Exposure events are sampled and batched; they must not sit on the request path.

## Data model and invariants

```text
Flag(tenant, project, environment, key, type, variations,
     rules, fallthrough, off_variation, prerequisites, version)
Rule(id, priority, clauses, rollout_ranges, track_events)
Clause(attribute, operator, typed_values, negate)
Segment(id, included, excluded, rules, version)
Snapshot(tenant, environment, sequence, generated_at, expires_at,
         evaluator_version, flags, segments, checksum, signature)
Change(id, actor, reason, before_hash, after_hash, approval, timestamp)
```

Flag keys are unique within project/environment. Rule order is semantically significant and rule IDs remain stable across edits. Snapshots are immutable and sequences strictly increase per environment. A snapshot is activated only after checksum, signature, schema, and evaluator-version verification. Rollout ranges cover non-overlapping portions of `[0,100000)` and their weights sum to 100000.

## API contracts

```http
POST /v1/projects/{project}/flags
PATCH /v1/flags/{key} If-Match: <version>
POST /v1/environments/{env}/releases       # candidate version + reason
POST /v1/releases/{id}:approve
POST /v1/releases/{id}:rollback
GET  /sdk/v1/snapshot?environment=&after_sequence=
GET  /sdk/v1/stream?environment=&after_sequence=
POST /sdk/v1/events                         # batched exposures/diagnostics
```

Mutations use idempotency keys and optimistic concurrency. A release response reports validation, approvers, target rings, and immutable snapshot hash. SDK endpoints derive tenant/environment authorization from scoped credentials.

## Architecture

```text
admin/API -> validator/compiler -> approval workflow -> transactional config store
                                                       |
                                                 snapshot builder/signing
                                                       |
                                         ordered publication log/outbox
                                                       |
                                  regional relays -> CDN + streaming fan-out
                                                       |
applications -> SDK cache/evaluator <--- delta/full snapshots
       |
       +-> bounded event buffer -> telemetry ingestion -> analytics/audit

emergency service -> independently replicated signed kill-switch manifest
```

The control plane validates and compiles human-friendly rules into a canonical evaluator representation. Publication atomically stores the configuration version and outbox record. Regional relays consume ordered versions, offer streaming notification plus polling fallback, and cache signed full snapshots. SDKs evaluate entirely in process. A small independently distributed emergency manifest can force specifically registered flags to their safe variations if the normal pipeline is unhealthy.

## Rule compilation and validation

Before publication:

1. type-check every variation, comparison, and default;
2. resolve segment and prerequisite references in the same immutable release;
3. reject missing references and detect prerequisite cycles with depth-first search;
4. canonicalize strings, semantic versions, IP/CIDR values, and timestamps;
5. compile clauses into bounded operators and rollout weights into exact ranges;
6. estimate snapshot size and segment/rule evaluation cost;
7. execute cross-language golden test vectors;
8. require environment-specific approval and a nonempty reason.

Unknown attributes make a clause false; they never coerce to an empty string. Invalid context or evaluator errors return the flag's explicit safe default plus an error reason. Regex, if offered, is compiled with a safe bounded engine.

## Main evaluation logic

```text
evaluate(flag_key, context, snapshot):
  flag = snapshot.flags.get(flag_key)
  if flag == null: return caller_default, FLAG_NOT_FOUND
  if invalid_context(context): return flag.off_variation, INVALID_CONTEXT
  if emergency_manifest.forces(flag_key): return emergency_safe_value, EMERGENCY_OFF
  if !flag.enabled: return flag.off_variation, FLAG_OFF

  seen = set()
  for prereq in flag.prerequisites:
    if prereq.key in seen or !evaluate_prerequisite(prereq, context, snapshot, seen):
      return flag.off_variation, PREREQUISITE_FAILED

  for rule in flag.rules_in_priority_order:
    if all(match(clause, context, snapshot.segments) for clause in rule.clauses):
      return select_variation(rule, flag, context), RULE_MATCH(rule.id)
  return select_variation(flag.fallthrough, flag, context), FALLTHROUGH
```

Targeting attributes are typed. Segment evaluation checks explicit exclusion before inclusion, then its ordered rules. Recursion depth and total clauses are bounded even though publication already prevents cycles.

## Stable percentage rollout

```text
select_variation(allocation, flag, context):
  key = context.get(allocation.bucket_by)
  if key == null: return allocation.unbucketed_variation
  material = tenant + environment + flag.key + allocation.salt + canonical(key)
  bucket = first_64_bits(SHA256(material)) mod 100000
  return allocation.range_containing(bucket).variation
```

The subject key never leaves the process in this calculation. A stable salt preserves assignment while weights expand; changing the salt intentionally reshuffles. Different experiments use different salts so cohorts do not correlate accidentally. The published hash algorithm and canonical encoding are versioned and tested identically in every SDK.

## Step-by-step workflow

1. An authorized author changes a flag against an expected version and supplies intent and rollback behavior.
2. The compiler type-checks rules, resolves segments/prerequisites, rejects cycles, and runs golden evaluations.
3. Required approvers approve the immutable candidate; publication stores a new version and outbox event atomically.
4. The builder creates, checksums, and signs a snapshot or ordered delta, then releases it to a canary ring.
5. Regional relays fan out the sequence; an SDK downloads, verifies, persists, and atomically swaps the complete snapshot.
6. Each application request evaluates deterministically from one captured snapshot reference.
7. The SDK asynchronously records sampled exposure and diagnostic events with flag/version/variation/reason.
8. Health gates expand the release or publish a rollback; emergency policy can force a predeclared safe value.

## SDK initialization, updates, and failure semantics

On startup, an SDK loads a verified disk snapshot, then requests all versions after its sequence. Deltas contain base and target sequence; any gap or base mismatch triggers a full snapshot fetch. The SDK builds a new immutable in-memory object and swaps one pointer, so a request never observes half an update.

Streaming is an optimization: heartbeat loss triggers exponential reconnect while periodic polling continues. Server SDKs may block startup for a bounded initialization deadline; client SDKs immediately use bootstrap/default values. Every flag declares stale behavior: last-known-good indefinitely for low-risk UI, or safe-off after a maximum age for security/cost-sensitive capabilities. Expiry uses monotonic elapsed time where possible.

Snapshot signing protects integrity but client-side rules are visible to a determined browser/mobile user. Secret targeting logic and privileged decisions use a server SDK or remote evaluation service. A feature flag never replaces backend authorization.

## Exposure events

An exposure is emitted only when a flag value influences behavior, not on every internal lookup. It contains tenant/project, flag/version, variation, evaluation reason, timestamp, anonymous stable subject hash, SDK version, and an event ID. SDKs batch, compress, sample diagnostics, retain experiment exposures as required, and use a bounded queue. Failure drops telemetry rather than application traffic. Server-side deduplication uses event ID; ingestion reports sampling probabilities.

## Safe rollout and rollback

Release rings progress from internal to 1%, 10%, 50%, and 100% of SDK instances or tenants. Gates examine propagation, evaluation errors, application SLOs, and exposure balance for a minimum observation period. Rollback publishes a new higher sequence pointing to prior semantics; sequences never move backward. Kill switches have an explicit safe variation, owner, expiration/review date, drill history, and dependency analysis.

## Failure handling

- **Control-plane outage:** evaluation continues from immutable local snapshots; authors cannot make unsafe partial writes.
- **Stream/CDN outage:** SDKs reconnect, poll, and retain last-known-good according to each flag's stale policy.
- **Corrupt/badly signed snapshot:** reject it, keep the prior snapshot, and report verification failure.
- **Delta gap/out-of-order delivery:** discard deltas and fetch the referenced full sequence.
- **Bad release:** canary gates halt; rollback is a new audited version.
- **Regional relay loss:** clients fail over to another signed source without changing evaluation semantics.
- **Telemetry outage:** bounded SDK queues drop events with counters; evaluation is unaffected.
- **Clock skew:** scheduled rules use signed server activation instants plus measured offset; emergency disable is not delayed by a client schedule.
- **SDK too old:** evaluator compatibility bounds reject unsupported snapshots and force upgrade/safe behavior.

## Security and privacy

Use tenant-scoped RBAC, short-lived SDK keys restricted to one environment, mTLS for servers, encryption, hardware-backed signing keys, secret rotation, and immutable audit logs. Separate author, approver, publisher, and emergency roles. Browser/mobile credentials are public identifiers and grant read-only access only to their client-filtered snapshot.

Allowlist targeting attributes, avoid raw PII, hash subject identifiers with tenant-specific rotating keys for telemetry, enforce residency/retention, and support deletion. Sanitize flag descriptions and prevent server-only flags from entering client snapshots.

## Observability and SLOs

Measure authoring/publish failures, approval age, snapshot build/sign latency, relay sequence lag, connected SDK version/age distribution, stream reconnects, polling failures, signature/delta errors, evaluation reasons/errors/latency, fallback/default use, exposure drops, rollout allocation balance, and emergency propagation.

Synthetic SDKs in every region continuously evaluate golden contexts and report expected snapshot hashes. For a kill switch, measure the percentage of active instances acknowledging the forced version over time. Page on propagation or integrity error-budget burn, not on harmless reconnect count alone.

## Implementation path

1. Define typed flag/rule semantics and cross-language golden vectors; ship a server SDK using static signed snapshots.
2. Add versioned authoring, optimistic concurrency, audit, approval, compiler validation, and rollback.
3. Add regional polling/CDN delivery, atomic SDK caches, stale policies, and compatibility negotiation.
4. Add ordered deltas, streaming hints, gap recovery, segments, prerequisites, and stable rollouts.
5. Add bounded exposure telemetry, privacy controls, rollout rings, automated health gates, and dashboards.
6. Add and drill an independently replicated emergency manifest, regional failover, key rotation, and disaster recovery.

## Final design

The control plane produces immutable, compiled, signed truth; the data plane evaluates that truth locally from an atomic last-known-good snapshot. Versioned deterministic bucketing makes rollouts stable and reproducible across SDKs. Streaming improves freshness but polling and persisted snapshots provide resilience. Explicit safe defaults, stale policies, progressive delivery, and an independently tested emergency path make flags dependable when the rest of the system is failing.
