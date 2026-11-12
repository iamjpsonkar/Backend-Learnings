# Complete Solution: Payment Gateway

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements and guarantees

Merchants create payment intents, tokenize payment methods, authenticate customers,
authorize, capture partially/fully, void, refund, query status, and receive signed
events. The gateway performs risk/limits, routes to capable processors, normalizes
callbacks, records financial effects in a double-entry ledger, and reconciles provider
settlement data.

Targets: 100 million payments/day with 10x peaks, gateway-added p99 below 300 ms and
end-to-end authorization p99 below two seconds when providers respond, 99.99% status
reads, 99.95% command availability, and zero duplicate ledger effects. A timeout is
`UNKNOWN`, not decline. API delivery is at least once; idempotency and reconciliation
provide effectively-once business effects.

## 2. Capacity estimation

At 100 million payments/day, average intent rate is about 1,160/s and campaign peak
about 12,000/s. Suppose each payment creates five state/audit events and three status
reads:

- events average 5,800/s and peak near 60,000/s;
- status reads average 3,500/s and peak near 35,000/s;
- at 3 KB intent/attempt/event metadata, hot operational growth is hundreds of
  GB/day before indexes, replicas, raw callback evidence, and ledger;
- retain idempotency keys beyond merchant/provider retry windows, and financial/audit
  records for mandated years in tiered verified storage;
- callbacks and settlement files are bursty, so isolate their queues from interactive
  authorization capacity.

## 3. API and contract

```text
POST /v1/payment-intents                 Idempotency-Key
POST /v1/payment-intents/{id}/confirm    Idempotency-Key
POST /v1/payment-intents/{id}/capture    {amount} Idempotency-Key
POST /v1/payment-intents/{id}/cancel     Idempotency-Key
POST /v1/refunds                         {intentId, amount, reason} Idempotency-Key
GET  /v1/payment-intents/{id}
GET  /v1/refunds/{id}
POST /v1/payment-method-tokens           PCI-hosted/client-encrypted payload
POST /v1/webhook-endpoints
```

Money uses integer minor units plus ISO currency and currency-specific scale; never
binary floats. A merchant-scoped idempotency key binds the canonical request hash and
returns the original response; reuse with different parameters is an error. Client
secrets expose only narrow intent operations and expire.

## 4. State and accounting invariants

```text
Intent: REQUIRES_METHOD -> REQUIRES_CONFIRMATION -> PROCESSING
          -> REQUIRES_ACTION -> PROCESSING
          -> AUTHORIZED -> PARTIALLY_CAPTURED -> CAPTURED
          -> CANCELLED | FAILED

Attempt: CREATED -> SENT -> SUCCEEDED | DECLINED | UNKNOWN | ERROR
Refund:  CREATED -> PROCESSING -> SUCCEEDED | FAILED | UNKNOWN
```

Invariants:

- authorized, captured, voided, and refunded amounts are nonnegative and bounded;
- total captures never exceed authorization, total refunds never exceed captures;
- one provider operation maps to one stable external request/reference;
- provider success posts one uniquely referenced ledger transaction;
- only verified evidence (synchronous response, callback, status query, settlement)
  resolves `UNKNOWN`;
- state never moves backward from an older callback.

## 5. Data model

```text
PaymentIntent(id, merchant_id, amount, currency, state, payment_method_token,
              authorized_amount, captured_amount, refunded_amount,
              customer_ref, order_ref, version, created_at)
PaymentAttempt(id, intent_id, operation, generation, processor, external_request_id,
               external_payment_id, amount, state, decline_code,
               request_ref, response_ref, version, started_at, resolved_at)
CustomerAction(id, attempt_id, type, redirect_or_sdk_token, expires_at, state)
Refund(id, intent_id, amount, state, version, reason, created_at)
Idempotency(merchant_id, endpoint, key, request_hash, resource_id,
            response_ref, state, expires_at)
Inbox(processor, provider_event_id, payload_hash, verified_at, processed_at)
Outbox(id, aggregate_id, sequence, event_type, payload, published_at)
LedgerLink(effect_type, resource_id, effect_generation, ledger_tx_id, amount)
ReconciliationCase(id, processor, external_ref, internal_ref, type, state, evidence)
```

Raw processor requests/responses/callbacks are encrypted evidence with redaction and
restricted retention. The token vault maps opaque tokens to payment credentials in
a separately isolated PCI environment.

## 6. Architecture

```text
merchant -> API/auth/idempotency -> intent service/state machine -> durable SQL/outbox
                                              |       |        |
                                         risk/limits router  workflow/timers
                                              |       |
client -> hosted fields -> PCI token vault    |   processor adapters -> providers
                                                      ^              |
callbacks -> edge signature/raw store -> verified inbox -------------+

outbox -> merchant webhooks + ledger posting + analytics
settlement/status feeds -> reconciliation -> cases/corrective commands
```

Keep adapters isolated by provider and version so their odd semantics do not leak
into the canonical state machine. The router chooses only before an attempt is sent;
an ambiguous attempt pins the operation to that provider until resolved.

## 7. Step-by-step workflow

1. Merchant creates an idempotent intent with exact amount/currency/order reference.
   Gateway stores it and returns an ID/client secret.
2. Hosted fields or client-side encryption sends credentials directly to PCI vault;
   merchant receives a scoped token, not card/account data.
3. Confirm checks merchant/intent state, velocity/risk, payment-method capability,
   sanctions/limits where applicable, and customer authentication requirements.
4. Router selects processor by method/currency/region/cost/health/success while honoring
   sticky routing and compliance. Before network I/O, persist attempt and stable
   external request ID.
5. Adapter sends authorize. A definitive signed response transitions intent; a 3DS/
   equivalent challenge returns `REQUIRES_ACTION`; timeout/reset becomes `UNKNOWN`.
6. Verified callback/status query resolves the same attempt. Success posts one ledger
   effect and outbox event. Capture/refund follow separate idempotent operations.
7. Reconciliation compares provider status/settlement with attempts and ledger, opening
   cases and executing approved correction commands.

## 8. Idempotent intent creation

```text
function createIntent(merchant, command, key):
    require validMoney(command.amount, command.currency)
    requestHash = canonicalHash(command)
    transaction:
        prior = idempotency.get(merchant.id, "create-intent", key)
        if prior exists:
            require prior.requestHash == requestHash
            return prior.response

        require merchantLimitsAllow(command)
        intent = intents.insert(newId(), merchant.id, command,
                                state=REQUIRES_METHOD, version=1)
        event = appendIntentEvent(intent, CREATED)
        outbox.insert(event)
        response = publicView(intent)
        idempotency.insert(merchant.id, endpoint, key, requestHash,
                           intent.id, response, IDEMPOTENCY_TTL)
    return response
```

Create and idempotency record share a unique transactional boundary. If a client
times out after commit, retry returns the same intent rather than charging again.

## 9. Core provider attempt logic

```text
function beginOperation(intentId, operation, amount, commandKey):
    transaction:
        intent = intents.getForUpdate(intentId)
        return prior command result if present
        require stateMachine.allows(intent, operation, amount)
        route = router.choose(intent, operation, healthSnapshot)
        generation = nextGeneration(intent, operation)
        externalRequestId = stableId(intent.id, operation, generation)
        attempt = attempts.insert(intent.id, operation, generation, route,
                                  externalRequestId, amount, CREATED)
        intent.state = PROCESSING; intent.version += 1
        append event/outbox and command result

    result = adapter(route).send(operation, intent, attempt,
                                 idempotency=externalRequestId)
    return recordSynchronousResult(attempt.id, result)

function recordSynchronousResult(attemptId, result):
    if result.isDefinitiveAndAuthentic:
        return resolveAttempt(attemptId, normalize(result))
    else:
        markAttemptUnknown(attemptId, evidence=result.transportEvidence)
        scheduleStatusQuery(attemptId)
        return PROCESSING
```

The database transaction completes before calling the provider. Retrying the send
uses the same provider idempotency/reference. If the provider lacks idempotency, query
by merchant reference before any retry and accept higher operational risk explicitly.

## 10. Resolving callbacks and out-of-order events

```text
function handleProviderCallback(provider, headers, rawBody):
    verifySignatureTimestampAndEndpoint(provider, headers, rawBody)
    event = parseWithVersionedAdapter(provider, rawBody)
    transaction:
        prior = inbox.get(provider, event.id)
        if prior exists:
            require prior.payloadHash == hash(rawBody); return ACK
        attempt = attempts.getByExternalReferenceForUpdate(provider, event.reference)
        require attempt exists and event.matchesMoneyAndMerchant(attempt)
        inbox.insert(provider, event.id, hash(rawBody), verified=true)
        if evidenceIsNewerAndTransitionAllowed(attempt, event):
            resolveAttemptAndIntent(attempt, event)
            append event/outbox
        mark inbox processed
    return ACK
```

Respond quickly after durable processing/acceptance. Duplicate callbacks are normal.
An older “authorized” callback cannot undo capture/refund; a contradictory event
opens reconciliation instead of guessing.

## 11. Authorization, capture, void, and refund

Authorization reserves payer funds but is not settlement. Store expiry and capture
rules. Capture command conditionally claims remaining authorized amount, creates a
stable provider operation, and only increments `captured_amount` from proven success.
Partial/multiple capture support is processor/method-dependent.

Void releases uncaptured authorization. Refund references captured payment, validates
cumulative amount and currency, and has its own state/attempt. A refund request timeout
is `UNKNOWN`; do not send a new refund blindly. Fees, disputes, FX, reserve, and payout
are separate ledger events, not mutations of the original payment row.

## 12. Exactly-once financial effect through ledger references

```text
function postSuccessfulEffect(effect):
    ledgerKey = (effect.type, effect.resourceId, effect.generation)
    ledger.postTransaction(
      idempotencyKey=ledgerKey,
      currency=effect.currency,
      entries=balancedEntriesFor(effect))
    transaction:
        ledgerLinks.insertUnique(ledgerKey, ledger.transactionId,
                                 effect.amount)
        mark effect LEDGER_POSTED if current version matches
```

The cross-service call can repeat; the ledger's unique external reference ensures one
balanced transaction. Reconciler finds successful effects without links and links
without matching amounts. Do not claim network exactly-once delivery.

## 13. Routing and retry policy

Route only among processors capable of method, currency, authentication, region,
merchant category, amount, capture/refund semantics, and data residency. Then optimize
expected approval, latency, cost, and capacity using controlled experiments. Maintain
merchant/payment-method affinity where it improves token portability and refunds.

Retry transport errors only with the same provider idempotency key. Do not reroute an
ambiguous authorization to a second provider: both may succeed. A definitive technical
failure proven not to have created an effect can start a new generation/provider;
declines are retried only under network/card-scheme/product rules to prevent abuse.

## 14. Risk and customer authentication

Risk evaluates merchant, account, device, IP, payment instrument token, amount,
velocity, history, and behavioral signals under a strict deadline. Actions are allow,
deny, review, or require step-up authentication. Store risk model/rule version and
reason codes; hard sanctions/limits fail closed.

Customer action has a nonce bound to intent/attempt/amount/merchant, return URL allowlist,
expiry, and one-time state. The result is verified server-to-server/provider-signed;
never trust only the browser redirect. Risk/model failure follows documented low/high
risk policy rather than silently approving everything.

## 15. Reconciliation

Continuously query aged `UNKNOWN` attempts. Daily/intraday provider reports and bank/
settlement files are checksummed, staged, parsed idempotently, and matched by external
reference, merchant reference, amount, currency, and date. Compare:

```text
provider operation <-> internal attempt/state <-> ledger effect
<-> fee/settlement/payout entries <-> bank movement
```

Classify missing internal, missing provider, amount/currency mismatch, duplicate,
state mismatch, and settlement mismatch. Safe automated repairs use idempotent commands;
money-changing/manual adjustments require approval and immutable evidence. Track every
case to terminal resolution.

## 16. Webhooks to merchants

Intent transaction emits ordered sequence events. Delivery platform signs raw body,
uses stable delivery/event ID, retries with jitter, and records attempts. Merchant
deduplicates event ID and fetches current intent before irreversible action. Ordering
is best effort unless a per-intent ordered stream is explicitly offered; event payload
contains object version. Merchant endpoint failure cannot roll back payment state.

## 17. Partitioning and resilience

Partition intents/attempts/inbox/outbox by intent ID; directory/index supports merchant
queries. Keep one home region/leader per intent with consensus/fencing. PCI vault,
risk, adapters, callback ingress, ledger, and reconciliation use separate credentials,
networks, and failure pools. Provider circuit breakers stop new routes but never block
callbacks/status reconciliation. Backpressure low-priority status/list/report work
before interactive commands.

## 18. Failure handling

| Failure | Correct behavior |
| --- | --- |
| Client retry after timeout | Same merchant key returns original resource/result |
| Provider timeout/reset | Attempt becomes UNKNOWN; query/reconcile same reference |
| Provider callback repeats | Verified inbox ID/hash makes it a no-op |
| Callback precedes API response | Same attempt state machine accepts newest evidence |
| Provider outage | Stop new routes; reconcile existing operations; route only new safe attempts |
| Gateway worker dies after send | Durable SENT/UNKNOWN attempt resumes status query |
| Ledger call repeats | Unique effect reference posts one balanced transaction |
| Webhook endpoint fails | Payment remains committed; delivery retries/DLQs |
| Region partitions | Fence old leader; favor consistency for money transitions |

## 19. Security and compliance

Minimize PCI scope with hosted fields/tokenization; never log PAN, CVV, bank credentials,
client secrets, or full provider payloads. Vault encrypts with HSM-managed keys and
strict network/role separation. Use mTLS/service identity, merchant RBAC, signed
requests/callbacks/webhooks, replay windows, key rotation, field encryption, tamper-
evident audit, and separation of duties.

Prevent amount/currency/merchant-reference tampering, IDOR, card testing, refund fraud,
credential stuffing, webhook SSRF, and malicious redirect URLs. Apply financial/PCI/
privacy retention, consent, deletion/minimization, sanctions, regional processing,
legal hold, incident response, and tested key/backup recovery with qualified review.

## 20. Observability

Track request/stage/provider latency, intent/attempt/refund state and age, authorization/
capture/refund rates, decline taxonomy, step-up conversion, provider routing/health/
circuit capacity, idempotency replay/hash mismatch, callback signature/duplicate/lag,
UNKNOWN count/time-to-resolution, ledger posting lag/duplicates, merchant webhook age,
reconciliation case type/age/value, settlement/payout mismatch, and money invariants.

Use synthetic low-value/test-provider transactions and adapter contract tests. Model-
check state transitions and property-test duplicate/reordered responses. Chaos tests
kill workers before/after provider send and state commit. Load tests include merchant
hot keys/callback bursts. Daily control totals compare provider, intents, ledger, and
bank/settlement evidence by currency—never aggregate different currencies.

## 21. Implementation path

1. **MVP:** one processor, tokenized method, intent/attempt state machine, merchant
   idempotency, authorize/capture/refund, verified callbacks, and manual reconciliation.
2. **Financial correctness:** outbox/inbox, UNKNOWN query worker, double-entry ledger
   links, automated reports/cases, signed merchant webhooks, and risk/authentication.
3. **Multi-provider:** capability-aware routing, isolated adapters/circuits, token
   portability policy, merchant controls, experiment guardrails, and regional capacity.
4. **Hardening:** PCI/security/privacy controls, fenced failover, state/model/chaos/
   load tests, control totals, restore/key-rotation drills, runbooks, and SLOs.

## 22. Final design

Use a merchant-idempotent payment intent with explicit attempts and amount-bounded
state transitions. Persist a stable provider request before network I/O; resolve only
from authenticated evidence and treat timeouts as unknown. Provider callbacks, ledger
posting, and merchant webhooks are at least once but deduplicated by stable references.
The vault minimizes credential scope, adapters isolate providers, and reconciliation
closes the unavoidable gap between database and external financial systems. This is
the core logic that prevents retries from becoming duplicate charges or refunds.
