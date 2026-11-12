# Complete Solution: Package Tracking

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Create/import shipments, ingest carrier webhooks/files/polls and internal scans, retain
raw evidence, normalize carrier-specific events, derive a customer-safe timeline/current
state, estimate delivery, expose authenticated/public tracking, notify meaningful
changes, handle exceptions/corrections and reconcile stale/missing carrier data.

Targets: event acceptance p99 below 300 ms, tracking read p99 below 200 ms, 99.99% reads,
99% of webhook events visible below one minute, clear source freshness, and no loss
after source ACK. Delivery is at least once and events are late/out of order. Immutable
raw events plus deterministic versioned projection permit replay; current state never
regresses merely because an old scan arrives.

## 2. Capacity estimation

Assume one billion shipments/year, 30 events/shipment, 20 tracking reads/shipment,
2 KB raw event, 500-byte normalized event, five notifications/shipment, and 10x
holiday/batch peaks.

- 30 billion events/year average about 950/s but holiday files/webhooks can exceed
  tens of thousands/s.
- Raw events add about 60 TB/year before replication; normalized events 15 TB/year.
- Reads average about 630/s over a year but customer campaigns/delivery days are bursty;
  current projections/cache make them cheap.
- Polling millions of active shipments must adapt to carrier limits/milestones. Webhook
  first, poll only where needed, and coalesce by carrier account.
- Tracking numbers may be reused, so carrier + account/service + number + shipment
  generation/time window—not number alone—defines identity.

## 3. APIs and integrations

```text
POST /v1/shipments                         Idempotency-Key
GET  /v1/shipments/{shipmentId}
GET  /v1/shipments/{shipmentId}/events?cursor=
GET  /v1/public-tracking/{capabilityToken}
POST /v1/shipments/{id}/subscriptions      Idempotency-Key
POST /v1/carriers/{carrier}/webhooks       signed carrier event
POST /v1/carriers/{carrier}/files          signed manifest/object reference
POST /v1/internal-scans                    device/site authenticated batch
POST /v1/shipments/{id}/refresh            Idempotency-Key
```

Bound batch/file/payload size, tracking identifiers, date range, poll/refresh rate,
subscriptions and cursor depth. Provider callbacks use mTLS/signature/timestamp/replay
checks. Public token reveals only approved status/detail and expires/revokes.

## 4. Canonical identity and data model

```text
Shipment(id, tenant_id, order_ref, carrier_id, carrier_account_id,
         tracking_number_ciphertext, generation, service, origin, destination,
         state, state_version, projection_version, source_freshness,
         promised_window, estimated_window, delivered_at, created_at)
RawEvent(id, source, source_event_id, received_at, raw_ref, payload_hash,
         schema_hint, verification_state, processing_state)
NormalizedEvent(id, shipment_id, raw_event_id, canonical_type, subtype,
                event_time, receive_time, location, source_sequence,
                source_version, confidence, attributes, normalizer_version)
TimelineEvent(shipment_id, display_sequence, normalized_event_id,
              public_type, public_text_key, state_effect, visibility)
Projection(shipment_id, source_watermark, state, current_location,
           estimated_window, exception, last_event_at, version)
PollTask(shipment_id, carrier_id, next_poll_at, attempt, lease_until, state)
NotificationIntent(shipment_id, transition_key, recipient, channel, state)
Inbox(source, source_event_id, payload_hash, processed_at)
Outbox(id, aggregate_id, version, event_type, payload, published_at)
```

Address/contact/customs data is encrypted and excluded from public projection. Retain
the original carrier code/message attributes even when mapped to a broad canonical type.

## 5. Canonical state model

```text
LABEL_CREATED -> CARRIER_ACCEPTED -> IN_TRANSIT -> OUT_FOR_DELIVERY -> DELIVERED
                        |              |                 |
                        +-> EXCEPTION <-+-----------------+
EXCEPTION -> IN_TRANSIT / OUT_FOR_DELIVERY / DELIVERED / RETURN_TO_SENDER / LOST
CANCELLED applies only before carrier acceptance under policy
```

This is a customer abstraction, not a destructive replacement for carrier nuance.
Canonical events include `PICKED_UP`, `DEPARTED_FACILITY`, `ARRIVED_FACILITY`,
`CUSTOMS_PENDING/CLEARED`, `DELIVERY_ATTEMPTED`, `ADDRESS_ISSUE`, `AVAILABLE_FOR_PICKUP`,
`RETURN_STARTED`, `DAMAGED`, `LOST`, `DELIVERED`, and correction/void events.

## 6. Architecture

```text
carrier webhook/file/poll/internal scan -> adapter ingress/verification
                                             |
                                  raw immutable object + inbox/log
                                             |
                                carrier-version normalizers
                                             |
                               shipment-partitioned event stream
                                  /            |           \
                           state/timeline    ETA model    quality/reconciliation
                                |               |
                         projection store/cache -> tracking APIs
                                |
                         outbox -> notification delivery

adaptive poll scheduler -> carrier rate-limit/fair adapter -> same raw ingress
```

Partition canonical events/processors by shipment ID to make deterministic fold local.
Carrier adapters have isolated credentials, parsers, rate limits, circuits and queues.
Raw data is persisted before acknowledging webhook/file acceptance.

## 7. Step-by-step workflow

1. Create shipment with carrier/account/tracking/generation/order mapping and source
   policy; schedule initial poll/webhook registration where applicable.
2. Ingress verifies source, stores raw bytes/checksum/metadata immutably and inserts
   unique inbox/source ID before quick ACK. Duplicate same hash is no-op; conflicting
   reuse is quarantined.
3. Versioned carrier adapter parses timestamps/time zones/codes/location/reference and
   resolves exactly one shipment generation or sends ambiguity to reconciliation.
4. Emit canonical normalized event keyed by shipment. Stateful processor deduplicates,
   orders/evaluates evidence, appends timeline and conditionally advances/corrects
   current state under explicit precedence rules.
5. ETA worker uses route/milestones/service/calendar/carrier history/exceptions to
   update a delivery interval and confidence. Projection/outbox commits version.
6. Notification planner compares meaningful transition keys/preferences and creates
   one intent; delivery retries independently.
7. Adaptive scheduler stops or slows polls at terminal state, backs off unchanged/
   failing sources, and reconciliation finds stale/missing/contradictory shipments.

## 8. Ingress deduplication logic

```text
function acceptCarrierEvent(carrier, headers, rawBody):
    verifyCarrierSignatureTimestampAndAccount(carrier, headers, rawBody)
    sourceId = adapter(carrier, headers.schemaVersion).extractEventId(rawBody)
               ?? deterministicHashOfCanonicalRawEnvelope(rawBody)
    payloadHash = sha256(rawBody)
    rawRef = rawStore.putByChecksumEncrypted(rawBody)

    transaction:
        prior = inbox.get(carrier.account, sourceId)
        if prior exists:
            if prior.payloadHash != payloadHash: quarantineConflict()
            return ACCEPTED_DUPLICATE
        raw = rawEvents.insert(carrier, sourceId, rawRef, payloadHash, VERIFIED)
        inbox.insert(carrier.account, sourceId, payloadHash, raw.id)
        outbox.insert(RawCarrierEventAccepted(raw.id))
    return ACCEPTED
```

If a carrier provides no stable ID, deterministic fallback may collapse identical raw
events but cannot guarantee semantic identity; normalization also deduplicates by a
canonical fingerprint with careful correction/version handling.

## 9. Normalization and shipment resolution

```text
function normalize(raw, adapterVersion):
    decoded = sandboxedAdapter(adapterVersion).parse(raw.verifiedBytes)
    require valid tracking, type, timestamp range and bounded attributes
    candidates = shipmentDirectory.lookup(decoded.carrierAccount,
                                          decoded.trackingNumber)
    candidates = candidates.filter(service/date/reference compatibility)
    if candidates.size != 1: quarantine AMBIGUOUS_SHIPMENT
    shipment = candidates[0]
    instant = resolveCarrierLocalTimestamp(decoded.time, decoded.locationTimezone,
                                            decoded.offset, adapterPolicy)
    return NormalizedEvent(
      stableId(raw.id, adapterVersion), shipment.id,
      mapCarrierCode(decoded.code), decoded.subtype, instant,
      decoded.location, decoded.sourceSequence, decoded.sourceVersion,
      confidence(decoded), preserveAllowlistedAttributes(decoded), adapterVersion)
```

Do not guess a timezone silently when a carrier omits it; use documented facility/
carrier policy and mark confidence. Retaining raw enables reparse after adapter fixes.

## 10. Deterministic timeline and state fold

Event time alone is insufficient: a late delivery scan can arrive before an earlier
facility scan, clocks can be wrong, and carriers issue corrections. Define precedence,
terminal evidence and source versions.

```text
function applyEvent(projection, event):
    if seen normalized ID or semanticFingerprint with same sourceVersion: return
    timeline.append(event)  // immutable even if it does not change current state

    if event explicitlyVoidsOrCorrects(priorEvent):
        mark prior evidence corrected; rebuild affected fold window
    else if event.sourceVersion older than applied version for same carrier event:
        ignore for state, retain in timeline/audit
    else if validTransition(projection.state, event.canonicalType):
        projection.state = transition(projection.state, event)
        projection.currentLocation = locationIfNewerMeaningful(event)
    else if terminalEvidenceDominates(event, projection):
        projection.state = terminalState(event)
    else:
        flag conflict; keep state until higher-confidence evidence/reconciliation

    projection.lastEventAt = max(projection.lastEventAt, event.eventTime)
    projection.version += 1
    emit ProjectionChanged only if customer-meaningful fields changed
```

Display timeline may sort by event time plus carrier/source sequence and mark corrected
events. Current state uses rule version and evidence confidence, not naive maximum enum.

## 11. Example transition rules

- `DELIVERED` from authenticated carrier proof is terminal unless an explicit higher-
  version correction/return/dispute event arrives.
- Late `ARRIVED_FACILITY` before delivered is inserted chronologically but does not
  regress current state.
- `DELIVERY_ATTEMPTED` after `OUT_FOR_DELIVERY` creates exception/next action; a later
  `IN_TRANSIT` may represent return to depot and is allowed with subtype.
- `CUSTOMS_PENDING` is a parallel exception/milestone, not necessarily global state;
  model facets when one enum loses important meaning.
- A reused tracking number cannot attach to a terminal old generation outside its
  shipment/reference/time window.

## 12. Adaptive polling

Prefer webhooks/push, but poll carriers lacking reliable push or to repair gaps:

```text
function nextPoll(shipment, result):
    if shipment.terminal: return NONE after final verification window
    interval = byMilestone(shipment.state)  // faster near expected delivery
    interval *= unchangedBackoff(result.consecutiveUnchanged)
    interval = max(interval, carrierRetryAfterOrRateLimit)
    interval /= priorityFactor(paidService, promisedDeadlineProximity)
    return now + jitter(clamp(interval, MIN, MAX))
```

Scheduler uses durable due buckets/leases and hierarchical fairness by carrier account/
tenant. Batch carrier endpoints where supported. One broken carrier backs off/circuits
without starving others; manual refresh joins same quota and cannot become a DDoS tool.

## 13. ETA model

Build a planned milestone/route from origin/destination/service, carrier network,
facility graph, pickup time, calendars/holidays/cutoffs and promised window. Update as
actual scans arrive. Features include current facility/state, remaining legs, historical
lane/carrier/service transit distributions, weekday/season, customs, exceptions,
weather/capacity where permitted and source freshness.

Return a calibrated interval and confidence, not an overprecise timestamp. Point-in-time
training joins prevent future scan leakage. Evaluate MAE/coverage/bias by carrier,
lane, service, state and horizon. On model/data failure, use carrier-provided promise
or historical rule range and mark lower confidence.

## 14. Notification idempotency

Meaningful transitions create keys such as:

```text
(shipment_id, projection_generation, public_transition,
 customer-visible_occurrence_version, recipient, channel)
```

Planner respects preference/timezone/quiet hours and suppresses noisy facility scans.
Out-for-delivery, attempted, pickup-ready, delivered, major exception and material ETA
shift may notify. Delivery uses stable ID and retries; status fetch remains authoritative.
A corrected transition can produce an explicit correction message rather than silently
deleting the first notification.

## 15. Public tracking and privacy

Tracking number alone can be guessable/reused and should not reveal recipient/address.
Use high-entropy signed capability or require authenticated order ownership; carrier-
style public lookup may require postal-code fragment/rate limits and only coarse data.
Return city/region, never exact home coordinates or full name/contact/instructions.

Capabilities bind shipment generation, permitted fields, expiry and revocation version.
Cache public projection separately from internal operational view. Access/support/
export is audited and tracking-number enumeration/credential stuffing is detected.

## 16. Exceptions and customer actions

Exceptions include weather, customs, address correction, failed attempt, damage, lost,
pickup deadline and return-to-sender. Store subtype/severity/owner/required action/SLA,
not just generic `EXCEPTION`. Customer action tokens are one-time, shipment-scoped,
expiring and validated against current carrier capabilities; changes flow through an
idempotent carrier saga and stay `PENDING` until confirmed.

Lost/damaged claims and delivery disputes retain chain-of-custody/proof under restricted
access. Refund/replacement belongs to order/claims workflows; tracking publishes their
references/status without rewriting scan history.

## 17. Rebuild and reconciliation

Rebuild projection by reading all normalized events for shipment under pinned
normalizer/state-rule versions, sorting/folding deterministically, writing a new
projection generation, comparing current state/timeline/ETA, then atomically switching.

Reconciliation checks active shipments with no event beyond state-specific threshold,
polls carrier, compares carrier current snapshot to projection, verifies raw->normalized
processing, detects tracking collisions, projection sequence gaps, terminal mismatch,
notification anomalies and order/fulfillment status disagreement. Repairs are versioned
commands/replays; contradictions open cases.

## 18. Partitioning and resilience

Partition normalized stream/state by shipment ID; directory and raw ingress by carrier
account/tracking hash. Isolate adapters/credentials/quotas per carrier. Replicate
projections regionally and cache terminal shipments longer. One shipment state owner/
processor epoch prevents competing projections; replay can rebuild after failover.

Under load, durably accept verified raw events, slow polling/bulk files, prioritize
terminal/exception scans, serve stale-labeled projection, and delay optional ETA/
notifications rather than drop scans. Raw store/log backpressure must stop ACK before loss.

## 19. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Carrier retries webhook/file row | Source ID/hash inbox accepts once |
| Adapter/parser breaks | Raw evidence retained; quarantine and replay fixed version |
| Late old scan arrives | Timeline adds it; state precedence prevents regression |
| Contradictory terminal scan | Preserve evidence and open reconciliation/correction |
| Projection processor dies | Restore checkpoint and replay shipment stream |
| Carrier API is unavailable | Back off, show source age, keep other carriers healthy |
| Notification fails | Tracking state remains correct; delivery retries |
| ETA service fails | Carrier promise/historical fallback with low confidence |
| Region fails | Serve replicated projection; resume fenced processing/replay elsewhere |

## 20. Security and compliance

Use mTLS/signatures/IP policy where useful, rotating carrier credentials in vault,
schema/parser sandboxing, object checksums, service RBAC, tenant/shipment field access,
encryption, signed public capabilities, nonce/timestamp replay controls, rate limits,
tamper-evident audit and break-glass review. Prevent forged scans/webhooks, tracking
enumeration, IDOR, malicious files/XML/CSV injection, adapter SSRF, credential leaks,
address/proof scraping, fake delivery and insider recipient lookup.

Apply postal/customs/transport/e-signature requirements, privacy minimization/consent/
retention/deletion, residency, child/sensitive-delivery protection, legal hold, claims/
dispute evidence and tested backup/key recovery. Redact carrier raw payloads from logs.

## 21. Observability

Track raw event/file/poll QPS/bytes/latency, verification/duplicate/hash conflicts,
carrier webhook and poll freshness/rate-limit/circuits, raw-to-normalized/projection lag,
adapter versions/errors/quarantine, ambiguous shipment mappings, late/out-of-order/
correction/state-conflict events, shipments/state and state age, stale sources, ETA
MAE/interval coverage/drift, tracking API/cache/auth denials, notification intents/
duplicates/delivery age, reconciliation case type/age, and processor partition lag.

Golden carrier fixtures cover each code/schema/timezone/correction/reuse case. Property-
test shuffled/duplicated events and require deterministic non-regressing fold. Replay
shadow new adapters/rules/models, load-test holiday files and failing carrier, kill
ingress/parser/processors/ETA/notifications/region, and reconcile raw, normalized,
projection, notification and carrier-current control counts.

## 22. Implementation path

1. **MVP:** few carriers, signed webhook/poll, raw retention, stable shipment identity,
   simple canonical timeline/current state, authenticated tracking and notifications.
2. **Reliable pipeline:** inbox/outbox, sandboxed versioned adapters, deterministic
   transition rules, replay/rebuild, adaptive poller, exceptions and reconciliation.
3. **Scale/quality:** carrier isolation, bulk files, regional projections/cache, ETA
   intervals/model, public capabilities, customer actions, claims/order integration.
4. **Hardening:** security/privacy/postal evidence controls, property/golden/holiday-
   load/chaos tests, adapter/restore/key drills, runbooks, dashboards, and SLOs.

## 23. Final design

Persist every authenticated carrier payload immutably before ACK, deduplicate by source
identity/hash, and normalize with a versioned isolated adapter into a shipment-keyed
event stream. A deterministic evidence-aware fold builds timeline/current state without
regressing on late scans, while preserving carrier nuance and corrections. Adaptive
polling repairs unreliable push, ETA produces calibrated windows, and versioned outbox
notifications remain separate. Raw replay and end-to-end carrier/order reconciliation
make the public status explainable and recoverable despite reused IDs, bad clocks,
duplicate files, outages and contradictory scans.
