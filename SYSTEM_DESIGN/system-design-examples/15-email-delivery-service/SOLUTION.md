# Complete Solution: Email Delivery Service

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Send transactional and bulk email from versioned templates, schedule messages,
apply suppression/consent, route through SMTP/provider pools, retry temporary
failures, process bounces/complaints, protect sender reputation, and expose an
auditable status stream.

Targets: 500 million recipient deliveries/day, 10x campaign bursts, transactional
queue p99 below one minute, no bulk starvation of transactional mail, and durable
acceptance after idempotent admission. Provider acceptance is not guaranteed inbox
placement or reading.

## 2. Capacity estimation

```text
average deliveries/s = 500M / 86,400 ~= 5.8K
10x peak             ~= 58K/s
rendered 100 KB each ~= 50 TB/day before compression/retention
```

Do not retain every rendered body forever. Keep template/version/variables or an
audit hash according to policy, with short body retention for troubleshooting.

## 3. API and model

```text
POST /v1/emails
Idempotency-Key: ...
{tenant, message_class, template_id, template_version,
 recipients, variables, schedule_at, headers, tags}
```

```text
Message(id, tenant, class, template_version, idempotency_key,
        state, schedule_at, subject, body_ref, created_at)
Recipient(message_id, recipient_id, address_hash, encrypted_address,
          state, attempt, next_attempt_at, provider, provider_id)
Suppression(address_hash, tenant_or_global, reason, source, expires_at)
SendingIdentity(domain, dkim_key_ref, pool, reputation_state)
```

One message may have many recipients, but each recipient has independent status
and retry. Bulk audience expansion uses deterministic recipient IDs.

## 4. Architecture

```text
producer -> admission/idempotency -> message store + outbox
                                   -> scheduler/audience expansion
                                   -> suppression + renderer
                                   -> class/tenant queues
                                   -> MTA/provider workers -> internet/providers
                                                        |
feedback webhooks/SMTP bounces -> verifier/normalizer -> status + suppression

reputation controller -> routing pools, quotas, pause/slow decisions
```

Transactional and bulk messages use separate queues, workers, provider quotas, and
sending identities where needed.

## 5. Step-by-step workflow

1. Authenticate tenant and validate sender identity, recipients, class, schedule,
   headers, template/version, variables, and idempotency.
2. Transactionally persist message and outbox; return message ID.
3. At due time, expand recipients in pages with deterministic IDs.
4. Check global/tenant suppression and consent before rendering.
5. Render pinned template, enforce HTML/text/size/link policy, and produce headers.
6. Queue recipient by class, tenant, domain/provider, and priority.
7. Worker chooses healthy sending pool, sends, and records SMTP/provider result.
8. Retry only temporary failures with bounded backoff; permanent failures stop.
9. Verified bounce/complaint/unsubscribe feedback updates recipient and suppression.

## 6. Admission logic

```text
function createEmail(tenant, request, key):
    validateTenantAndSendingIdentity(tenant, request.from)
    template = templates.getPinned(request.templateId, request.templateVersion)
    requestHash = sha256(canonicalJson(request))

    transaction:
        old = idempotency.get(tenant.id, key)
        if old exists:
            require old.requestHash == requestHash else Conflict
            return old.messageId

        message = Message(uniqueId(), tenant.id, request.class,
                          template.version, key, QUEUED, request.scheduleAt)
        messages.insert(message)
        idempotency.insert(tenant.id, key, requestHash, message.id)
        outbox.insert(MessageReady(message.id))
    return message.id
```

Pin template and sending identity policy at admission, but recheck suppression at
send time because a user may unsubscribe while a campaign waits.

## 7. Recipient expansion and rendering

```text
function expand(message, user):
    address = directory.emailFor(user)
    addressHash = hmac(normalize(address))
    recipientId = hash(message.id, addressHash)
    if not recipients.insertIfAbsent(recipientId, encrypted(address), READY): return

    if suppression.matches(message.tenant, addressHash, message.class):
        recipients.finish(recipientId, SUPPRESSED); return

    rendered = renderer.render(message.templateVersion, user.locale,
                               validatedVariables(message,user))
    require rendered.totalBytes <= MAX_EMAIL_BYTES
    bodyRef = bodyStore.putImmutable(hash(rendered), rendered)
    recipients.attachBody(recipientId, bodyRef)
    queueFor(message.class, domain(address)).publish(recipientId)
```

Template output must escape variables by context. Generate multipart text/plain
and text/html; never let a variable inject arbitrary headers.

## 8. Delivery and retry logic

```text
function deliver(recipientId):
    delivery = recipients.lease(recipientId, workerId, 60 seconds)
    if not acquired: return
    if suppression.nowMatches(delivery): finish(SUPPRESSED); return

    route = reputationRouter.choose(delivery.tenant, domain(delivery.address),
                                    delivery.messageClass)
    result = route.send(buildRfcMessage(delivery), stableMessageId=recipientId)

    if result.smtpCode in 200..299:
        finish(ACCEPTED, result.providerId)
    else if result.temporary and attempts < policy.max and beforeExpiry:
        retryAt(cappedBackoffWithJitter(attempts))
    else:
        finish(BOUNCED_OR_FAILED, normalize(result))
        if result.hardBounce: suppression.add(addressHash, HARD_BOUNCE)
```

An SMTP timeout can be ambiguous: remote server may have accepted after local
timeout. Retry with stable RFC `Message-ID`; duplicates are still possible and
status records the ambiguity.

## 9. Feedback processing

1. Verify provider webhook signature or ingest authenticated bounce mailbox.
2. Deduplicate provider event ID.
3. Resolve stable message/recipient reference.
4. Apply monotonic state transition; late “delivered” cannot erase a complaint.
5. Hard bounce/complaint/unsubscribe writes suppression immediately.
6. Reputation metrics and tenant alerts update asynchronously.

Feedback is untrusted input: bound payload, validate source, and quarantine unknown
formats instead of corrupting suppression.

## 10. Reputation and routing

- Configure SPF, DKIM, DMARC, reverse DNS, and domain alignment.
- Warm new IP/domain pools gradually.
- Separate transactional from bulk reputation; isolate abusive tenants.
- Apply per-domain concurrency/rate based on observed deferrals.
- Pause a campaign on complaint/bounce guardrails.
- Do not fail over repeatedly across providers in a way that multiplies duplicates.

Dedicated pools isolate large senders but cost capacity; shared pools improve
utilization while coupling reputation. Use thresholds and business tier.

## 11. Suppression precedence

Global legal/complaint suppression wins over tenant preference. Transactional
categories may bypass marketing opt-out only when explicitly permitted, but never
bypass hard-bounce or abuse blocks. Store source/reason/time and audit every
manual override.

## 12. Scheduling and cancellation

Durable time buckets release scheduled messages. Cancellation prevents recipients
not yet leased; already accepted SMTP messages cannot be recalled. API reports
counts by queued/submitted/terminal state instead of a misleading boolean.

## 13. Failure handling

| Failure | Behavior |
| --- | --- |
| Admission DB/queue fails | Idempotent retry; transactional outbox prevents loss |
| Expansion/render worker fails | Deterministic recipient row makes replay safe |
| Provider/MTA unavailable | Circuit and bounded temporary retries; other pools only by policy |
| Ambiguous SMTP timeout | Stable Message-ID, retry policy, duplicate risk recorded |
| Feedback duplicated/out of order | Event dedupe and monotonic state precedence |
| Suppression store unavailable | Bulk/marketing fails closed; critical policy is explicit |
| Reputation degrades | Slow/pause affected tenant/domain/pool, preserve others |
| Bulk surge | Separate queue/capacity and tenant quotas protect transactional mail |

## 14. Security and compliance

- Tenant RBAC and verified sender/domain ownership.
- Encrypt addresses/body and tightly limit raw-content access.
- No arbitrary From, reply routing, headers, links, or attachments without policy.
- Scan attachments/URLs and prevent template/header injection.
- Signed unsubscribe links with scope/expiry; process immediately.
- Audit sends, audience access, suppression, replay, and employee content access.
- Retention, residency, consent, and deletion follow jurisdiction/product class.

## 15. Observability

Measure admission/render/queue age, accepted/delivered/temporary/hard-bounce/
complaint/unsubscribe rates by tenant/domain/pool/provider/class, retry and ambiguous
outcomes, suppression hits, feedback delay, reputation/DMARC signals, body bytes,
cost, and transactional SLO during bulk campaigns.

Synthetic seed inboxes verify authentication, rendering, links, provider routing,
feedback, unsubscribe, and transactional latency. Test provider outage, ambiguous
timeout, feedback replay, and campaign guardrail pause.

## 16. Implementation path

1. **MVP:** one managed provider, verified sender, transactional queue,
   idempotency, templates, recipient status, hard-bounce suppression.
2. **Correct delivery:** outbox, scheduler, deterministic expansion, retries/DLQ,
   feedback verification, unsubscribe/complaint, audit.
3. **Scale/isolation:** bulk queues, tenant/domain quotas, batching, audience paging,
   body retention, reputation guardrails, and pool separation.
4. **Resilience/compliance:** multiple providers/pools, warm-up automation,
   regional rules, chaos/load tests, restore/replay drills.

## 17. Final design

Use idempotent transactional admission, deterministic recipient expansion,
suppression-before-render and before-send, isolated durable queues, provider/MTA
workers with bounded SMTP-aware retry, authenticated feedback, and reputation-based
routing. The invariant is that every recipient state is auditable and monotonic;
the system never claims inbox delivery merely because a provider accepted mail.
